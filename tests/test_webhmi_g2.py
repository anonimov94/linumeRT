"""Testy bramy G2 bez LinuxCNC: zero detalu, wczytanie programu, alarmy i Reset.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-03. Odbiór na LinuxCNC + Plant: test_g2_webhmi_linuxcnc.py.
"""

import pytest
from linumert.cnc import FakeMachine, Mode
from linumert_webhmi import Command, FakeBackend, Gateway
from linumert_webhmi.backend import CommandError
from pydantic import ValidationError
from test_webhmi_linuxcnc_backend import backend as lc_backend

PROGRAM = "G21 G90\nG0 X5\nG1 X10 F600\nM2\n"


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def make(tmp_path, mode=Mode.MANUAL, homed=True):
    (tmp_path / "kwadrat.ngc").write_text(PROGRAM, encoding="utf-8")
    (tmp_path / ".ukryty.ngc").write_text(PROGRAM, encoding="utf-8")
    (tmp_path / "notatki.txt").write_text("nie program", encoding="utf-8")
    machine = FakeMachine(limits={"X": (-50.0, 50.0)})
    machine.estop_reset()
    machine.power_on()
    if homed:
        machine.home()
        machine.run_until_idle()
    machine.set_mode(mode)
    clock = Clock()
    gateway = Gateway(FakeBackend(machine, clock=clock, programs_dir=tmp_path), clock=clock)
    return gateway, machine, clock


def run(gateway, clock, seconds, step=0.02):
    for _ in range(round(seconds / step)):
        clock.t += step
        gateway.step()


def axes(gateway):
    return {a["name"]: a for a in gateway.snapshot()[1]["axes"]}


def test_work_zero_sets_active_offset_to_current_position(tmp_path):
    gateway, machine, clock = make(tmp_path)
    gateway.execute(Command(cmd="jog_increment", axis="X", speed=5, distance=1))
    run(gateway, clock, 0.5)
    gateway.execute(Command(cmd="work_zero", axis="X"))
    run(gateway, clock, 0.04)
    row = axes(gateway)["X"]
    assert row["position"] == pytest.approx(1.0)
    assert row["work_position"] == pytest.approx(0.0)
    gateway.execute(Command(cmd="work_zero"))
    run(gateway, clock, 0.04)
    assert all(abs(a["work_position"]) < 1e-9 for a in axes(gateway).values())


def test_work_zero_refused_while_jogging_unhomed_or_outside_manual(tmp_path):
    gateway, _, _ = make(tmp_path)
    gateway.execute(Command(cmd="jog", axis="X", speed=1))
    with pytest.raises(CommandError, match="JOG"):
        gateway.execute(Command(cmd="work_zero"))
    gateway, _, _ = make(tmp_path, homed=False)
    with pytest.raises(CommandError, match="bazowanie"):
        gateway.execute(Command(cmd="work_zero"))
    gateway, _, _ = make(tmp_path, mode=Mode.MDI)
    with pytest.raises(CommandError, match="MANUAL"):
        gateway.execute(Command(cmd="work_zero"))


def test_program_list_hides_non_programs_and_open_loads_file(tmp_path):
    gateway, _, clock = make(tmp_path, mode=Mode.AUTO)
    assert gateway.snapshot()[1]["programs"] == ["kwadrat.ngc"]
    gateway.execute(Command(cmd="open", name="kwadrat.ngc"))
    gateway.execute(Command(cmd="run"))
    run(gateway, clock, 2)
    state = gateway.snapshot()[1]
    assert state["program"].endswith("kwadrat.ngc")
    assert axes(gateway)["X"]["position"] == pytest.approx(10.0)


@pytest.mark.parametrize("name", ["../kwadrat.ngc", "/etc/passwd", ".ukryty.ngc",
                                  "notatki.txt", "a/b.ngc", "x.ngc\n"])
def test_open_rejects_paths_and_hidden_files(name):
    with pytest.raises(ValidationError):
        Command(cmd="open", name=name)


def test_open_rejects_file_outside_listing_and_without_homing(tmp_path):
    gateway, _, _ = make(tmp_path)
    with pytest.raises(CommandError, match="brak pliku"):
        gateway.execute(Command(cmd="open", name="brak.ngc"))
    gateway, _, _ = make(tmp_path, homed=False)
    with pytest.raises(CommandError, match="bazowanie"):
        gateway.execute(Command(cmd="open", name="kwadrat.ngc"))


