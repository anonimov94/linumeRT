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
    """Granice muszą być wykryte naprawdę — bez LinuxCNC.

    Regresja: usługa karmiła surowy G-code do ``limits.analyze_canon``, który oczekuje
    tekstu canon (wyjścia rs274), więc nie znajdował nic i meldował "program w granicach".
    Do tego ``Violation.limit`` to pojedynczy float, a ``message`` to metoda — czytanie
    ``v.limit[0]`` i ``getattr(v, "message")`` dawało TypeError i obiekt metody.
    Poprzednia wersja testu iterowała po naruszeniach, których nigdy nie było, więc
    asercja o polach nigdy się nie wykonała.
    """
    out = call("program.check", {"text": "G0 X0 Y0 Z0\nG1 X900 Y0 F200\nG1 X-300 Y20 F200\n"})
    assert out["ok"] is False, "program poza granicami musi być zgłoszony"
    assert out["moves"] > 0 and out["lines"] > 0
    assert out["interpreter"] in {"rs274", "subset"}
    sides = {v["side"] for v in out["violations"]}
    assert sides == {"min", "max"}, sides
    for violation in out["violations"]:
        assert {"axis", "line", "value", "limit", "side", "count", "message"} <= set(violation)
        assert isinstance(violation["limit"], (int, float))
        assert violation["message"] and "przekracza" in violation["message"]
        assert violation["count"] >= 1

    ok = call("program.check", {"text": "G0 X0 Y0 Z0\nG1 X50 Y50 F200\n"})
    assert ok["ok"] is True and ok["violations"] == []


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


def _cam_params(operation: dict) -> dict:
    """Poprawne parametry generatora — domyślne plus sensowne wartości pól wymaganych."""
    params = {}
    for name, spec in operation["parameters"].items():
        default = spec.get("default")
        if default not in (None, ""):
            params[name] = default
        elif name == "paths":            # JSON: lista ścieżek, każda >= 2 punkty XY
            params[name] = json.dumps([[[0, 0], [10, 0], [10, 10], [0, 10]]])
        elif name == "segments":         # opis pola: "L x,y x,y; A x,y x,y cx,cy CW|CCW"
            params[name] = "L 0,0 20,0; L 20,0 20,20; L 20,20 0,20; L 0,20 0,0"
        elif name == "text":
            params[name] = "lrt"
        elif name in ("depth", "diameter"):
            params[name] = 6.0
        elif name == "tool_d":
            params[name] = 4.0
        elif spec.get("type") in ("float", "int"):
            params[name] = 5.0
        elif spec.get("type") == "choice":
            params[name] = spec["choices"][0]
        elif spec.get("type") == "bool":
            params[name] = False
        else:
            params[name] = ""
    return params


def test_cam_katalog_ma_pola_formularza_nie_sygnature(call) -> None:
    """Schemat parametrów musi opisywać pola generatora, nie ``args``/``kwargs``.

    Regresja: rejestr zwraca instancje, więc czytanie sygnatury ``__init__`` dawało
    GUI bezużyteczny formularz z polami ``args`` i ``kwargs``.
    """
    for operation in call("cam.operations")["operations"]:
        assert set(operation["parameters"]) != {"args", "kwargs"}, operation["name"]
        for name, spec in operation["parameters"].items():
            assert spec["label"], f"{operation['name']}.{name} bez etykiety"
            assert spec["type"] in ("float", "int", "bool", "choice", "text")
            assert "required" in spec and "default" in spec


def test_cam_operacje_maja_opis_dla_menu_gui(call) -> None:
    """Każdy generator musi mieć opis — GUI buduje z tego menu.

    Regresja: usługa czytała pole ``summary``, którego generatory nie mają (mają polski
    ``title``), więc wszystkie 16 pozycji wracało z pustym opisem i menu nie miało etykiet.
    """
    for operation in call("cam.operations")["operations"]:
        assert operation["summary"].strip(), f"{operation['name']} bez opisu"
        assert operation["version"] >= 1


