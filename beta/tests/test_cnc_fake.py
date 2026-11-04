"""Testy atrapy maszyny (bez LinuxCNC). Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from linumert.cnc import FakeMachine, InterpState, Mode, TaskState


def make(mode=Mode.MDI, **kwargs):
    machine = FakeMachine(**kwargs)
    assert machine.estop_reset() and machine.power_on()
    assert machine.home()
    machine.run_until_idle()
    assert machine.set_mode(mode)
    return machine


def pos(machine, axis="X"):
    return machine.snapshot().axis(axis).position


def test_initial_state_is_estop_and_unhomed():
    snap = FakeMachine().snapshot()
    assert snap.task_state is TaskState.ESTOP
    assert snap.axis_names == ("X", "Y", "Z")
    assert not snap.all_homed
    assert snap.interp_state is InterpState.IDLE


def test_power_sequence_requires_estop_reset():
    machine = FakeMachine()
    assert machine.power_on() is False
    assert "E-stop" in machine.snapshot().errors[-1]
    assert machine.estop_reset() and machine.power_on()
    assert machine.snapshot().task_state is TaskState.ON


def test_homing_takes_distance_over_homing_speed():
    machine = FakeMachine(start={"X": 10.0})
    machine.estop_reset()
    machine.power_on()
    assert machine.home()
    elapsed = machine.run_until_idle()
    assert elapsed == pytest.approx(0.5, abs=0.06)  # 10 mm / 20 mm/s
    snap = machine.snapshot()
    assert snap.all_homed and snap.positions == {"X": 0.0, "Y": 0.0, "Z": 0.0}


def test_mdi_and_auto_refused_when_not_homed():
    machine = FakeMachine()
    machine.estop_reset()
    machine.power_on()
    assert machine.set_mode(Mode.MDI) is False
    assert "zbazowane" in machine.snapshot().errors[-1]


def test_mdi_requires_machine_on():
    assert FakeMachine().mdi("G0 X1") is False


def test_rapid_move_duration_and_position():
    machine = make()
    assert machine.mdi("G0 X100")
    assert machine.run_until_idle() == pytest.approx(0.5, abs=0.06)  # 100 mm / 200 mm/s
    assert pos(machine) == pytest.approx(100.0)


def test_feed_move_interpolates_linearly():
    machine = make()
    machine.mdi("G1 X50 F600")  # 10 mm/s
    machine.advance(2.5)
    assert pos(machine) == pytest.approx(25.0)
    assert machine.snapshot().interp_state is InterpState.READING
    assert machine.run_until_idle() == pytest.approx(2.5, abs=0.06)


def test_feed_and_rapid_override_scale_time():
    machine = make()
    machine.set_override(feed=0.5, rapid=0.5)
    machine.mdi("G1 X50 F600")
    assert machine.run_until_idle() == pytest.approx(10.0, abs=0.06)
    machine.mdi("G0 X150")
    assert machine.run_until_idle() == pytest.approx(1.0, abs=0.06)  # 100 mm / 100 mm/s


def test_zero_override_stalls_motion():
    machine = make()
    machine.set_override(feed=0.0)
    machine.mdi("G1 X10 F600")
    with pytest.raises(TimeoutError):
        machine.run_until_idle(max_time=1.0)
    assert pos(machine) == 0.0


def test_relative_distance_mode():
    machine = make()
    machine.mdi("G0 X10")
    machine.run_until_idle()
    machine.mdi("G91 G0 X5")
    machine.run_until_idle()
    machine.mdi("G91 G0 X5")
    machine.run_until_idle()
    assert pos(machine) == pytest.approx(20.0)
    assert "G91" in machine.snapshot().active_gcodes


def test_work_offset_and_g53():
    machine = make()
    machine.set_work_offset("G54", X=100.0)
    machine.mdi("G54 G0 X10")
    machine.run_until_idle()
    snap = machine.snapshot()
    assert snap.axis("X").position == pytest.approx(110.0)
    assert snap.work_position("X") == pytest.approx(10.0)
    assert snap.work_offset_name == "G54"
    machine.mdi("G53 G0 X0")
    machine.run_until_idle()
    assert pos(machine) == pytest.approx(0.0)
    assert machine.snapshot().work_position("X") == pytest.approx(-100.0)


def test_soft_limit_rejects_move_without_motion():
    machine = make(limits={"X": (-10.0, 10.0)})
    assert machine.mdi("G0 X20") is False
    assert "limit" in machine.snapshot().errors[-1]
    assert machine.run_until_idle() == 0.0
    assert pos(machine) == 0.0


def test_program_runs_lines_and_reports_current_line():
    machine = make(Mode.AUTO)
    machine.load_program(["G0 X10", "(komentarz) G1 Y10 F600", "", "M30", "G0 X99"], "t.ngc")
    assert machine.run()
    assert machine.snapshot().current_line == 1
    machine.advance(0.06)
    snap = machine.snapshot()
    assert snap.current_line == 2 and snap.interp_state is InterpState.READING
    assert snap.program_file == "t.ngc"
    machine.run_until_idle()
    snap = machine.snapshot()
    assert snap.positions["X"] == pytest.approx(10.0) and snap.positions["Y"] == pytest.approx(10.0)
    assert snap.interp_state is InterpState.IDLE and snap.current_line == 0


def test_pause_resume_and_m0():
    machine = make(Mode.AUTO)
    machine.load_program(["G1 X10 F600", "M0", "G0 X20"])
    machine.run()
    machine.advance(0.2)
    assert machine.pause()
    frozen = pos(machine)
    machine.advance(5.0)
    assert pos(machine) == frozen
    assert machine.snapshot().interp_state is InterpState.PAUSED
    assert machine.resume()
    machine.run_until_idle()  # zatrzymuje sie na M0
    snap = machine.snapshot()
    assert snap.positions["X"] == pytest.approx(10.0)
    assert snap.interp_state is InterpState.PAUSED and snap.current_line == 2
    machine.resume()
    machine.run_until_idle()
    assert pos(machine) == pytest.approx(20.0)


def test_dwell_reports_waiting():
    machine = make()
    machine.mdi("G4 P2")
    machine.advance(1.0)
    assert machine.snapshot().interp_state is InterpState.WAITING
    assert machine.run_until_idle() == pytest.approx(1.0, abs=0.06)


def test_spindle_and_tool_codes():
    machine = make()
    machine.mdi("T5 M6")
    machine.mdi("M3 S1200")
    snap = machine.snapshot()
    assert snap.tool_number == 5 and snap.spindle_running
    assert snap.spindle_direction == 1 and snap.spindle_speed == 1200.0
    machine.mdi("M5")
    assert not machine.snapshot().spindle_running


def test_estop_stops_everything_and_clears_homing():
    machine = make(Mode.MDI)
    machine.mdi("M3 S500")
    machine.mdi("G0 X100")
    machine.advance(0.1)
    machine.estop()
    snap = machine.snapshot()
    assert snap.task_state is TaskState.ESTOP and not snap.spindle_running
    assert not snap.all_homed and snap.interp_state is InterpState.IDLE


def test_unsupported_gcode_aborts_program_and_reports_error():
    machine = make(Mode.AUTO)
    machine.load_program(["G0 X1", "G2 X2 Y2 I1", "G0 X3"])
    machine.run()
    machine.run_until_idle()
    snap = machine.snapshot()
    assert snap.positions["X"] == pytest.approx(1.0)
    assert snap.interp_state is InterpState.IDLE
    assert any("G2" in text for text in snap.errors)
    machine.clear_errors()
    assert machine.snapshot().errors == ()


def test_mode_change_refused_while_moving():
    machine = make()
    machine.mdi("G0 X100")
    assert machine.set_mode(Mode.MANUAL) is False


def test_snapshot_freshness_uses_virtual_clock():
    machine = make()
    old = machine.snapshot()
    machine.advance(1.0)
    assert not old.is_fresh(machine.clock())
    assert machine.snapshot().is_fresh(machine.clock())
    assert old.age(machine.clock()) == pytest.approx(1.0)


def test_rotary_axis_and_axis_validation():
    machine = make(axes=("X", "Y", "Z", "A"))
    machine.mdi("G0 A90")
    machine.run_until_idle()
    assert pos(machine, "A") == pytest.approx(90.0)
    with pytest.raises(ValueError):
        FakeMachine(axes=("Q",))


def test_jog_moves_until_stopped_and_respects_limits():
    machine = make(Mode.MANUAL, limits={"X": (-5.0, 5.0)})
    assert machine.jog("X", 2.0)
    machine.advance(1.0)
    assert pos(machine) == pytest.approx(2.0)
    machine.advance(10.0)
    assert pos(machine) == pytest.approx(5.0)  # twardo obciete limitem
    machine.jog_stop("X")
    machine.advance(1.0)
    assert pos(machine) == pytest.approx(5.0)


def test_jog_refused_outside_manual_and_when_off():
    machine = make(Mode.MDI)
    assert not machine.jog("X", 1.0)
    assert not machine.jog("Q", 1.0)
    machine.estop()
    assert not machine.jog("X", 1.0)
