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


def backend(task_state=70, task_mode=1, wait_result=0):
    # Stałe celowo inne niż w prawdziwym LinuxCNC: mapowanie idzie po nazwie stałej.
    stat = SimpleNamespace(
        poll=lambda: None, task_state=task_state, task_mode=task_mode, interp_state=1,
        axis_mask=0b111, actual_position=(0,) * 9, position=(0,) * 9, homed=(1, 1, 1),
        limit=(0, 0, 0), axis=({}, {}, {}), current_line=0, file="", feedrate=1.0,
        rapidrate=1.0, spindle=({},), tool_in_spindle=0, tool_offset=(), g5x_index=1,
        g5x_offset=(), gcodes=(), mcodes=())
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


def test_jog_converts_mm_per_second_to_per_minute_on_axis_index():
    b, c = backend(task_mode=1)
    b.jog("z", 2.5)
    b.jog_stop("Z")
    assert c.calls == [("jog", 21, False, 2, 150.0), ("jog", 20, False, 2)]


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
    assert c.calls == [("jog", 20, False, 0), ("jog", 20, False, 1), ("jog", 20, False, 2)]


def test_home_one_axis_and_all_and_unknown():
    b, c = backend()
    b.home("Y")
    b.home(None)
    assert c.calls == [("mode", 1), ("wait_complete", 2.0), ("home", 1),
                       ("mode", 1), ("wait_complete", 2.0), ("home", 0), ("home", 1),
                       ("home", 2)]
    with pytest.raises(CommandError, match="nieznana"):
        b.home("A")


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