def test_cam_generate_dziala_dla_kazdego_generatora(call) -> None:
    """Wszystkie generatory z katalogu muszą produkować G-code — bez wyjątków i skipów."""
    catalog = call("cam.operations")
    assert len(catalog["operations"]) >= 16
    for operation in catalog["operations"]:
        result = call("cam.generate",
                      {"operation": operation["name"], "parameters": _cam_params(operation)})
        assert result["operation"] == operation["name"]
        assert result["gcode"].strip(), f"{operation['name']} bez G-code"
        assert result["version"] >= 1


def test_cam_zle_parametry_daja_bledy_polowe_z_kodami(call) -> None:
    """GUI podświetla pola: błąd niesie kod z katalogu alarmów i nazwę pola."""
    with pytest.raises(ApiError) as excinfo:
        # depth jest wymagany — bez niego wróciłby błąd brakującego pola (P-5014),
        # a nie konflikt geometrii (P-5007), który tu sprawdzamy.
        call("cam.generate", {"operation": "pocket_circle",
                              "parameters": {"diameter": 6.0, "depth": 3.0, "tool_d": 50.0}})
    assert excinfo.value.code == "invalid_request"
    errors = excinfo.value.details["errors"]
    assert errors and all(e["code"] and e["message"] for e in errors)
    assert any(e["field"] == "tool_d" for e in errors)


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


def test_plant_machine_drives_rozwiazuje_szablony(call) -> None:
    """Napędy maszyny: szablon z biblioteki plus nadpisania z machine.yaml.

    Regresja: ``load_machine_drives`` zwraca krotkę ``(MachineConfig, dict)``, a usługa
    wołała ``.items()`` na krotce — każda taka operacja kończyła się AttributeError.
    Metoda nie była też zarejestrowana w kontrakcie, więc GUI nie miało do niej drogi.
    """
    result = call("plant.machine_drives", {"name": "router_xyza"})
    assert result["machine"] == "router_xyza"
    assert result["axes"] == ["X", "Y", "Z", "A"]
    assert result["drives"], "maszyna bez napędów"
    for name, params in result["drives"].items():
        assert name and isinstance(params, dict)
        assert params, f"napęd {name} bez parametrów"
        assert "id" in params


def test_plant_faults_ma_katalog_i_pozwala_wstrzyknac(call) -> None:
    """Panel testowy GUI: katalog awarii i wstrzyknięcie z parametrami rodzaju.

    Regresja: ``plant.fault_set`` miał w schemacie tylko pole ``drive``, które usługa
    przekazywała jako ``target`` — a ``Faults.inject`` dla ``drive_fault`` czyta
    ``drive``. Żaden rodzaj z parametrami nie dawał się wstrzyknąć.
    """
    call("plant.start", {"machine": "mill_servo_table.yaml", "port": 0})
    try:
        catalog = call("plant.faults")
        kinds = {item["kind"] for item in catalog["catalog"]}
        assert {"estop", "drive_fault", "frame_loss", "delay"} <= kinds
        for item in catalog["catalog"]:
            assert item["desc"] and isinstance(item["params"], list)

        # rodzaj z parametrami — wcześniej nie do wstrzyknięcia
        drive = next(iter(call("plant.machine_drives", {"name": "mill_servo_table"})["drives"]))
        call("plant.fault_set", {"kind": "drive_fault",
                                 "params": {"drive": drive, "code": "FOLLOWING_ERROR"}})
        active = call("plant.faults")["active"]
        assert len(active) == 1 and active[0]["kind"] == "drive_fault"
        call("plant.fault_set", {"kind": "drive_fault", "enabled": False,
                                 "params": {"drive": drive, "code": "FOLLOWING_ERROR"}})
        assert call("plant.faults")["active"] == []

        # zły kod awarii: błąd musi wyliczyć znane kody, nie tylko odrzucić
        with pytest.raises(ApiError) as excinfo:
            call("plant.fault_set", {"kind": "drive_fault",
                                     "params": {"drive": drive, "code": "NIE-MA-TAKIEGO"}})
        assert excinfo.value.code == "invalid_request"
        assert excinfo.value.details.get("catalog")
    finally:
        call("plant.stop")


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


