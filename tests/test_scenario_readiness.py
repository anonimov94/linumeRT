"""Runner must not confuse task ON with drive readiness. Model-Author: Codex."""

import json
import sys
from types import SimpleNamespace

import pytest
from linumert_plant.scenario_linuxcnc import DRIVER

START = 'out["machine_on"] = machine_on()'


def driver(monkeypatch, delayed_joint, ready_at):
    clock = SimpleNamespace(value=0.0)
    calls = []
    status = SimpleNamespace(task_state=0, poll=lambda: None)

    def read_hal(name):
        calls.append((clock.value, name))
        joint = int(name.split(".")[1])
        return joint != delayed_joint or clock.value >= ready_at

    monkeypatch.setitem(sys.modules, "hal", SimpleNamespace(
        component=lambda name: SimpleNamespace(ready=lambda: None), get_value=read_hal))
    monkeypatch.setitem(sys.modules, "linuxcnc", SimpleNamespace(
        STATE_ESTOP_RESET=2, STATE_ON=4,
        command=lambda: SimpleNamespace(state=lambda value: setattr(status, "task_state", value)),
        stat=lambda: status, error_channel=lambda: SimpleNamespace(poll=lambda: None)))
    monkeypatch.setattr(sys, "argv", ["driver.py", json.dumps({"diagnostics": True})])
    namespace = {}
    exec(DRIVER.split(START, 1)[0], namespace)
    namespace["driver_started"] = 0.0
    namespace["time"] = SimpleNamespace(
        time=lambda: clock.value, monotonic=lambda: clock.value,
        sleep=lambda seconds: setattr(clock, "value", clock.value + seconds))
    return namespace, clock, calls


@pytest.mark.parametrize("joint", range(4))
def test_machine_on_waits_for_each_drive_after_task_on(monkeypatch, joint):
    namespace, clock, calls = driver(monkeypatch, joint, ready_at=1.0)
    assert namespace["machine_on"]()
    assert 1.0 <= clock.value < 1.1
    assert {name for _, name in calls} == {f"lrt-cia402.{j}.enabled" for j in range(4)}
    assert namespace["out"]["drive_ready"][-1]["ready"] is True


def test_missing_drive_readiness_stops_before_homing(monkeypatch):
    namespace, clock, _ = driver(monkeypatch, 3, ready_at=float("inf"))
    # Run the actual startup statements through the first manual-mode command.
    startup = DRIVER[DRIVER.index(START):DRIVER.index('c.mode(linuxcnc.MODE_MANUAL)')]
    with pytest.raises(RuntimeError, match="napędy niegotowe do bazowania"):
        exec(startup, namespace)
    assert 5 <= clock.value < 5.1
    assert namespace["out"]["machine_on"] is False
    assert namespace["out"]["drive_ready"][-1]["ready"] is False
