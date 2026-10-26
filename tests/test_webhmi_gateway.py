"""Testy bramy web-hmi bez LinuxCNC: deadman jogu, polecenia, limit, schemat.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

import json

import pytest
from linumert.cnc import FakeMachine, Mode
from linumert_webhmi import Command, FakeBackend, Gateway, snapshot_to_dict
from linumert_webhmi.backend import CommandError
from linumert_webhmi.gateway import RateLimiter
from pydantic import ValidationError


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def make(mode=Mode.MANUAL, **kwargs):
    machine = FakeMachine(limits={"X": (-50.0, 50.0)})
    machine.estop_reset()
    machine.power_on()
    machine.home()
    machine.run_until_idle()
    machine.set_mode(mode)
    clock = Clock()
    gateway = Gateway(FakeBackend(machine, clock=clock), clock=clock, **kwargs)
    return gateway, machine, clock


def run(gateway, clock, seconds, step=0.02):
    for _ in range(round(seconds / step)):
        clock.t += step
        gateway.step()


def x(gateway):
    return gateway.snapshot()[1]["axes"][0]["position"]


def test_state_schema_is_json_serialisable_and_finite():
    gateway, _, _ = make()
    state = gateway.snapshot()[1]
    text = json.dumps(state, allow_nan=False)  # bez inf/nan
    assert '"schema": 1' in text
    assert state["task_state"] == "on" and state["mode"] == "manual"
    assert [a["name"] for a in state["axes"]] == ["X", "Y", "Z"]
    assert state["axes"][0]["soft_min"] == -50.0
    assert state["axes"][1]["soft_min"] == -1000.0


def test_snapshot_to_dict_maps_infinite_limits_to_null():
    from linumert.cnc.model import AxisSnapshot, MachineSnapshot

    snap = MachineSnapshot(timestamp=0.0, axes=(AxisSnapshot(name="X"),))
    state = snapshot_to_dict(snap)
    assert state["axes"][0]["soft_min"] is None and state["axes"][0]["soft_max"] is None
    json.dumps(state, allow_nan=False)


def test_jog_refresh_keeps_moving_and_deadman_stops_it():
    gateway, _, clock = make(jog_hold_s=0.4)
    jog = Command(cmd="jog", axis="X", speed=5.0)
    for _ in range(10):  # klient odświeża co 100 ms przez 1 s
        gateway.execute(jog)
        run(gateway, clock, 0.1)
    moved = x(gateway)
    assert moved == pytest.approx(5.0, abs=0.7)
    assert gateway.snapshot()[1]["jog_active"] == ["X"]
    run(gateway, clock, 1.0)  # klient znika: bez odświeżeń jog gaśnie po 0,4 s
    stopped = x(gateway)
    assert stopped - moved <= 5.0 * 0.5
    run(gateway, clock, 1.0)
    assert x(gateway) == pytest.approx(stopped)
    assert gateway.snapshot()[1]["jog_active"] == []


def test_losing_last_client_stops_jog_immediately():
    gateway, _, clock = make()
    gateway.client_connected()
    gateway.execute(Command(cmd="jog", axis="X", speed=5.0))
    run(gateway, clock, 0.1)
    gateway.client_disconnected()
    after = x(gateway)
    run(gateway, clock, 0.3)  # jeszcze w oknie deadmana, ale jog już zdjęty
    assert x(gateway) == pytest.approx(after)


def test_estop_and_stop_cancel_jog_and_estop_leaves_machine_off():
    gateway, _, clock = make()
    gateway.execute(Command(cmd="jog", axis="X", speed=5.0))
    run(gateway, clock, 0.1)
    gateway.execute(Command(cmd="estop"))
    held = x(gateway)
    run(gateway, clock, 0.3)
    assert x(gateway) == pytest.approx(held)
    assert gateway.snapshot()[1]["task_state"] == "estop"


def test_gateway_has_no_estop_reset_command():
    with pytest.raises(ValidationError):
        Command(cmd="estop_reset")
    gateway, _, _ = make()
    gateway.execute(Command(cmd="estop"))
    with pytest.raises(CommandError, match="reset E-stop|wlaczona|wymagany"):
        gateway.execute(Command(cmd="power_on"))  # bez resetu poza bramą


def test_machine_refusals_become_polish_command_errors():
    gateway, _, _ = make(Mode.MDI)
    with pytest.raises(CommandError, match="MANUAL"):
        gateway.execute(Command(cmd="jog", axis="X", speed=1.0))
    gateway.execute(Command(cmd="mdi", text="G0 X10"))


def test_command_validation_rejects_bad_input():
    for bad in (
        {"cmd": "jog", "axis": "X", "speed": 51.0},
        {"cmd": "jog", "axis": "X", "speed": float("inf")},
        {"cmd": "jog", "axis": "Q", "speed": 1.0},
        {"cmd": "mdi", "text": "G0 X1\nM30"},
        {"cmd": "mdi", "text": "   "},
        {"cmd": "mdi", "text": "G" * 201},
        {"cmd": "override", "feed": 2.5},
        {"cmd": "run", "from_line": 0},
        {"cmd": "format_disk"},
    ):
        with pytest.raises(ValidationError):
            Command.model_validate(bad)


def test_missing_arguments_are_rejected_by_gateway():
    gateway, _, _ = make()
    for cmd in (Command(cmd="jog", axis="X"), Command(cmd="mdi"), Command(cmd="mode"),
                Command(cmd="override")):
        with pytest.raises(CommandError):
            gateway.execute(cmd)


def test_rate_limiter_refills_over_time():
    clock = Clock()
    limiter = RateLimiter(rate=10.0, burst=3.0, clock=clock)
    assert [limiter.allow() for _ in range(4)] == [True, True, True, False]
    clock.t += 0.2  # +2 tokeny
    assert [limiter.allow() for _ in range(3)] == [True, True, False]


def test_gateway_rate_limit_blocks_command_flood():
    gateway, _, _ = make(command_rate=5.0)
    with pytest.raises(CommandError, match="zbyt wiele"):
        for _ in range(50):
            gateway.execute(Command(cmd="override", feed=1.0))


def test_heartbeat_reflects_recent_client_activity():
    gateway, _, clock = make()
    assert gateway.snapshot()[1]["heartbeat"] is False
    gateway.client_connected()
    run(gateway, clock, 0.1)
    assert gateway.snapshot()[1]["heartbeat"] is True
    run(gateway, clock, 2.0)  # klient milczy dłużej niż HEARTBEAT_S
    assert gateway.snapshot()[1]["heartbeat"] is False
    gateway.touch()
    run(gateway, clock, 0.1)
    assert gateway.snapshot()[1]["heartbeat"] is True
