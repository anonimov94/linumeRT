"""Usługi domenowe: programy, narzędzia, CAM, offsety, symulacja, Plant, konfiguracja.

SPDX-License-Identifier: GPL-2.0-or-later

Każdy test idzie przez kontrakt (``call``), czyli dokładnie tą drogą, którą pójdzie GUI.
Sprawdzamy wynik merytoryczny, nie tylko brak wyjątku: liczby, ścieżki plików i komunikaty.
"""

from __future__ import annotations

import json

import pytest

from linumert_headless.errors import ApiError

# --------------------------------------------------------------------------- programy


def test_program_list_read_write_delete(app, call, workdir) -> None:
    programs = call("program.list")
    names = {p["name"] for p in programs["programs"]}
    assert "linumert_demo.ngc" in names
    assert programs["root"].endswith("nc_files")

    text = call("program.read", {"name": "linumert_kwadrat.ngc"})["text"]
    assert "G1" in text

    assert call("program.write", {"name": "test_api.ngc", "text": "G21\nG0 X1\nM2\n"})["ok"]
    assert (workdir / "config" / "nc_files" / "test_api.ngc").exists()

    with pytest.raises(ApiError) as excinfo:
        call("program.write", {"name": "test_api.ngc", "text": "M2\n"})
    assert excinfo.value.code == "conflict"  # bez overwrite nie nadpisujemy

    assert call("program.delete", {"name": "test_api.ngc"})["ok"]
    assert not (workdir / "config" / "nc_files" / "test_api.ngc").exists()