def test_machine_error_becomes_alarm_until_reset(tmp_path):
    gateway, machine, clock = make(tmp_path, mode=Mode.AUTO)
    (tmp_path / "zly.ngc").write_text("G0 X5\nG33 X1\nM2\n", encoding="utf-8")
    gateway.execute(Command(cmd="open", name="zly.ngc"))
    gateway.execute(Command(cmd="run"))  # atrapa przerywa program na nieobsługiwanym G33
    run(gateway, clock, 1)
    alarms = gateway.snapshot()[1]["alarms"]
    assert [a["code"] for a in alarms] == ["E-1000"]
    assert alarms[0]["text"].startswith("Komunikat LinuxCNC:")
    run(gateway, clock, 0.5)
    assert len(gateway.snapshot()[1]["alarms"]) == 1  # komunikat nie znika sam
    gateway.execute(Command(cmd="reset"))
    assert gateway.snapshot()[1]["alarms"] == []
    assert gateway.snapshot()[1]["task_state"] == "on"


def test_condition_alarm_is_one_report_not_one_per_poll(tmp_path):
    gateway, _, clock = make(tmp_path)
    gateway.execute(Command(cmd="estop"))
    run(gateway, clock, 1)
    assert [(a["code"], a["count"]) for a in gateway.snapshot()[1]["alarms"]] == [("E-1100", 1)]


def test_reset_keeps_estop_alarm_and_never_releases_estop(tmp_path):
    gateway, machine, clock = make(tmp_path)
    gateway.execute(Command(cmd="estop"))
    run(gateway, clock, 0.04)
    assert [a["code"] for a in gateway.snapshot()[1]["alarms"]] == ["E-1100"]
    gateway.execute(Command(cmd="reset"))
    state = gateway.snapshot()[1]
    assert [a["code"] for a in state["alarms"]] == ["E-1100"]  # przyczyna trwa
    assert state["task_state"] == "estop"
    machine.estop_reset()  # zatrzask w HAL, poza bramą
    run(gateway, clock, 0.04)
    gateway.execute(Command(cmd="reset"))
    assert gateway.snapshot()[1]["alarms"] == []
    assert gateway.snapshot()[1]["task_state"] == "estop_reset"


def test_linuxcnc_work_zero_uses_g10_l20_and_returns_to_manual():
    b, c = lc_backend()
    b.snapshot()
    b.work_zero(None)
    assert ("mdi", "G10 L20 P0 X0 Y0 Z0") in c.calls
    assert [call for call in c.calls if call[0] == "mode"] == [("mode", 80), ("mode", 1)]
    c.calls.clear()
    b.work_zero("Y")
    assert ("mdi", "G10 L20 P0 Y0") in c.calls


@pytest.mark.parametrize("command", [Command(cmd="work_zero", axis="X"),
                                     Command(cmd="open", name="kwadrat.ngc")])
def test_setup_refused_until_failed_jog_stop_is_confirmed(tmp_path, command):
    gateway, _, _ = make(tmp_path)
    gateway.execute(Command(cmd="jog", axis="X", speed=1))
    original_stop = gateway.backend.jog_stop
    def failed_stop(axis):
        raise CommandError("STOP niepotwierdzony")
    gateway.backend.jog_stop = failed_stop
    with pytest.raises(CommandError, match="niepotwierdzone"):
        gateway.execute(Command(cmd="jog_stop", axis="X"))
    assert not gateway._jog and gateway._jog_retry
    with pytest.raises(CommandError, match="niepotwierdzone"):
        gateway.execute(command)
    gateway.backend.jog_stop = original_stop
    gateway.execute(Command(cmd="jog_stop"))
    gateway.execute(command)


def test_linuxcnc_work_zero_refuses_outside_manual():
    b, c = lc_backend(task_mode=80)
    b.snapshot()
    with pytest.raises(CommandError, match="MANUAL"):
        b.work_zero(None)
    assert c.calls == []


def test_linuxcnc_open_program_in_auto_from_program_dir(tmp_path):
    (tmp_path / "kwadrat.ngc").write_text(PROGRAM, encoding="utf-8")
    b, c = lc_backend()
    b._programs_dir = tmp_path
    b.snapshot()
    assert b.programs() == ("kwadrat.ngc",)
    b.open_program("kwadrat.ngc")
    assert c.calls == [("mode", 2), ("wait_complete", 2.0),
                       ("program_open", str(tmp_path / "kwadrat.ngc")),
                       ("wait_complete", 2.0)]
    with pytest.raises(CommandError, match="brak pliku"):
        b.open_program("inny.ngc")
