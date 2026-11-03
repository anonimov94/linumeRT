"""Mapowanie poleceń bramy na linuxcnc.command, na sztucznym module (bez LinuxCNC).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · NIEZWERYFIKOWANE NA LinuxCNC 2.9 RIP
"""

from types import SimpleNamespace

import pytest
from linumert.cnc import Mode
from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert_webhmi import LinuxCNCBackend
from linumert_webhmi.backend import CommandError


class Recorder:
    """Zapisuje wywołania ``linuxcnc.command``; ``wait_complete`` zwraca 0 (sukces)."""

    def __init__(self, wait_result=0):
        self.calls = []
        self.wait_result = wait_result

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name, *args))
            return self.wait_result if name == "wait_complete" else None
        return call


def backend(task_state=70, task_mode=1, wait_result=0, linear_units=1.0):
    # Stałe celowo inne niż w prawdziwym LinuxCNC: mapowanie idzie po nazwie stałej.
    stat = SimpleNamespace(
        poll=lambda: None, task_state=task_state, task_mode=task_mode, interp_state=1,
        axis_mask=0b111, actual_position=(0,) * 9, position=(0,) * 9, homed=(1, 1, 1),
        limit=(0, 0, 0), axis=({}, {}, {}), current_line=0, file="", feedrate=1.0,
        rapidrate=1.0, spindle=({},), tool_in_spindle=0, tool_offset=(), g5x_index=1,
        g5x_offset=(), gcodes=(), mcodes=(), linear_units=linear_units)
    command = Recorder(wait_result)
    module = SimpleNamespace(
        STATE_ESTOP=1, STATE_ESTOP_RESET=2, STATE_OFF=3, STATE_ON=70,
        MODE_MANUAL=1, MODE_AUTO=2, MODE_MDI=80, INTERP_IDLE=1, INTERP_READING=2,
        INTERP_PAUSED=91, INTERP_WAITING=4,
        AUTO_RUN=10, AUTO_PAUSE=11, AUTO_RESUME=12,
        JOG_STOP=20, JOG_CONTINUOUS=21, JOG_INCREMENT=22,
        stat=lambda: stat, error_channel=lambda: None, command=lambda: command)
    reader = LinuxCNCReader(module=module, stat=stat, error_channel=SimpleNamespace(
        poll=lambda: None), clock=lambda: 1.0)
    return LinuxCNCBackend(module=module, reader=reader, command=command), command


def test_estop_power_and_mode_use_named_constants():
    b, c = backend()
    b.estop()
    b.power_off()
    b.set_mode(Mode.MDI)
    assert c.calls == [("state", 1), ("state", 3), ("mode", 80), ("wait_complete", 2.0)]


def test_power_on_requires_external_estop_reset():
    b, c = backend(task_state=1)  # ESTOP
    with pytest.raises(CommandError, match="reset E-STOP"):
        b.power_on()
    assert c.calls == []
    b2, c2 = backend(task_state=2)  # ESTOP_RESET
    b2.power_on()
    assert c2.calls == [("state", 70)]


def test_gateway_backend_has_no_estop_reset_method():
    b, _ = backend()
    assert not hasattr(b, "estop_reset")


def test_mdi_run_pause_resume_stop():
    b, c = backend()
    b.mdi("G0 X1")
    b.run(5)
    b.pause()
    b.resume()
    b.stop()
    assert c.calls == [
        ("mode", 80), ("wait_complete", 2.0), ("mdi", "G0 X1"),
        ("mode", 2), ("wait_complete", 2.0), ("auto", 10, 5),
        ("auto", 11), ("auto", 12), ("abort",)]


@pytest.mark.parametrize("speed", [2.5, -2.5, 0.05])
@pytest.mark.parametrize("units", [1.0, 1 / 25.4])
def test_jog_uses_native_units_per_second(speed, units):
    # Po bazowaniu teleop numerem osi: LinuxCNC 2.9 odmawia jogu jointa z HOME_SEQUENCE < 0.
    b, c = backend(task_mode=1, linear_units=units)
    b.jog("z", speed)
    b.jog_stop("Z")
    assert c.calls == [("teleop_enable", 1), ("wait_complete", 2.0),
                       ("jog", 21, False, 2, speed * units), ("jog", 20, False, 2),
                       ("jog", 20, True, 2)]


