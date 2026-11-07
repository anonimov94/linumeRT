"""Guard dispatch using constructed observations; actual CNC acceptance is separate.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from linumert.cnc import AxisSnapshot, InterpState, MachineSnapshot, Mode, TaskState
from linumert.tools.tbl import OFFSET_AXES, parse_tbl
from linumert_webhmi import Command, Gateway
from linumert_webhmi.backend import CommandError
from linumert_webhmi.job_instance import Instance, prepare
from test_job_instance import configuration as configuration
from test_job_instance import package as package


@pytest.fixture
def ready(configuration, tmp_path):
    record = prepare(configuration, tmp_path / "instance")
    clock = lambda: 100.0  # noqa: E731 - fixed synthetic clock, no real CNC
    instance = Instance(tmp_path / "instance/instance.json",
                        tmp_path / "instance/config" / record["ini"], clock=clock)
    start = [200, 200, -5]
    axes = tuple(AxisSnapshot(a, commanded=v, position=v + .0003, homed=True,
                             soft_min=instance._limits[a][0], soft_max=instance._limits[a][1])
                 for a, v in zip("XYZ", start, strict=True))
    snapshot = MachineSnapshot(timestamp=clock(), task_state=TaskState.ON, mode=Mode.AUTO,
        interp_state=InterpState.IDLE, axes=axes,
        program_file=str(instance.root / "config/nc_files/program.ngc"))
    tools = [{"id": t.number, "offsets": [t.values.get(a, 0) for a in OFFSET_AXES],
              "diameter": t.values.get("D", 0), "frontangle": t.values.get("I", 0),
              "backangle": t.values.get("J", 0), "orientation": t.orientation or 0}
             for t in parse_tbl(instance._files["tool.tbl"])]
    live = {"ini": str(instance.root / "config" / record["ini"]), "linear_units": 1,
            "inpos": True, "task_done": True, "current_vel": 0,
            "g5x_index": 1, "g5x_offset": [200, 200, -80] + [0] * 6,
            "g92_offset": [0] * 9, "rotation_xy": 0, "tool_offset": [0] * 9,
            "tool_table": tools, "hal": dict(instance.hal_expectations), "motion_line": 0}
    calls = []
    backend = SimpleNamespace(tick=lambda: None, snapshot=lambda: snapshot,
        binding_state=lambda pins: live, programs=lambda: ("program.ngc",), jog_stop=lambda a: None,
        confirm_job_state=lambda **kw: calls.append(("confirm", kw)),
        run_confirmed=lambda line: calls.append(("run", line)))
    gateway = Gateway(backend, clock=clock, instance=instance,
                      hal_pins=SimpleNamespace(tick=lambda *args: None))
    gateway.client_connected()
    gateway.step()
    yield gateway, instance, backend, calls, live
    if instance.run and instance.run.active:
        instance.fail("unavailable")


def test_matching_start_has_new_controller_confirmation_and_log_before_run(ready):
    gateway, instance, _, calls, _ = ready
    assert instance.can_start(), instance.status()
    gateway.execute(Command(cmd="run"))
    assert calls == [("confirm", {"paused": False}), ("run", 1)]
    manifest = json.loads((instance.run.path / "manifest.json").read_text())
    assert manifest["job_id"] == instance.record["job_id"] and manifest["target"] == "plant"
    assert instance.run.active and not instance.can_start()


@pytest.mark.parametrize("problem", ["file", "hal", "ram", "stale", "line", "client"])
def test_rejection_never_reaches_control_confirmation_or_run(ready, problem):
    gateway, instance, backend, calls, live = ready
    command = Command(cmd="run")
    if problem == "file":
        path = instance.root / "config/nc_files/program.ngc"
        path.write_text(path.read_text() + "G0 X500\n")
    elif problem == "hal":
        live["hal"]["lrt_hmi_bypass.in1"] = True
    elif problem == "ram":
        live["tool_table"][0]["offsets"][2] += .00001
    elif problem == "stale":
        snapshot = replace(backend.snapshot(), timestamp=99)
        backend.snapshot = lambda: snapshot
    elif problem == "client":
        gateway.client_disconnected()
    else:
        command = Command(cmd="run", from_line=5)
    with pytest.raises(CommandError):
        gateway.execute(command)
    assert calls == [] and instance.run is None
    assert not (instance.root / "runs").exists()


def test_changed_readiness_after_echo_is_rejected_before_auto_run(ready):
    gateway, instance, backend, calls, live = ready
    def confirm(**kwargs):
        calls.append(("confirm", kwargs))
        live["g92_offset"][0] = .001
    backend.confirm_job_state = confirm
    with pytest.raises(CommandError, match="zablokowany"):
        gateway.execute(Command(cmd="run"))
    assert calls == [("confirm", {"paused": False})] and instance.run is None


def test_gateway_shutdown_aborts_active_job_and_closes_incomplete_log(ready):
    gateway, instance, backend, calls, _ = ready
    backend.stop = lambda: calls.append(("stop",))
    gateway.execute(Command(cmd="run"))
    gateway.stop()
    assert calls[-1] == ("stop",)
    assert instance.run.phase == "unavailable" and instance.run.stream.closed
    result = json.loads((instance.run.path / "result.json").read_text())
    assert result["status"] == "unavailable"


@pytest.mark.parametrize("change", [False, True])
@pytest.mark.parametrize("file", ["nc_files/program.ngc", "macros/lrt_m6.ngc", "unapproved.ngc"])
def test_resume_uses_paused_tool_and_pose_instead_of_initial_t0(ready, change, file):
    gateway, instance, backend, calls, live = ready
    gateway.execute(Command(cmd="run"))
    paused = replace(backend.snapshot(), interp_state=InterpState.PAUSED, tool_number=1,
        program_file=str(instance.root / "config" / file),
        axes=tuple(replace(a, commanded=a.commanded + 1, position=a.position + 1)
                   for a in backend.snapshot().axes))
    backend.snapshot = lambda: paused
    backend.resume = lambda: calls.append(("resume",))
    live["tool_offset"][2] = 40
    live["inpos"] = False  # paused LinuxCNC retains the pending motion queue
    for _ in range(3):
        gateway.step()
    assert instance.can_resume() == (file != "unapproved.ngc")
    assert not instance.can_start()
    if change or file == "unapproved.ngc":
        live["tool_offset"][2] = 40.01
        with pytest.raises(CommandError, match="zablokowane"):
            gateway.execute(Command(cmd="resume"))
        assert ("resume",) not in calls
    else:
        gateway.execute(Command(cmd="resume"))
        assert calls[-2:] == [("confirm", {"paused": True}), ("resume",)]
        assert not instance.can_resume()
