"""Makra ruchu przez kontrakt: zmiana narzędzia (M6) i sondowanie (``o<lrt_probe>``).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Atrapa wykonuje ``T<n> M6`` sama (bez tabeli narzędzi), więc zmianę narzędzia widać
w migawce. Sondowania atrapa nie wykona (brak G38.x i podprogramów) — sprawdzamy jawną
odmowę, a ścieżkę LinuxCNC na atrapie z zapisem wysłanych poleceń MDI.
Rzeczywiste wykonanie makra w LinuxCNC: NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import re

import pytest
from conftest import BETA

from linumert.programs.probe_macro import PROBE_MACRO, probe_call
from linumert_headless.errors import ApiError


def _mdi(call) -> None:
    call("machine.set_mode", {"mode": "mdi"})


# --------------------------------------------------------------------------- M6


def test_zmiana_narzedzia_wymaga_potwierdzenia(ready_machine) -> None:
    with pytest.raises(ApiError) as excinfo:
        ready_machine("machine.tool_change", {"tool": 1})
    assert excinfo.value.code == "safety_refused"
    assert "potwierdzenia" in excinfo.value.message


def test_zmiana_narzedzia_t_m6_zmienia_narzedzie_w_uchwycie(ready_machine) -> None:
    result = ready_machine("machine.tool_change", {"tool": 1, "confirm": True})
    assert result["details"]["gcode"] == "T1 M6"
    assert result["details"]["previous"] == 0
    assert ready_machine("machine.state")["tool_number"] == 1
    again = ready_machine("machine.tool_change", {"tool": 1, "confirm": True})
    assert "już w uchwycie" in again["message"]


def test_zmiana_na_narzedzie_spoza_bazy_jest_odrzucona(ready_machine) -> None:
    with pytest.raises(ApiError) as excinfo:
        ready_machine("machine.tool_change", {"tool": 777, "confirm": True})
    assert excinfo.value.code == "not_found"
    assert ready_machine("machine.state")["tool_number"] == 0


def test_zmiana_narzedzia_przy_pracujacym_wrzecionie_jest_odrzucona(ready_machine) -> None:
    _mdi(ready_machine)
    ready_machine("machine.mdi", {"text": "S8000 M3"})
    with pytest.raises(ApiError) as excinfo:
        ready_machine("machine.tool_change", {"tool": 1, "confirm": True})
    assert excinfo.value.code == "safety_refused"
    assert "wrzecion" in excinfo.value.message


def test_zmiana_narzedzia_bez_bazowania_jest_odrzucona(call) -> None:
    call("machine.estop_reset")
    call("machine.power_on")
    with pytest.raises(ApiError) as excinfo:
        call("machine.tool_change", {"tool": 1, "confirm": True})
    assert excinfo.value.code == "safety_refused"
    assert "zbazowanych" in excinfo.value.message


# --------------------------------------------------------------------------- sonda


@pytest.fixture
def linuxcnc_like(app, monkeypatch):
    """Atrapa udająca backend z podprogramami: zapisuje MDI zamiast wykonywać makro."""
    sent: list[str] = []
    monkeypatch.setattr(app.backend, "capabilities", frozenset({"subroutines"}),
                        raising=False)
    monkeypatch.setattr(app.backend, "mdi", sent.append)
    return sent


def test_sondowanie_na_atrapie_jest_jawnie_odrzucone(ready_machine) -> None:
    with pytest.raises(ApiError) as excinfo:
        ready_machine("offset.probe_run", {"axis": "Z", "direction": -1, "confirm": True})
    assert excinfo.value.code == "conflict"
    assert "LinuxCNC" in excinfo.value.message


def test_sondowanie_wymaga_potwierdzenia(ready_machine, linuxcnc_like) -> None:
    with pytest.raises(ApiError) as excinfo:
        ready_machine("offset.probe_run", {"axis": "Z", "direction": -1})
    assert excinfo.value.code == "safety_refused"
    assert linuxcnc_like == []


def test_sondowanie_wysyla_jedno_wywolanie_makra(ready_machine, linuxcnc_like) -> None:
    result = ready_machine("offset.probe_run",
                           {"axis": "z", "direction": -1, "distance": 25, "offset": "G55",
                            "value": 10.0, "confirm": True})
    assert linuxcnc_like == ["o<lrt_probe> call [2] [-1] [25] [100] [2] [10] [2]"]
    assert result["gcode"] == linuxcnc_like[0]
    assert result["axis"] == "Z" and result["correction"] == 0.0 and result["feed"] == 100.0
    assert ready_machine("machine.state")["mode"] == "mdi"


def test_sondowanie_uwzglednia_kalibracje_i_jej_posuw(ready_machine, linuxcnc_like) -> None:
    ready_machine("offset.probe_calibrate",
                  {"axis": "Z", "direction": -1, "measured": [5.004, 5.006],
                   "true_value": 5.0})
    result = ready_machine("offset.probe_run",
                           {"axis": "Z", "direction": -1, "value": 0.0, "confirm": True})
    # Odczyt sondy jest o 0,005 mm za wysoko: punkt styku dostaje 0 - (-0,005) = 0,005.
    assert result["correction"] == pytest.approx(-0.005, abs=1e-9)
    assert linuxcnc_like[-1].endswith("[1] [0.005] [2]")

    with pytest.raises(ApiError) as excinfo:
        ready_machine("offset.probe_run",
                      {"axis": "Z", "direction": -1, "feed": 250, "confirm": True})
    assert excinfo.value.code == "invalid_request"
    assert excinfo.value.details["calibration_feed"] == 100.0
    assert len(linuxcnc_like) == 1


def test_sondowanie_odrzuca_osie_obrotowe_i_brak_osi(ready_machine, linuxcnc_like) -> None:
    with pytest.raises(ApiError) as excinfo:
        ready_machine("offset.probe_run", {"axis": "A", "direction": 1, "confirm": True})
    assert excinfo.value.code == "invalid_request"
    with pytest.raises(ApiError) as excinfo:
        ready_machine("offset.probe_run",
                      {"axis": "Z", "direction": -1, "distance": 500, "confirm": True})
    assert excinfo.value.code == "invalid_request"
    assert linuxcnc_like == []


# --------------------------------------------------------------------------- makro


def test_wywolanie_pasuje_do_sygnatury_makra() -> None:
    call = probe_call("Y", 1, 12.5, 80, "G59.3", -1.25, 3)
    assert call == "o<lrt_probe> call [1] [1] [12.5] [80] [9] [-1.25] [3]"
    used = {int(n) for n in re.findall(r"#(\d)\b", PROBE_MACRO)}
    assert used == set(range(1, 8)), "makro czyta dokładnie 7 argumentów wywołania"
    for axis, param in (("X", 5061), ("Y", 5062), ("Z", 5063)):
        assert f"G38.2 {axis}#<dist>" in PROBE_MACRO
        assert f"G10 L20 P#5 {axis}[#<_{axis.lower()}> - #{param} + #6]" in PROBE_MACRO


def test_makro_jest_w_konfiguracjach_i_generatorze() -> None:
    for path in ("config/sim/linumert_xyz/macros/lrt_probe.ngc",
                 "config/plant/linumert_plant_xyz/macros/lrt_probe.ngc"):
        assert (BETA / path).read_text(encoding="utf-8") == PROBE_MACRO, path

    from linumert.machine import configgen
    from linumert.machine.schema import load_machine

    cfg = load_machine(BETA / "config/machines/router_gantry_steppers.yaml")
    files = configgen.render(cfg, "sim")
    assert files["macros/lrt_probe.ngc"] == PROBE_MACRO


def test_wygenerowany_kontrakt_nie_ma_operacji_planowanych() -> None:
    contract = json.loads((BETA / "api/contract.json").read_text(encoding="utf-8"))
    planned = [o["name"] for o in contract["operations"] if o["status"] == "planned"]
    assert planned == []