def test_jog_before_homing_moves_the_axis_joint():
    b, c = backend(task_mode=1)
    b._reader._stat.homed = (0, 0, 0)
    b.jog("Z", 2.0)
    assert c.calls == [("teleop_enable", 0), ("jog", 21, True, 2, 2.0)]


@pytest.mark.parametrize("units", [None, 0, -1, float("nan"), float("inf")])
def test_jog_without_valid_machine_units_sends_no_motion(units):
    b, c = backend(linear_units=units)
    with pytest.raises(CommandError, match="skali jednostek"):
        b.jog("X", 1)
    assert c.calls == []


def test_jog_refused_outside_manual_and_for_unknown_axis():
    b, c = backend(task_mode=80)  # MDI
    with pytest.raises(CommandError, match="MANUAL"):
        b.jog("X", 1.0)
    b2, c2 = backend(task_mode=1)
    with pytest.raises(CommandError, match="nieznana"):
        b2.jog("A", 1.0)  # oś A nie jest w axis_mask
    assert c.calls == [] and c2.calls == []


def test_jog_stop_all_stops_every_configured_axis():
    b, c = backend()
    b.jog_stop(None)
    assert c.calls == [("jog", 20, False, 0), ("jog", 20, True, 0), ("jog", 20, False, 1),
                       ("jog", 20, True, 1), ("jog", 20, False, 2), ("jog", 20, True, 2)]


def test_home_one_axis_and_all_and_unknown():
    b, c = backend()
    b.home("Y")
    b.home(None)
    prepare = [("mode", 1), ("wait_complete", 2.0), ("teleop_enable", 0), ("wait_complete", 2.0)]
    assert c.calls == [*prepare, ("home", 1), *prepare, ("home", -1)]
    with pytest.raises(CommandError, match="nieznana"):
        b.home("A")


def gantry(homed=(1, 1, 1, 1), joint_axes=("X", "Y", "Y", "Z")):
    """mill_servo_table: osie X Y Z na jointach X Y Y Z."""
    b, c = backend()
    stat = b._reader._stat
    stat.joints, stat.ini_filename, stat.homed = len(joint_axes), "m.ini", homed
    stat.limit = (0,) * len(joint_axes)
    b._lc().ini = lambda _path: SimpleNamespace(
        find=lambda section, key: dict(enumerate(joint_axes)).get(int(section[6:])))
    return b, c


def motion(calls):
    return [call for call in calls if call[0] in ("home", "jog", "teleop_enable")]


def test_gantry_home_axis_z_is_joint_3_not_second_y():
    b, c = gantry()
    b.home("Z")
    assert c.calls[-1] == ("home", 3)


def test_gantry_home_all_includes_last_joint_through_home_sequence():
    b, c = gantry()
    b.home(None)
    assert c.calls[-1] == ("home", -1)


def test_gantry_joint_jog_z_goes_to_joint_3():
    b, c = gantry(homed=(0, 0, 0, 0))  # przed bazowaniem: joint osi
    b.jog("Z", 2.0)
    assert motion(c.calls) == [("teleop_enable", 0), ("jog", 21, True, 3, 2.0)]


@pytest.mark.parametrize("method, args", [("jog", (2.0,)), ("jog_increment", (2.0, 0.5))])
def test_gantry_axis_is_never_jogged_by_one_joint_before_homing(method, args):
    b, c = gantry(homed=(1, 0, 0, 1))
    with pytest.raises(CommandError, match="bazowania|bazowanie"):
        getattr(b, method)("Y", *args)
    assert motion(c.calls) == []


def test_gantry_axis_after_homing_jogs_in_teleop_by_axis_number():
    b, c = gantry()
    b.jog("Y", -2.0)
    assert motion(c.calls) == [("teleop_enable", 1), ("jog", 21, False, 1, -2.0)]
    c.calls.clear()
    b.jog_increment("Y", -2.0, 0.5)
    assert motion(c.calls) == [("teleop_enable", 1), ("jog", 22, False, 1, -2.0, 0.5)]


