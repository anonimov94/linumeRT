"""Kontrakt operacji: kompletność, spójność i eksport dla GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Kontrakt jest jedynym źródłem prawdy dla REST, WebSocket, CLI, SDK i przyszłego GUI, więc
jego kształt jest testowany osobno: każda operacja ma domenę, schematy i status, a funkcje
niewdrożone są jawnie oznaczone zamiast udawać działanie.
"""

from __future__ import annotations

import json

import pytest

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
    "tool.list", "tool.upsert", "tool.export_tbl",
    "cam.operations", "cam.generate",
    "offset.stock_set", "offset.workpiece_get",
    "sim.run",
    "plant.status", "plant.start", "plant.scenario_run", "plant.drives",
    "config.machines", "config.generate",
    "alarm.list", "alarm.ack",
    "diag.doctor", "diag.journal", "diag.cia402",
    "access.login", "access.session",
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
    planned = [o for o in app.contract.operations() if o.status == "planned"]
    assert planned, "kontrakt powinien pokazywać zakres funkcji planowanych"
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
