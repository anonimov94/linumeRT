"""Offline failure-path checks; never starts LinuxCNC. Model-Author: Codex."""
import io
import json
import sys
from types import SimpleNamespace

import pytest
from plant_fixture_diagnostics import capture_console
from test_plant_linuxcnc import DRIVER


def prepare(monkeypatch, tmp_path):
    messages = iter([(1, "limit switch"), None])
    status = SimpleNamespace(
        poll=lambda: None, task_state=3, task_mode=2, interp_state=4,
        current_vel=0.2, position=[99, 200, -20], actual_position=[98.99, 200, -20],
        homed=[1]*4, limit=[1, 0, 0, 0], paused=False, motion_line=42,
        read_line=44, exec_state=7, joint=[{"ferror": 0.01, "fault": 1}]*4)
    monkeypatch.setitem(sys.modules, "linuxcnc", SimpleNamespace(
        INTERP_IDLE=1, command=lambda: None, stat=lambda: status,
        error_channel=lambda: SimpleNamespace(poll=lambda: next(messages, None))))
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "driver.py")])
    callbacks = []
    monkeypatch.setitem(sys.modules, "atexit", SimpleNamespace(register=callbacks.append))
    ns = {"__file__": str(tmp_path / "driver.py")}
    exec(DRIVER.split('c.state(linuxcnc.STATE_ESTOP_RESET)', 1)[0], ns)
    clock = SimpleNamespace(value=0.0)
    ns["time"] = SimpleNamespace(
        time=lambda: clock.value, monotonic=lambda: clock.value,
        sleep=lambda seconds: setattr(clock, "value", clock.value + seconds))
    ns["stage"] = "before_softlimit"
    return ns, callbacks, status


def test_timeout_and_assertion_keep_state_errors_and_prior_results(monkeypatch, tmp_path):
    ns, callbacks, _ = prepare(monkeypatch, tmp_path)
    ns["out"]["pockets"] = [{"done": True}]
    with pytest.raises(AssertionError):
        exec('assert wait(lambda: False, 0.1)', ns)
    ns.pop("__file__")  # LinuxCNC can remove it before interpreter shutdown
    callbacks[0]()  # the hook Python runs during interpreter shutdown
    saved = json.loads((tmp_path / "driver_diagnostics.json").read_text())
    assert saved["stage"] == "before_softlimit"
    assert saved["current_vel"] == 0.2
    assert saved["actual_position"][0] == 98.99
    assert saved["joints"][0]["fault"] == 1
    assert saved["results"]["errors"] == ["limit switch"]
    assert saved["results"]["pockets"] == [{"done": True}]
    assert saved["results"]["timeouts"][0]["reason"] == "wait_timeout"


def test_failed_poll_is_recorded_without_losing_results(monkeypatch, tmp_path):
    ns, callbacks, status = prepare(monkeypatch, tmp_path)
    def broken():
        raise RuntimeError("NML unavailable")
    status.poll = broken
    callbacks[0]()
    saved = json.loads((tmp_path / "driver_diagnostics.json").read_text())
    assert "NML unavailable" in saved["snapshot_error"]
    assert saved["results"] == {"errors": []}


def test_console_drain_preserves_output(tmp_path):
    target = tmp_path / "linuxcnc-console.log"
    thread = capture_console(SimpleNamespace(stdout=io.StringIO("startup\nlimit error\n")), target)
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert target.read_text() == "startup\nlimit error\n"


def test_initial_move_waits_for_feedback_instead_of_one_fixed_sleep(monkeypatch, tmp_path):
    ns, _, status = prepare(monkeypatch, tmp_path)
    status.interp_state, status.current_vel, status.inpos = 1, 0.0, True
    def poll():
        stamp = ns["time"].monotonic()
        # Inside once, then outside: the dwell must restart at the last recovery.
        settled = 0.1 <= stamp < 0.2 or stamp >= 0.4
        status.actual_position = [100 if settled else 99.9947, 200, -20]
    status.poll = poll
    assert ns["wait"](ns["settled_position"]((100, 200, -20)), 1.0)
    assert ns["time"].monotonic() >= 0.6
    assert status.actual_position == [100, 200, -20]


def test_endpoint_outside_existing_tolerance_still_times_out(monkeypatch, tmp_path):
    ns, _, status = prepare(monkeypatch, tmp_path)
    status.interp_state, status.current_vel, status.inpos = 1, 0.0, True
    status.actual_position = [99.9947, 200, -20]
    assert not ns["wait"](ns["settled_position"]((100, 200, -20)), 0.5)
    assert ns["out"]["timeouts"]
