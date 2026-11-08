# SPDX-License-Identifier: GPL-2.0-or-later
"""Piny HAL bramy WebHMI: sygnał życia, uzbrojenie watchdoga, podwójny Reset (D35, D37).

Model-Author: Claude · 2026-11-04. Bez LinuxCNC: atrapa zapisu pinów i zegar testu.
Odbiór na LinuxCNC + Plant: ``tests/test_webhmi_watchdog_linuxcnc.py``.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import pytest
from linumert.cnc import FakeMachine
from linumert_webhmi.backend import CommandError, FakeBackend
from linumert_webhmi.gateway import (
    ALARM_RESET_DELAY_S,
    ESTOP_RESET_DELAY_S,
    HEARTBEAT_S,
    Gateway,
)
from linumert_webhmi.hal_link import ARM_DELAY_S, PINS, PULSE_S, HalPins
from linumert_webhmi.schema import Command


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


class Pins:
    """Zapis pinów z historią zboczy sygnału życia."""

    def __init__(self) -> None:
        self.value: dict[str, bool] = {}
        self.hb_edges = 0

    def write(self, name: str, value: bool) -> None:
        if name == PINS["hb"] and name in self.value and self.value[name] != value:
            self.hb_edges += 1
        self.value[name] = value


def make(machine: FakeMachine | None = None):
    clock, pins = Clock(), Pins()
    hal = HalPins(pins.write, clock())
    gateway = Gateway(FakeBackend(machine or FakeMachine()), clock=clock, hal_pins=hal)
    return gateway, clock, pins


def run(gateway: Gateway, clock: Clock, seconds: float, session: str | None = None) -> None:
    for _ in range(round(seconds / 0.02)):
        clock.t += 0.02
        if session is not None:
            gateway.touch(session)
        gateway.step()


def test_start_state_is_fail_safe_and_arms_after_delay():  # REQ-QA-03
    gateway, clock, pins = make()
    assert pins.value == {PINS["wd"]: False, PINS["ack"]: False, PINS["hb"]: False,
                          PINS["ok"]: True}
    run(gateway, clock, ARM_DELAY_S - 0.05)
    assert pins.value[PINS["wd"]] is False
    run(gateway, clock, 0.1)
    assert pins.value[PINS["wd"]] is True  # zbocze uzbrojenia
    assert gateway.snapshot()[1]["hmi_hal"] is True


def test_heartbeat_toggles_only_while_browser_alive():  # REQ-QA-03
    gateway, clock, pins = make()
    run(gateway, clock, 1.0)
    assert pins.hb_edges == 0  # brak przeglądarki = brak sygnału życia
    gateway.client_connected("s1")
    run(gateway, clock, 1.0, session="s1")
    assert pins.hb_edges >= 45  # ~50 obiegów/s, zbocze w każdym
    edges = pins.hb_edges
    run(gateway, clock, HEARTBEAT_S + 0.1)  # karta milczy
    silent = pins.hb_edges
    run(gateway, clock, 1.0)
    assert pins.hb_edges == silent > edges  # po HEARTBEAT_S zbocza ustają
    gateway.client_disconnected("s1")
    run(gateway, clock, 0.5)
    assert pins.hb_edges == silent


def test_stopped_gateway_gives_no_heartbeat():  # REQ-QA-03
    """Zawieszona brama (brak obiegów) nie przełącza pinu: watchdog HAL dostaje ciszę."""
    gateway, clock, pins = make()
    gateway.client_connected("s1")
    run(gateway, clock, 0.5, session="s1")
    edges = pins.hb_edges
    clock.t += 5.0
    gateway.touch("s1")  # przeglądarka żyje, ale obieg bramy nie biegnie
    assert pins.hb_edges == edges


def test_double_reset_acknowledges_estop_through_hal():  # REQ-QA-03
    machine = FakeMachine()  # start w E-STOP
    gateway, clock, pins = make(machine)
    gateway.client_connected("s1")
    run(gateway, clock, 1.0, session="s1")
    assert gateway.snapshot()[1]["task_state"] == "estop"
    gateway.execute(Command(cmd="reset"), "s1")  # pojedynczy: tylko alarmy
    run(gateway, clock, 1.0, session="s1")
    assert gateway.snapshot()[1]["task_state"] == "estop"
    assert pins.value[PINS["ack"]] is False
    gateway.execute(Command(cmd="reset", double=True), "s1")
    assert pins.value[PINS["ack"]] is True and pins.value[PINS["wd"]] is False
    run(gateway, clock, PULSE_S + 0.02, session="s1")
    assert pins.value[PINS["ack"]] is False and pins.value[PINS["wd"]] is True  # ponowne uzbrojenie
    assert gateway.snapshot()[1]["task_state"] == "estop"  # reset dopiero po impulsie
    run(gateway, clock, ESTOP_RESET_DELAY_S, session="s1")
    assert gateway.snapshot()[1]["task_state"] == "estop_reset"
    assert any(a["code"] == "E-1100" for a in gateway.snapshot()[1]["alarms"])
    run(gateway, clock, ALARM_RESET_DELAY_S + 0.05, session="s1")
    assert gateway.snapshot()[1]["alarms"] == []  # jak Qt: alarm E-STOP skasowany po resecie


def test_double_reset_outside_estop_sends_no_ack():  # REQ-QA-03
    machine = FakeMachine()
    machine.estop_reset()
    gateway, clock, pins = make(machine)
    gateway.client_connected("s1")
    run(gateway, clock, 1.0, session="s1")
    gateway.execute(Command(cmd="reset", double=True), "s1")
    assert pins.value[PINS["ack"]] is False
    run(gateway, clock, 1.0, session="s1")
    assert gateway.snapshot()[1]["task_state"] == "estop_reset"


def test_double_reset_without_hal_is_refused():  # REQ-QA-03
    gateway = Gateway(FakeBackend(FakeMachine()))
    with pytest.raises(CommandError, match="--hal"):
        gateway.execute(Command(cmd="reset", double=True))
    assert gateway.snapshot()[1]["task_state"] == "estop"
    assert gateway.snapshot()[1]["hmi_hal"] is False


@pytest.mark.parametrize("command", ["estop", "power_off", "stop"])
def test_new_stop_cancels_old_reset_and_allows_fresh_ack(command):  # REQ-QA-03
    gateway, clock, pins = make()
    gateway.execute(Command(cmd="reset", double=True))
    clock.t += PULSE_S + 0.02
    if command == "power_off":
        # Atrapa odmawia wyłączenia już wyłączonej maszyny; stary reset i tak musi wygasnąć.
        with pytest.raises(CommandError):
            gateway.execute(Command(cmd=command))
    else:
        gateway.execute(Command(cmd=command))
    gateway.step()
    expected = gateway.snapshot()[1]["task_state"]
    run(gateway, clock, 1.0)
    assert gateway.snapshot()[1]["task_state"] == expected
    assert gateway._estop_reset_at is None and gateway._alarm_reset_at is None
    assert pins.value[PINS["ack"]] is False and pins.value[PINS["wd"]] is False
    gateway.execute(Command(cmd="estop"))
    gateway.step()
    gateway.execute(Command(cmd="reset", double=True))
    run(gateway, clock, ESTOP_RESET_DELAY_S + 0.1)
    assert gateway.snapshot()[1]["task_state"] == "estop_reset"


def test_stop_without_pending_reset_does_not_disarm_watchdog():  # REQ-QA-03
    gateway, clock, pins = make()
    run(gateway, clock, ARM_DELAY_S + 0.1)
    gateway.execute(Command(cmd="stop"))
    assert pins.value[PINS["wd"]] is True


@pytest.mark.parametrize("command", ["estop", "power_off", "stop"])
def test_failed_hal_write_does_not_block_stop_delivery(command):  # REQ-QA-03
    gateway, clock, pins = make()
    gateway.execute(Command(cmd="reset", double=True))
    calls = []
    setattr(gateway.backend, command, lambda: calls.append(command))
    def broken_write(name, value):
        raise RuntimeError("HAL write failed")
    gateway._hal._write = broken_write
    with pytest.raises(RuntimeError, match="HAL write failed"):
        gateway.execute(Command(cmd=command))
    assert calls == [command]
    assert gateway._estop_reset_at is None


def test_refused_estop_reset_becomes_alarm():  # REQ-QA-03
    class Refusing(FakeBackend):
        def estop_reset(self) -> None:
            raise CommandError("obwód safety otwarty")

    clock, pins = Clock(), Pins()
    gateway = Gateway(Refusing(FakeMachine()), clock=clock,
                      hal_pins=HalPins(pins.write, clock()))
    gateway.client_connected("s1")
    run(gateway, clock, 0.5, session="s1")
    gateway.execute(Command(cmd="reset", double=True), "s1")
    run(gateway, clock, 1.0, session="s1")
    texts = [a["text"] for a in gateway.snapshot()[1]["alarms"]]
    assert any("obwód safety otwarty" in t for t in texts), texts
