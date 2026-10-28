"""Domena ``machine``: sterowanie przez kontrakt na atrapie maszyny.

SPDX-License-Identifier: GPL-2.0-or-later

Sprawdzamy ścieżkę, którą pójdzie GUI: operacja → walidacja → port maszyny → migawka stanu.
Bez LinuxCNC i bez X — backend to atrapa z zegarem sterowanym ręcznie, więc ruch postępuje
tylko wtedy, gdy test przesunie zegar (``clock``).
"""

from __future__ import annotations

import time

import pytest

from linumert_headless.errors import ApiError


def test_migawka_stanu_ma_osie_i_backend(call) -> None:
    state = call("machine.state")
    assert [a["name"] for a in state["axes"]] == ["X", "Y", "Z"]
    assert state["backend"] == "fake"
    assert state["task_state"] == "estop"
    assert state["schema_version"] >= 1


def test_sekwencja_operatora_estop_zasilanie_bazowanie_jog(ready_machine, clock) -> None:
    call = ready_machine
    assert call("machine.state")["all_homed"] is True

    assert call("machine.set_mode", {"mode": "manual"})["ok"] is True
    assert call("machine.jog", {"axis": "X", "speed": 10.0, "session": "test"})["ok"] is True
    clock(0.5)
    moved = call("machine.state")["axes"][0]["position"]
    assert moved == pytest.approx(5.0, abs=0.001)

    assert call("machine.jog_stop", {"axis": None})["ok"] is True
    clock(0.5)
    assert call("machine.state")["axes"][0]["position"] == pytest.approx(moved, abs=1e-6)


def test_bazowanie_trwa_w_czasie_wirtualnym(call, clock) -> None:
    """Bazowanie jest ruchem w kolejce atrapy — stan ``homed`` pojawia się po czasie."""
    call("machine.estop_reset")
    call("machine.power_on")
    assert call("machine.home")["ok"] is True
    assert call("machine.state")["all_homed"] is False
    clock(5.0)
    assert call("machine.state")["all_homed"] is True


def test_ruch_bez_zasilania_jest_odmowiony(call) -> None:
    call("machine.estop")
    with pytest.raises(ApiError) as excinfo:
        call("machine.home", {"axis": "X"})
    assert excinfo.value.code == "safety_refused"


def test_jog_poza_zakresem_predkosci_jest_odrzucony(ready_machine) -> None:
    with pytest.raises(ApiError) as excinfo:
        ready_machine("machine.jog", {"axis": "X", "speed": 900.0, "session": "t"})
    assert excinfo.value.code in {"invalid_request", "safety_refused"}


def test_deadman_jogu_zatrzymuje_os(ready_machine, clock, app) -> None:
    call = ready_machine
    call("machine.set_mode", {"mode": "manual"})
    call("machine.jog", {"axis": "Y", "speed": 20.0, "session": "s1"})
    clock(0.1)

    # Sesja przestała odświeżać jog — deadman musi wygasić ruch.
    app.sessions._jog["Y"] = ("s1", time.monotonic() - 1.0)
    assert app.services["machine"].expired_jog() == ["Y"]
    clock(0.5)
    before = call("machine.state")["axes"][1]["position"]
    clock(0.5)
    assert call("machine.state")["axes"][1]["position"] == pytest.approx(before, abs=1e-6)


def test_jog_nalezy_do_jednej_sesji(ready_machine) -> None:
    call = ready_machine
    call("machine.set_mode", {"mode": "manual"})
    call("machine.jog", {"axis": "Z", "speed": 5.0, "session": "właściciel"})
    with pytest.raises(ApiError) as excinfo:
        call("machine.jog", {"axis": "Z", "speed": 5.0, "session": "inna"})
    assert excinfo.value.code == "conflict"


def test_jog_przyrostowy_zatrzymuje_sie_po_dystansie(ready_machine, clock) -> None:
    call = ready_machine
    call("machine.set_mode", {"mode": "manual"})
    assert call("machine.jog_increment",
                {"axis": "X", "speed": 10.0, "distance": 2.0})["ok"] is True
    clock(2.0)
    position = call("machine.state")["axes"][0]["position"]
    assert position == pytest.approx(2.0, abs=0.05)
    clock(2.0)
    assert call("machine.state")["axes"][0]["position"] == pytest.approx(position, abs=1e-6)


