"""Compare actual NML observations with immutable inputs; no command channel.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from linumert.cnc import AxisSnapshot, InterpState, MachineSnapshot, Mode, TaskState
from linumert.programs.job_binding import inspect
from test_webhmi_linuxcnc_backend import backend


@pytest.fixture
def observation(tmp_path):
    axes = tuple(AxisSnapshot(name=a, commanded=v, position=v + .0005, homed=True)
                 for a, v in zip("XYZ", (200, 200, -5), strict=True))
    snap = MachineSnapshot(timestamp=1, task_state=TaskState.ON, mode=Mode.AUTO,
        interp_state=InterpState.IDLE, axes=axes, program_file=str(tmp_path / "program.ngc"))
    live = {"ini": str(tmp_path / "machine.ini"), "linear_units": 1,
            "inpos": True, "current_vel": 0, "tool_offset": [0] * 9,
            "g5x_index": 2, "g5x_offset": [200, 200, -80, 0, 0, 0, 0, 0, 0],
            "g92_offset": [0] * 9, "rotation_xy": 0,
            "tool_table": [{"id": 1, "offsets": [0, 0, 40, 0, 0, 0, 0, 0, 0],
                            "diameter": 6, "frontangle": 0, "backangle": 0, "orientation": 0}]}
    expected = {"ini": tmp_path / "machine.ini", "program": tmp_path / "program.ngc",
        "table": "T1 P1 Z40 D6\n", "start": [200, 200, -5],
        "setup": {"offset": "G55", "origin_mm": [200, 200, -80]}}
    return snap, live, expected


def test_g55_and_sub_micron_settled_error_are_compared_without_rounding(observation):
    snap, live, expected = observation
    assert all(c["status"] == "passed" for c in inspect(snap, live, **expected).values())
    # Display rounding must never turn a position outside acceptance into a pass.
    x = replace(snap.axes[0], position=200.001001)
    bad = replace(snap, axes=(x, *snap.axes[1:]))
    assert inspect(bad, live, **expected)["start_position"]["status"] == "failed"
    x = replace(snap.axes[0], commanded=200.00001)
    bad = replace(snap, axes=(x, *snap.axes[1:]))
    assert inspect(bad, live, **expected)["start_position"]["status"] == "failed"


@pytest.mark.parametrize("field,value,check", [
    ("ini", "/different/machine.ini", "controller"),
    ("linear_units", 1 / 25.4, "units"), ("linear_units", float("nan"), "units"),
    ("tool_offset", [0, 0, 40, 0, 0, 0, 0, 0, 0], "initial_tool"),
    ("tool_offset", [0, 0, False, 0, 0, 0, 0, 0, 0], "initial_tool"),
    ("g5x_index", 1, "work_setup"), ("g5x_offset", [200, 200, -79] + [0] * 6, "work_setup"),
    ("g92_offset", [.00001] + [0] * 8, "work_setup"), ("rotation_xy", 1, "work_setup"),
    ("inpos", False, "machine_ready"), ("current_vel", .01, "machine_ready"),
])
def test_wrong_live_context_is_rejected(observation, field, value, check):
    snap, live, expected = observation
    live[field] = value
    assert inspect(snap, live, **expected)[check]["status"] == "failed"


def test_ram_tool_change_is_detected_with_unchanged_tool_file(observation):
    snap, live, expected = observation
    before = copy.deepcopy(expected)
    live["tool_table"][0]["offsets"][2] = 40.00001
    assert inspect(snap, live, **expected)["tool_table"]["status"] == "failed"
    assert expected == before
    live["tool_table"] = None
    assert inspect(snap, live, **expected)["tool_table"]["status"] == "unavailable"


def test_unknown_controller_data_and_wrong_program_never_pass(observation):
    snap, _, expected = observation
    checks = inspect(replace(snap, program_file=""), None, **expected)
    assert all(v["status"] != "passed" for k, v in checks.items() if k != "start_position")


def test_backend_binding_state_reads_ram_without_polling_or_commands():
    b, commands = backend()
    stat = b._reader._stat
    polls = []
    stat.poll = lambda: polls.append(1)
    row = {a + "offset": 0.0 for a in "xyzabcuvw"}
    row.update(id=1, zoffset=40.1234, diameter=6, frontangle=0, backangle=0, orientation=0)
    stat.tool_table = [SimpleNamespace(**row)]
    stat.ini_filename = "/private/machine.ini"
    state = b.binding_state()
    assert state["ini"] == stat.ini_filename
    assert state["tool_table"][0]["offsets"][2] == 40.1234
    assert commands.calls == polls == []
