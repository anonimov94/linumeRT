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
        command=lambda: None, stat=lambda: status,
        error_channel=lambda: SimpleNamespace(poll=lambda: next(messages, None))))
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