def test_mdi_wymaga_trybu_mdi(ready_machine) -> None:
    call = ready_machine
    call("machine.set_mode", {"mode": "mdi"})
    assert call("machine.mdi", {"text": "G0 X10"})["ok"] is True


def test_wrzeciono_i_nastawy(ready_machine, clock) -> None:
    call = ready_machine
    call("machine.set_mode", {"mode": "mdi"})
    assert call("machine.spindle", {"speed": 12000, "direction": 1})["ok"] is True
    assert call("machine.set_override", {"feed": 0.5})["ok"] is True
    assert call("machine.state")["feed_override"] == 0.5


def test_program_auto_pauza_stop(ready_machine, clock) -> None:
    """AUTO na programie, który atrapa interpretuje (``linumert_neon_demo.ngc``)."""
    call = ready_machine
    assert call("program.read", {"name": "linumert_neon_demo.ngc"})["text"]
    assert call("program.load", {"name": "linumert_neon_demo.ngc"})["ok"] is True
    call("machine.set_mode", {"mode": "auto"})
    assert call("machine.run", {"from_line": 1})["ok"] is True
    clock(0.5)
    running = call("machine.state")
    assert running["interp_state"] == "reading"
    assert running["current_line"] > 0

    assert call("machine.pause")["ok"] is True
    assert call("machine.state")["interp_state"] == "paused"
    assert call("machine.resume")["ok"] is True
    assert call("machine.stop")["ok"] is True


def test_blad_interpretatora_trafia_do_migawki(ready_machine, clock) -> None:
    """Nieobsłużony kod G przerywa program i jest widoczny w ``machine.state().errors``."""
    call = ready_machine
    call("program.load", {"name": "linumert_demo.ngc"})
    call("machine.set_mode", {"mode": "auto"})
    assert call("machine.run", {"from_line": 1})["ok"] is True
    clock(1.0)
    state = call("machine.state")
    assert any("G43" in error for error in state["errors"]), state["errors"]
    assert state["interp_state"] == "idle"


def test_mdi_z_nieobsluzonym_kodem_jest_odrzucone(ready_machine) -> None:
    """Atrapa odmawia MDI, którego nie interpretuje — GUI dostaje ``conflict``."""
    call = ready_machine
    call("machine.set_mode", {"mode": "mdi"})
    with pytest.raises(ApiError) as excinfo:
        call("machine.mdi", {"text": "G43 H1 Z10"})
    assert excinfo.value.code == "conflict"


def test_offset_pracy_idzie_przez_backend(ready_machine) -> None:
    call = ready_machine
    assert call("machine.set_work_offset",
                {"name": "G54", "values": {"X": 10.0, "Y": 5.0}})["ok"] is True
    state = call("machine.state")
    assert state["work_offset_name"] == "G54"


def test_stan_publikowany_jest_w_magazynie(app) -> None:
    app.publish_state()
    topics = app.hub.snapshot()["topics"]
    assert "machine" in topics and "alarms" in topics
    assert topics["machine"]["backend"] == "fake"


def test_pętla_stanu_odswieza_migawke(app, call, clock) -> None:
    """Pętla 50 Hz publikuje stan — GUI dostaje push zamiast odpytywać maszynę."""
    call("machine.estop_reset")
    call("machine.power_on")
    call("machine.home")
    clock(5.0)
    app.start()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        machine = app.hub.get("machine")
        if machine and machine.get("all_homed"):
            break
        time.sleep(0.02)
    app.stop()
    assert app.hub.get("machine")["all_homed"] is True


def test_backend_linuxcnc_ma_zegar_czytnika() -> None:
    """`now()` wołało nieistniejące `self._clock` — każdy `machine.state` padał."""
    from linumert.cnc.linuxcnc_reader import LinuxCNCReader
    from linumert_headless.backends.linuxcnc import LinuxCNCBackend

    backend = LinuxCNCBackend(module=object(), reader=LinuxCNCReader(module=object(),
                                                                     clock=lambda: 42.0))
    assert backend.now() == 42.0
    assert "subroutines" in backend.capabilities
