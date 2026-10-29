"""Testy czytnika LinuxCNC na sztucznym module (bez LinuxCNC). Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import linumert
from linumert.cnc import InterpState, Mode, TaskState
from linumert.cnc.linuxcnc_reader import LinuxCNCReader


class FakeChannel:
    def __init__(self, items):
        self.items = list(items)

    def poll(self):
        return self.items.pop(0) if self.items else None


def fake_module(**stat_values):
    """Stale celowo maja inne liczby niz w prawdziwym LinuxCNC: mapowanie ma isc po nazwie."""
    values = {
        "task_state": 70, "task_mode": 80, "interp_state": 91, "axis_mask": 0b111,
        "actual_position": (1.0, 2.0, 3.0, 0, 0, 0, 0, 0, 0),
        "position": (1.5, 2.5, 3.5, 0, 0, 0, 0, 0, 0),
        "homed": (1, 1, 0), "limit": (0, 1, 0),
        "axis": ({"min_position_limit": -10.0, "max_position_limit": 10.0}, {}, {}),
        "current_line": 7, "file": "a.ngc", "feedrate": 0.8, "rapidrate": 0.5,
        "spindle": ({"speed": -1200.0, "direction": -1, "override": 1.1, "enabled": 1},),
        "tool_in_spindle": 4, "tool_offset": (0, 0, -12.5, 0, 0, 0, 0, 0, 0),
        "g5x_index": 2, "g5x_offset": (100.0, 0, -5.0, 0, 0, 0, 0, 0, 0),
        "gcodes": (7, 10, 170, 210, 551, 901, -1), "mcodes": (7, 5, -1, 9),
    }
    values.update(stat_values)
    stat = SimpleNamespace(poll=lambda: None, **values)
    return SimpleNamespace(
        STATE_ESTOP=1, STATE_ESTOP_RESET=2, STATE_OFF=3, STATE_ON=70,
        MODE_MANUAL=1, MODE_AUTO=2, MODE_MDI=80,
        INTERP_IDLE=1, INTERP_READING=2, INTERP_PAUSED=91, INTERP_WAITING=4,
        stat=lambda: stat,
        error_channel=lambda: FakeChannel([(1, "blad A"), (2, "info B")]),
    )


def read(**stat_values):
    return LinuxCNCReader(module=fake_module(**stat_values), clock=lambda: 42.0).read()


def test_states_are_mapped_by_constant_name():
    snap = read()
    assert snap.task_state is TaskState.ON
    assert snap.mode is Mode.MDI
    assert snap.interp_state is InterpState.PAUSED
    assert snap.timestamp == 42.0


def test_unknown_state_values_fall_back_to_safe_defaults():
    snap = read(task_state=999, task_mode=999, interp_state=999)
    assert snap.task_state is TaskState.ESTOP and snap.mode is Mode.MANUAL
    assert snap.interp_state is InterpState.IDLE


def test_axes_positions_homing_and_limits():
    snap = read()
    assert snap.axis_names == ("X", "Y", "Z")
    x, y, z = snap.axes
    assert (x.position, x.commanded) == (1.0, 1.5)
    assert x.homed and y.homed and not z.homed and not snap.all_homed
    assert (x.soft_min, x.soft_max) == (-10.0, 10.0)
    assert y.limit_hit and not x.limit_hit
    assert y.soft_min == float("-inf")


def test_axis_mask_selects_letters_for_four_axis_machine():
    snap = read(
        axis_mask=0b1111, homed=(1, 1, 1, 1), axis=(),
        actual_position=(1, 2, 3, 90, 0, 0, 0, 0, 0), position=(1, 2, 3, 90, 0, 0, 0, 0, 0),
    )
    assert snap.axis_names == ("X", "Y", "Z", "A")
    assert snap.axis("A").position == 90.0 and snap.all_homed


def test_spindle_tool_overrides_and_work_offset():
    snap = read()
    assert snap.spindle_direction == -1 and snap.spindle_speed == 1200.0
    assert snap.spindle_override == 1.1 and snap.feed_override == 0.8
    assert snap.rapid_override == 0.5 and snap.tool_number == 4
    assert snap.tool_offset["Z"] == -12.5
    assert snap.work_offset_name == "G55" and snap.work_offset["X"] == 100.0
    assert snap.work_position("X") == pytest.approx(-99.0)
    assert (snap.current_line, snap.program_file) == (7, "a.ngc")


def test_gcodes_and_mcodes_are_formatted_and_filtered():
    snap = read(gcodes=(7, 10, 170, 591, 901, -1, 0), mcodes=(3, 5, -1, 9))
    assert snap.active_gcodes == ("G1", "G17", "G59.1", "G90.1", "G0")
    assert snap.active_mcodes == ("M5", "M9")


def test_errors_are_drained_from_channel():
    reader = LinuxCNCReader(module=fake_module(), clock=lambda: 0.0)
    assert reader.read().errors == ("blad A", "info B")
    assert reader.read().errors == ()


def test_missing_linuxcnc_module_gives_clear_error():
    reader = LinuxCNCReader()
    try:
        import linuxcnc  # noqa: F401
    except ImportError:
        with pytest.raises(RuntimeError, match="linuxcnc"):
            reader.read()


def test_importing_package_does_not_import_linuxcnc():
    source = Path(linumert.__file__).resolve().parents[1]
    code = (
        "import sys; import linumert, linumert.cnc, linumert.cnc.linuxcnc_reader; "
        "sys.exit(1 if 'linuxcnc' in sys.modules else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env={"PYTHONPATH": str(source)}, check=False
    )
    assert result.returncode == 0
