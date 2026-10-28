"""Kontrakt operacji: kompletność, spójność i eksport dla GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Kontrakt jest jedynym źródłem prawdy dla REST, WebSocket, CLI, SDK i przyszłego GUI, więc
jego kształt jest testowany osobno: każda operacja ma domenę, schematy i status, a funkcje
niewdrożone są jawnie oznaczone zamiast udawać działanie.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linumert_headless import __version__

BETA = Path(__file__).resolve().parent.parent

REQUIRED_DOMAINS = {
    "access", "alarm", "cam", "config", "diag", "machine",
    "offset", "plant", "program", "sim", "system", "tool",
}

REQUIRED_OPERATIONS = {
    "system.info", "system.health", "system.contract", "system.state",
    "machine.state", "machine.estop", "machine.power_on", "machine.home",
    "machine.jog", "machine.jog_stop", "machine.mdi", "machine.run",
    "program.list", "program.read", "program.write", "program.compile",
    "program.check", "program.estimate", "program.toolpath",
    "tool.list", "tool.upsert", "tool.export_tbl", "tool.import_tbl", "tool.history",
    "cam.operations", "cam.generate",
    "offset.stock_set", "offset.workpiece_get", "offset.workpiece_set",
    "sim.run",
    "plant.status", "plant.start", "plant.scenario_run", "plant.drives",
    "plant.faults", "plant.machine_drives",
    "config.machines", "config.generate",
    "alarm.list", "alarm.ack", "alarm.codes",
    "diag.doctor", "diag.journal", "diag.journal_csv", "diag.cia402",
    "access.login", "access.logout", "access.session", "access.roles",
    "access.audit", "access.set_pin", "access.clear_pin",
}


def test_wszystkie_domeny_sa_obslugiwane(app) -> None:
    assert set(app.contract.domains()) == REQUIRED_DOMAINS


def test_wymagane_operacje_sa_zarejestrowane(app) -> None:
    names = {o.name for o in app.contract.operations()}
    missing = REQUIRED_OPERATIONS - names
    assert not missing, f"brak operacji w kontrakcie: {sorted(missing)}"


def test_kazda_operacja_ma_poprawny_opis(app) -> None:
    for operation in app.contract.operations():
        assert operation.summary, f"{operation.name}: brak podsumowania"
        assert operation.kind in {"command", "query"}
        assert operation.status in {"implemented", "planned"}
        assert operation.role in {"operator", "technolog", "serwis"}
        assert operation.safety in {"none", "motion", "stop", "config"}
        assert operation.domain == operation.name.split(".", 1)[0]


def test_polecenia_stop_nie_podlegaja_limiterowi(app) -> None:
    """E-STOP i stop muszą przejść nawet po wyczerpaniu tokenów."""
    from linumert_headless.errors import RateLimited

    stopping = {o.name for o in app.contract.operations() if o.safety == "stop"}
    assert {"machine.estop", "machine.stop", "machine.jog_stop"} <= stopping

    # Drenujemy wiadro tokenów do zera.
    drained = 0
    while app.sessions._limiter.allow() and drained < 1000:
        drained += 1
    assert drained > 0
    with pytest.raises(RateLimited):
        app.call("machine.mdi", {"text": "G0 X1"})
    # Polecenia zatrzymujące przechodzą mimo to — to warunek bezpieczeństwa obsługi.
    assert app.call("machine.estop").ok is True
    assert app.call("machine.stop").ok is True


def _line(lines: list[str], number: int) -> str:
    """Fragment linii do komunikatu błędu (pełne wiersze kontraktu są za długie)."""
    return lines[number - 1][:90] if 1 <= number <= len(lines) else "<brak>"


def test_zatwierdzony_contract_json_jest_zsynchronizowany_z_kodem(app) -> None:
    """``api/contract.json`` musi być dokładnie tym, co generuje ``linumertd contract``.

    Plik jest zatwierdzony w repo i służy autorom GUI do codegen, więc cicha rozbieżność
    z kodem (zmiana schematu bez regeneracji) oszukałaby ich: GUI zbudowane na starym
    kontrakcie wysyłałoby pola, których usługa już nie przyjmuje. Porównanie dotyczy
    całych bajtów, nie tylko parsowalności — tak samo zapisuje CLI
    (``json.dumps(..., ensure_ascii=False, indent=2)``, bez końcowej nowej linii).
    """
    path = BETA / "api" / "contract.json"
    assert path.exists(), f"brak zatwierdzonego kontraktu: {path}"
    payload = app.contract.export(application="linumeRT headless", version=__version__)
    generated = json.dumps(payload, ensure_ascii=False, indent=2)
    committed = path.read_text(encoding="utf-8")
    if generated != committed:
        gen_lines = generated.splitlines()
        com_lines = committed.splitlines()
        pairs = zip(gen_lines, com_lines, strict=False)
        first = next((i for i, (a, b) in enumerate(pairs, 1) if a != b),
                     min(len(gen_lines), len(com_lines)) + 1)
        raise AssertionError(
            f"api/contract.json rozjechany z kodem (pierwsza różnica w linii {first}; "
            f"{len(com_lines)} -> {len(gen_lines)} linii). "
            f"Zregeneruj: python -m linumert_headless contract --out api/contract.json\n"
            f"  zatwierdzone: {_line(com_lines, first)}\n"
            f"  wygenerowane: {_line(gen_lines, first)}")


def test_eksport_kontraktu_jest_jsonem_dla_gui(app) -> None:
    payload = app.contract.export(application="test", version="0.0.0")
    text = json.dumps(payload)  # musi być serializowalny bez wiedzy o Pythonie
    assert len(payload["operations"]) == len(app.contract.operations())
    for item in payload["operations"]:
        assert {"name", "domain", "kind", "status", "safety", "role",
                "request", "result"} <= set(item)
        assert item["request"].get("type") == "object"
    assert payload["events"], "kontrakt musi opisywać zdarzenia stanu dla GUI"
    assert json.loads(text)


def test_operacje_planned_zglaszaja_not_implemented_z_planem(app) -> None:
    # Wszystkie operacje są wdrożone; mechanizm "planned" zostaje dla przyszłych funkcji,
    # więc sprawdzamy go na operacji dopisanej w teście.
    app.contract.command("system.przyszla_funkcja", domain="system", summary="test",
                         status="planned", plan="opis wdrożenia")
    planned = [o for o in app.contract.operations() if o.status == "planned"]
    assert [o.name for o in planned] == ["system.przyszla_funkcja"]
    for operation in planned:
        assert operation.plan, f"{operation.name}: brak opisu planu wdrożenia"
        with pytest.raises(Exception) as excinfo:
            app.call(operation.name)
        assert excinfo.value.code == "not_implemented"
        assert excinfo.value.details["plan"]


def test_nieznana_operacja_daje_czytelny_blad(app) -> None:
    with pytest.raises(Exception) as excinfo:
        app.call("machine.nie_ma_takiej")
    assert excinfo.value.code == "not_found"
    assert "known" in excinfo.value.details


def test_zle_parametry_daja_invalid_request_z_listą_bledow(app) -> None:
    with pytest.raises(Exception) as excinfo:
        app.call("machine.jog", {"axis": "Q", "speed": 1.0})
    assert excinfo.value.code == "invalid_request"
    assert excinfo.value.details["errors"]


def test_kazda_operacja_ma_test_lub_jest_planned(app) -> None:
    """Każda wdrożona operacja musi dać się wywołać (albo wymagać backendu/konfiguracji)."""
    from linumert_headless.errors import ApiError

    for operation in app.contract.operations():
        if operation.status == "planned":
            continue
        assert callable(app.contract._handlers[operation.name]), operation.name
        # Wywołanie bez parametrów: albo działa, albo zgłasza błąd z kontraktu.
        try:
            app.call(operation.name, {})
        except ApiError:
            pass
