"""Integracja dekodera CiA 402 ze stanami napędów wirtualnej maszyny Plant.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT (koordynacja: Claude)

Testy z rdzeniem C są pomijane, jeśli kompilacja biblioteki nie jest dostępna.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_master import Master, drive_state

from linumert.diag.cia402 import CiA402State, decode_statusword, describe_error_code
from linumert_plant.server import PlantConfig, PlantServer

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


def _server(core, **cfg) -> PlantServer:
    from linumert_plant.build_machine import build_machine

    seed = 1
    machine = core.PlantMachine(build_machine(MACHINE, seed=seed))
    return PlantServer(machine, PlantConfig(seed=seed, **cfg))


def _local(server: PlantServer) -> Master:
    return Master(len(server.drives), transport=server.handle)


def test_statusword_matches_plant_master_for_all_16bit_values() -> None:
    """Porównanie nie wymaga rdzenia C Plant ani interfejsu operatorskiego."""
    aliases = {
        CiA402State.FAULT: "FAULT",
        CiA402State.FAULT_REACTION_ACTIVE: "FAULT",
        CiA402State.NOT_READY_TO_SWITCH_ON: "NOT_READY",
        CiA402State.UNKNOWN: "NOT_READY",
    }
    for word in range(0x10000):
        state = decode_statusword(word).state
        expected = aliases.get(state, state.name)
        observed = drive_state(word)
        assert observed == expected, (
            f"statusword=0x{word:04X}, dekoder={state.name}, master={observed}"
        )


def test_watchdog_fault_visible_in_diagnostics_and_reset(core) -> None:  # REQ-QA-03
    server = _server(core, watchdog_ms=50)
    master = _local(server)
    master.enable()

    for _ in range(5):
        master.exchange()
    assert len(master.last.axes) == len(server.drives)
    for axis in master.last.axes:
        assert decode_statusword(axis.statusword).state is CiA402State.OPERATION_ENABLED

    for _ in range(50):
        master.exchange()
    master.exchange(advance_ns=60_000_000)  # odstęp następnej ramki: 61 ms
    master.exchange()

    assert server.watchdog_tripped
    for axis in master.last.axes:
        result = decode_statusword(axis.statusword)
        assert result.state is CiA402State.FAULT
        assert result.description
        assert axis.error_code == 0x8130
        assert describe_error_code(axis.error_code) == (
            "Problem z komunikacją napędu (0x8130)"
        )

    master.enable()  # fault reset i ponowne załączenie wszystkich osi
    for _ in range(5):
        master.exchange()
    assert not server.watchdog_tripped
    for axis in master.last.axes:
        assert decode_statusword(axis.statusword).state is CiA402State.OPERATION_ENABLED


def test_injected_single_drive_fault_isolated_in_diagnostics(core) -> None:  # REQ-QA-03
    server = _server(core)
    master = _local(server)
    master.enable()
    for _ in range(5):
        master.exchange()

    # drive.h: LRT_DRIVE_FAULT_OVERLOAD = 3, kod 603Fh = 0x2350.
    drive = server.drives[0]
    server.machine.inject_fault(drive, 3, sticky=True)
    for _ in range(5):
        master.exchange()

    states = [decode_statusword(axis.statusword).state for axis in master.last.axes]
    assert states[0] in {CiA402State.FAULT, CiA402State.FAULT_REACTION_ACTIVE}
    assert all(state is CiA402State.OPERATION_ENABLED for state in states[1:])

    error_code = master.last.axes[0].error_code
    description = describe_error_code(error_code)
    assert error_code == 0x2350, f"napęd {drive}: 0x{error_code:04X}"
    assert description and "Nierozpoznana" not in description, (
        f"napęd {drive}: 0x{error_code:04X}, opis: {description}"
    )