def test_gantry_stop_reaches_both_y_joints_and_teleop_and_z():
    b, c = gantry()
    b.jog_stop(None)
    assert c.calls == [("jog", 20, False, 0), ("jog", 20, True, 0), ("jog", 20, False, 1),
                       ("jog", 20, True, 1), ("jog", 20, True, 2), ("jog", 20, False, 2),
                       ("jog", 20, True, 3)]


def test_unhomed_z_blocks_increment_on_gantry():
    b, c = gantry(homed=(1, 1, 1, 0))
    with pytest.raises(CommandError, match="bazowanie"):
        b.jog_increment("X", 1, 0.1)
    assert motion(c.calls) == []


def test_ini_without_joint_map_refuses_motion_but_still_stops():
    b, c = gantry(joint_axes=(None, None, None, None))
    for call in (lambda: b.home("Z"), lambda: b.jog("Z", 1.0)):
        with pytest.raises(CommandError, match="JOINT_n"):
            call()
    assert motion(c.calls) == []
    b.jog_stop("Z")
    assert c.calls == [("jog", 20, False, 2)] + [("jog", 20, True, j) for j in range(4)]


def test_overrides_only_send_given_values():
    b, c = backend()
    b.set_override(feed=0.5, rapid=None, spindle=1.2)
    assert c.calls == [("feedrate", 0.5), ("spindleoverride", 1.2)]


def test_commands_do_not_drain_the_error_channel():
    b, c = backend(task_mode=1)
    reads = []
    original = b._reader.read
    b._reader.read = lambda: (reads.append(1), original())[1]
    b.snapshot()  # wątek odpytujący: jedyne źródło odczytu
    b.jog("X", 1.0)
    b.jog_stop(None)
    b.home("Y")
    assert len(reads) == 1


def test_home_unknown_axis_sends_nothing():
    b, c = backend()
    with pytest.raises(CommandError):
        b.home("A")
    assert c.calls == []


def test_wait_timeout_is_reported_to_operator():
    b, _ = backend(wait_result=-1)
    with pytest.raises(CommandError, match="nie potwierdził"):
        b.set_mode(Mode.AUTO)


def test_rcs_error_from_wait_complete_is_reported():
    b, c = backend(wait_result=3)
    b._lc().RCS_ERROR = 3
    with pytest.raises(CommandError, match="RCS_ERROR"):
        b.set_mode(Mode.MDI)


@pytest.mark.parametrize("units", [1.0, 1 / 25.4])
@pytest.mark.parametrize("speed", [2.5, -2.5])
def test_increment_converts_both_velocity_and_distance_without_reissuing_mode(units, speed):
    b, c = backend(linear_units=units)
    b.snapshot()
    b.jog_increment("X", speed, 0.1)
    assert c.calls == [("teleop_enable", 1), ("wait_complete", 2.0),
                       ("jog", 22, False, 0, speed * units, 0.1 * units)]


def test_increment_rotary_is_in_degrees_even_with_inch_linear_machine():
    b, c = backend(linear_units=1 / 25.4)
    b._reader._stat.axis_mask = 0b1111
    b._reader._stat.homed = (1,) * 4
    b.snapshot()
    b.jog_increment("A", -2, 1)
    assert c.calls[-1] == ("jog", 22, False, 3, -2, 1)


def test_increment_rejects_state_units_and_limits_before_any_motion():
    for b, c in (backend(task_state=1), backend(task_mode=80), backend(linear_units=None)):
        with pytest.raises(CommandError):
            b.jog_increment("X", 1, 1)
        assert c.calls == []
    b, c = backend()
    b._reader._stat.homed = (0, 1, 1)
    with pytest.raises(CommandError, match="bazowanie"):
        b.jog_increment("X", 1, 1)
    assert c.calls == []


def test_increment_checks_soft_limits_in_native_inch_units():
    b, c = backend(linear_units=1 / 25.4)
    b._reader._stat.actual_position = (0.99,) + (0,) * 8
    b._reader._stat.axis = ({"max_position_limit": 1}, {}, {})
    b.snapshot()
    with pytest.raises(CommandError, match="limit"):
        b.jog_increment("X", 1, 1)
    assert c.calls == []
    b.jog_increment("X", 1, 0.1)
    assert c.calls[-1][:4] == ("jog", 22, False, 0)
    assert c.calls[-1][4:] == pytest.approx((1 / 25.4, 0.1 / 25.4))