def test_alarm_codes_daje_gui_katalog_z_tlumaczeniami(call) -> None:
    """GUI nie trzyma własnych tłumaczeń — bierze komunikaty z katalogu.

    Regresja: usługa czytała nieistniejący atrybut ``definitions`` katalogu i oddawała
    pustą listę, więc GUI nie miało jak opisać żadnego alarmu.
    """
    codes = call("alarm.codes")["codes"]
    assert len(codes) >= 50
    for item in codes:
        assert item["code"] and item["level"]
        assert item["message_pl"], f"{item['code']} bez komunikatu PL"
        assert item["message_en"], f"{item['code']} bez komunikatu EN"
        assert item["clear"] in ("ack", "auto", "reset"), item
        assert isinstance(item["params"], list)
    # kod z parametrami musi je zadeklarować — GUI podstawi wartości
    with_params = [c for c in codes if c["params"]]
    assert with_params, "katalog bez kodów parametryzowanych"


def test_alarm_raise_ack_reset(call) -> None:
    codes = call("alarm.list")
    assert isinstance(codes["active"], list)

    # Katalog jest ładowany z catalog.yaml i ma kilkadziesiąt kodów — jeśli jest pusty,
    # to jest błąd, a nie powód do pominięcia testu.
    catalog = call("alarm.codes")["codes"]
    assert len(catalog) >= 50, f"katalog alarmów podejrzanie mały: {len(catalog)}"
    # clear=auto: potwierdzenie tylko oznacza alarm, więc zostaje na liście aktywnej
    # (przy clear=ack potwierdzenie od razu go kasuje). Bez parametrów, żeby komunikat
    # dał się sformatować bez dodatkowych danych.
    target = next(c for c in catalog if not c["params"] and c["clear"] == "auto")
    raised = call("alarm.raise", {"code": target["code"]})
    assert raised["code"] == target["code"]
    assert raised["message"]
    assert "{" not in raised["message"], "niesformatowany parametr w komunikacie"
    assert raised["level"] == target["level"], "poziom musi pochodzić z katalogu"
    assert raised["state"] == "active" and raised["acknowledged"] is False

    # Ponowne zgłoszenie tego samego alarmu zwiększa licznik, nie dokłada wpisu.
    call("alarm.raise", {"code": target["code"]})
    active = call("alarm.list")["active"]
    ours = [a for a in active if a["code"] == target["code"]]
    assert len(ours) == 1, "powtórzenie nie może tworzyć drugiego alarmu"
    assert ours[0]["count"] == 2
    assert call("alarm.list")["worst_level"] == target["level"]

    assert call("alarm.ack", {"alarm_id": None})["ok"] is True
    after = [a for a in call("alarm.list")["active"] if a["code"] == target["code"]][0]
    assert after["acknowledged"] is True and after["state"] == "acknowledged"

    # Reset NIE kasuje wszystkiego: alarmy z clear=auto czekają na swoje zdarzenie
    # (semantyka udokumentowana w linumert.alarms.manager).
    assert call("alarm.reset")["ok"] is True
    assert any(a["code"] == target["code"] for a in call("alarm.list")["active"]), \
        "reset nie może skasować alarmu z clear=auto"

    # Alarm z clear=reset znika po resecie i trafia do historii.
    resettable = next(c for c in catalog if not c["params"] and c["clear"] == "reset")
    call("alarm.raise", {"code": resettable["code"]})
    assert any(a["code"] == resettable["code"] for a in call("alarm.list")["active"])
    assert call("alarm.reset")["ok"] is True
    assert not any(a["code"] == resettable["code"] for a in call("alarm.list")["active"]), \
        "reset musi skasować alarm z clear=reset"
    history = call("alarm.list")["history"]
    assert history, "skasowany alarm musi trafić do historii"
    assert history[0]["state"] == "cleared"


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