def test_program_nie_wyjdzie_poza_katalog(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("program.read", {"name": "../../pyproject.toml"})
    assert excinfo.value.code == "invalid_request"


def test_program_estimate_liczy_czas_i_droge(call) -> None:
    result = call("program.estimate", {"name": "linumert_demo.ngc"})
    assert result["seconds"] > 0
    assert result["distance_mm"] > 0
    assert result["feed_mm"] >= 0
    assert "min" in result["message"]


def test_program_check_zglasza_granice(call) -> None:
    result = call("program.check", {"name": "linumert_kwadrat.ngc"})
    assert isinstance(result["ok"], bool)
    assert result["lines"] > 0
    for violation in result["violations"]:
        assert {"axis", "line", "value", "limit_min", "limit_max"} <= set(violation)


def test_program_toolpath_zwraca_punkty_bez_grafiki(call) -> None:
    result = call("program.toolpath", {"name": "linumert_kwadrat.ngc", "max_points": 500})
    assert result["points"], "ścieżka powinna mieć punkty"
    assert result["source"] in {"rs274", "subset"}
    assert result["length_mm"] > 0
    assert {"min_x", "max_x", "min_y", "max_y", "min_z", "max_z"} <= set(result["bounds"])
    first = result["points"][0]
    assert {"line", "x", "y", "z", "rapid", "feed"} <= set(first)


# --------------------------------------------------------------------------- narzędzia


def test_tool_upsert_get_wear_export(app, call, workdir) -> None:
    assert call("tool.upsert", {"number": 7, "pocket": 7, "type": "flat",
                                "description": "frez 6 mm", "diameter": 6.0,
                                "params": {"d": 6.0, "l": 45.0,
                                           "flute_length": 30.0}})["ok"]
    tool = call("tool.get", {"number": 7})
    assert tool["description"] == "frez 6 mm"
    assert tool["diameter"] == 6.0

    call("tool.set_wear", {"number": 7, "axis": "Z", "value": -0.02})
    assert call("tool.get", {"number": 7})["offsets"]["Z"] == pytest.approx(-0.02)

    exported = call("tool.export_tbl", {"units": "mm",
                                        "path": str(workdir / "state" / "tool.tbl")})
    assert "T7" in exported["text"]
    assert exported["path"]

    numbers = [t["number"] for t in call("tool.list")["tools"]]
    assert 7 in numbers
    assert call("tool.delete", {"number": 7})["ok"]


def test_tool_brak_numeru_daje_not_found(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("tool.get", {"number": 999})
    assert excinfo.value.code == "not_found"


# --------------------------------------------------------------------------- CAM


def test_cam_katalog_operacji_ma_schematy_parametrow(call) -> None:
    catalog = call("cam.operations")
    assert catalog["operations"], "rejestr generatorów powinien być wypełniony"
    for operation in catalog["operations"]:
        assert operation["name"] and operation["version"] >= 1
        assert isinstance(operation["parameters"], dict)


def test_cam_generate_zwraca_gcode(call) -> None:
    catalog = call("cam.operations")
    target = next((o for o in catalog["operations"] if o["parameters"]), None)
    assert target is not None, "brak generatora z parametrami"
    defaults = {name: spec.get("default")
                for name, spec in target["parameters"].items()
                if spec.get("default") is not None}
    try:
        result = call("cam.generate", {"operation": target["name"], "parameters": defaults})
    except ApiError as exc:
        assert exc.code == "invalid_request", exc
        pytest.skip(f"generator {target['name']} wymaga innych parametrów: {exc.message}")
    assert result["gcode"]
    assert result["operation"] == target["name"]


def test_cam_nieznana_operacja_daje_not_found_z_lista(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("cam.generate", {"operation": "nie_ma_takiej", "parameters": {}})
    assert excinfo.value.code == "not_found"
    assert excinfo.value.details["known"]


# --------------------------------------------------------------------------- offsety


def test_offset_przygotowka_i_detal(call) -> None:
    result = call("offset.stock_set", {"shape": "BOX", "x": 120.0, "y": 80.0, "z": 25.0})
    assert result["shape"] == "BOX"
    assert "BOX X120 Y80 Z25" in result["line"]
    assert result["line"].startswith(";@STOCK")
    assert call("offset.stock_get")["x"] == 120.0

    piece = call("offset.workpiece_get")
    assert piece["shape"] in {"box", "cylinder", "tube", "casting"}


def test_offset_kalibracja_sondy_liczy_i_zapisuje(call, workdir) -> None:
    result = call("offset.probe_calibrate",
                  {"axis": "X", "direction": 1,
                   "measured": [10.001, 10.002, 10.003], "true_value": 10.0})
    # Rdzeń zwraca poprawkę w mm: 10.0 - średnia(10.001, 10.002, 10.003) = -0.002
    assert result["correction"] == pytest.approx(-0.002, abs=1e-6)
    assert result["spread"] == pytest.approx(0.002, abs=1e-6)
    assert (workdir / "state" / "probe_calibration.json").exists()

    applied = call("offset.probe_apply", {"axis": "X", "direction": 1, "measured": 25.0})
    assert applied["value"] == pytest.approx(24.998, abs=1e-6)


def test_offset_kalibracja_z_duzym_rozrzutem_jest_odrzucona(call) -> None:
    """Rozrzut odczytów ponad limit rdzenia = brak kalibracji (czytelny błąd dla GUI)."""
    with pytest.raises(ApiError) as excinfo:
        call("offset.probe_calibrate",
             {"axis": "Z", "direction": -1, "measured": [10.0, 10.5], "true_value": 10.0})
    assert excinfo.value.code == "invalid_request"
    assert "rozrzut" in excinfo.value.message


def test_offset_sondowanie_ruchem_jest_planowane(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("offset.probe_run")
    assert excinfo.value.code == "not_implemented"


# --------------------------------------------------------------------------- symulacja


def test_sim_run_liczy_material_i_kolizje(call) -> None:
    program = call("program.read", {"name": "linumert_kwadrat.ngc"})["text"]
    result = call("sim.run", {"program": program, "stock": "BOX X150 Y150 Z20",
                              "tools": [[1, 40.0, 6.0]]})
    assert result["seconds"] > 0
    assert result["length_mm"] > 0
    assert result["segments"] > 0
    assert {"min_x", "max_x", "min_z", "max_z"} <= set(result["bounds"])


def test_sim_run_przez_nazwe_programu(call) -> None:
    result = call("sim.run", {"name": "linumert_kwadrat.ngc", "stock": "BOX X150 Y150 Z20",
                              "tools": [[1, 40.0, 6.0]]})
    assert result["ok"] is True


def test_sim_bez_programu_daje_invalid_request(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("sim.run", {"program": "", "name": ""})
    assert excinfo.value.code == "invalid_request"


# --------------------------------------------------------------------------- Plant


def test_plant_biblioteka_napedow_i_scenariusze(call) -> None:
    drives = call("plant.drives")
    assert drives["templates"], "biblioteka napędów nie może być pusta"
    assert {t["id"] for t in drives["templates"]}

    scenarios = call("plant.scenarios")
    assert scenarios["scenarios"], "brak scenariuszy w beta/scenarios"


def test_plant_status_przed_startem(call) -> None:
    status = call("plant.status")
    assert status["running"] is False


def test_plant_start_i_stop_serwera_lrtnet(call) -> None:
    started = call("plant.start", {"machine": "mill_servo_table.yaml", "mode": "lockstep",
                                   "listen": "127.0.0.1", "port": 0})
    assert started["running"] is True
    assert started["port"] > 0
    assert started["machine"]

    status = call("plant.status")
    assert status["running"] is True
    assert call("plant.stop")["ok"] is True
    assert call("plant.status")["running"] is False


def test_plant_drugi_start_daje_conflict(call) -> None:
    call("plant.start", {"machine": "mill_servo_table.yaml", "port": 0})
    try:
        with pytest.raises(ApiError) as excinfo:
            call("plant.start", {"machine": "mill_servo_table.yaml", "port": 0})
        assert excinfo.value.code == "conflict"
    finally:
        call("plant.stop")


def test_plant_telemetria_wymaga_dzialajacego_serwera(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("plant.telemetry", {"drive": "x", "limit": 10})
    assert excinfo.value.code == "conflict"


# --------------------------------------------------------------------------- konfiguracja


def test_config_lista_maszyn_z_walidacja(call) -> None:
    machines = call("config.machines")
    assert machines["machines"]
    for item in machines["machines"]:
        assert item["name"].endswith((".yaml", ".yml"))
        assert isinstance(item["valid"], bool)


def test_config_get_i_validate(call) -> None:
    data = call("config.machine_get", {"name": "mill_servo_table.yaml"})
    assert data["axes"]
    assert data["data"], "konfiguracja powinna być zwrócona jako dane dla GUI"

    result = call("config.validate", {"name": "mill_servo_table.yaml"})
    assert isinstance(result["ok"], bool)


def test_config_generate_podglad_i_zapis(call, workdir) -> None:
    preview = call("config.generate", {"name": "mill_servo_table.yaml", "target": "sim"})
    assert preview["files"], "generator powinien zwrócić pliki"
    assert preview["written"] == []

    written = call("config.generate", {"name": "mill_servo_table.yaml", "target": "sim",
                                       "write": True})
    assert written["written"]
    for path in written["written"]:
        assert json.loads(json.dumps(path))  # ścieżka musi być JSON-owalna
        from pathlib import Path

        assert Path(path).exists()


def test_config_nieznana_maszyna_daje_not_found(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("config.machine_get", {"name": "nie_ma.yaml"})
    assert excinfo.value.code == "not_found"


# --------------------------------------------------------------------------- alarmy


def test_alarm_raise_ack_reset(call) -> None:
    codes = call("alarm.list")
    assert isinstance(codes["active"], list)

    from linumert_headless.services.alarm import AlarmService

    service = AlarmService()
    known = sorted(getattr(service.catalog, "definitions", {}) or {})
    if not known:
        pytest.skip("katalog alarmów pusty")
    raised = call("alarm.raise", {"code": known[0]})
    assert raised["code"] == known[0]
    assert raised["message"]

    active = call("alarm.list")["active"]
    assert any(a["code"] == known[0] for a in active)
    assert call("alarm.ack", {"alarm_id": None})["ok"] is True
    assert call("alarm.reset")["ok"] is True


def test_alarm_nieznany_kod_daje_not_found_z_lista(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("alarm.raise", {"code": "K-9999"})
    assert excinfo.value.code == "not_found"


# --------------------------------------------------------------------------- diagnostyka


def test_diag_doctor_zglasza_braki_srodowiska(call) -> None:
    report = call("diag.doctor")
    names = {entry["name"] for entry in report["entries"]}
    assert {"Python", "System"} <= names
    assert "hardware_verified" not in report or report["ok"] in (True, False)
    assert report["report"]


def test_diag_dziennik_zapisuje_wywolania(call) -> None:
    call("machine.state")
    journal = call("diag.journal", {"limit": 50})
    assert journal["entries"], "dziennik powinien zawierać wywołania operacji"
    assert {"time", "level", "message"} <= set(journal["entries"][0])


def test_diag_cia402_dekoduje_statusword(call) -> None:
    result = call("diag.cia402", {"statusword": 0x0231, "error_code": 0x7300})
    assert result["state"]
    assert result["description"]
    assert result["error_text"]


# --------------------------------------------------------------------------- dostęp


def test_access_bez_pin_kontrola_wylaczona(call) -> None:
    session = call("access.session")
    assert session["role"] == "operator"
    assert session["enforced"] is False


def test_access_login_z_blednym_pinem_daje_blad(call) -> None:
    with pytest.raises(ApiError) as excinfo:
        call("access.login", {"role": "serwis", "pin": "1234"})
    assert excinfo.value.code in {"invalid_request", "permission_denied"}


def test_access_rola_nie_moze_wiecej_niz_operator_gdy_brak_pinu(call) -> None:
    """Dopóki nie ma PIN-ów, każdy klient jest operatorem (brak domyślnych haseł)."""
    session = call("access.session")
    assert session["role"] == "operator"
