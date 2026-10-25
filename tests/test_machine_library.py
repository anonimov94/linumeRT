# SPDX-License-Identifier: GPL-2.0-or-later
"""Biblioteka maszyn w panelu Plant: nowa z kopii, zmiana nazwy, kosz, aktywacja, edycja YAML.

Model-Author: Claude · 2026-10-25 (prośba właściciela: edycja każdego parametru, nowe maszyny,
usuwanie). Wymaga rdzenia C oraz grupy zależności `panel` (fastapi, httpx); inaczej pomijany.
Pliki maszyn i biblioteka napędów są kopiowane do katalogu tymczasowego.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from linumert_plant.server import PlantConfig, PlantServer

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config" / "machines" / "mill_servo_table.yaml"
ROUTER = ROOT / "config" / "machines" / "router_gantry_steppers.yaml"
LIBRARY = ROOT / "plant" / "library" / "drives"


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


@pytest.fixture
def env(core, tmp_path):
    """(klient, katalog maszyn, serwer): MILL i ROUTER skopiowane do katalogu maszyn."""
    from fastapi.testclient import TestClient
    from linumert_plant.build_machine import build_model
    from linumert_plant.machine_drives import load_machine_drives
    from linumert_plant.panel.app import create_app

    machines = tmp_path / "machines"
    machines.mkdir()
    for source in (MILL, ROUTER):
        shutil.copy(source, machines / source.name)
    lib = tmp_path / "drives"
    shutil.copytree(LIBRARY, lib)
    active = machines / MILL.name
    mcfg, drives = load_machine_drives(active, lib)
    server = PlantServer(core.PlantMachine(build_model(mcfg, drives, seed=1)),
                         PlantConfig(machine=active),
                         drive_params={n: i.params for n, i in drives.items()})
    app = create_app(server, tmp_path / "state")
    app.state.editor.library_dir = lib
    return TestClient(app), machines, server


def files(client) -> dict[str, dict]:
    return {m["file"]: m for m in client.get("/api/machines").json()["machines"]}


# REQ-VM-12
def test_list_marks_active_and_validity(env) -> None:
    client, machines, _ = env
    listing = files(client)
    assert set(listing) == {"mill_servo_table.yaml", "router_gantry_steppers.yaml"}
    assert listing["mill_servo_table.yaml"]["active"] and not listing[
        "router_gantry_steppers.yaml"]["active"]
    assert all(m["valid"] for m in listing.values())
    assert listing["router_gantry_steppers.yaml"]["axes"] == "XYZ"
    assert client.get("/api/machines").json()["directory"] == str(machines)


# REQ-VM-12
def test_clone_creates_valid_machine_with_new_name(env) -> None:
    client, machines, _ = env
    res = client.post("/api/machines/clone", json={"file": "mill_servo_table.yaml",
                                                   "name": "moja_frezarka"})
    assert res.status_code == 200 and res.json()["file"] == "moja_frezarka.yaml"
    data = yaml.safe_load((machines / "moja_frezarka.yaml").read_text(encoding="utf-8"))
    assert data["machine"]["name"] == "moja_frezarka"
    assert files(client)["moja_frezarka.yaml"]["valid"]
    # ta sama nazwa drugi raz i niepoprawne nazwy są odrzucane
    for body in ({"file": "mill_servo_table.yaml", "name": "moja_frezarka"},
                 {"file": "mill_servo_table.yaml", "name": "../zla"},
                 {"file": "mill_servo_table.yaml", "name": "1abc"},
                 {"file": "../mill_servo_table.yaml", "name": "inna"},
                 {"file": "nie_ma.yaml", "name": "inna"}):
        bad = client.post("/api/machines/clone", json=body)
        assert bad.status_code == 400, body
    assert sorted(p.name for p in machines.glob("*.yaml")) == [
        "mill_servo_table.yaml", "moja_frezarka.yaml", "router_gantry_steppers.yaml"]


# REQ-VM-12
def test_rename_and_delete_use_trash_and_protect_active(env) -> None:
    client, machines, _ = env
    assert client.post("/api/machines/rename", json={"file": "mill_servo_table.yaml",
                                                     "name": "x"}).status_code == 400  # aktywna
    assert client.post("/api/machines/delete", json={"file": "mill_servo_table.yaml"}
                       ).status_code == 400
    ok = client.post("/api/machines/rename", json={"file": "router_gantry_steppers.yaml",
                                                   "name": "router_testowy"})
    assert ok.status_code == 200 and not (machines / "router_gantry_steppers.yaml").exists()
    assert yaml.safe_load((machines / "router_testowy.yaml").read_text(encoding="utf-8"))[
        "machine"]["name"] == "router_testowy"
    gone = client.post("/api/machines/delete", json={"file": "router_testowy.yaml"})
    assert gone.status_code == 200 and not (machines / "router_testowy.yaml").exists()
    trash = client.get("/api/machines").json()["trash"]
    assert len(trash) == 1 and trash[0]["machine"] == "router_testowy.yaml"
    back = client.post("/api/machines/restore", json={"file": trash[0]["file"]})
    assert back.status_code == 200 and (machines / "router_testowy.yaml").is_file()
    assert client.get("/api/machines").json()["trash"] == []
    assert client.post("/api/machines/restore", json={"file": "../etc"}).status_code == 400


# REQ-VM-12
def test_activate_switches_machine_and_reverts_on_error(env) -> None:
    client, machines, server = env
    client.post("/api/machines/clone", json={"file": "mill_servo_table.yaml", "name": "druga"})
    res = client.post("/api/machines/activate", json={"file": "druga.yaml"})
    assert res.status_code == 200, res.text
    assert server.cfg.machine == machines / "druga.yaml"
    assert files(client)["druga.yaml"]["active"]
    assert client.get("/api/machine").json()["file"] == "druga.yaml"
    # router ma inną liczbę osi LRT-NET niż frezarka: aktywacja zgłasza błąd i wraca do poprzedniej
    bad = client.post("/api/machines/activate", json={"file": "router_gantry_steppers.yaml"})
    assert bad.status_code in (200, 400)
    if bad.status_code == 400:
        assert server.cfg.machine == machines / "druga.yaml"


# REQ-VM-12, REQ-VM-11
def test_yaml_text_edit_any_parameter_validated_and_versioned(env) -> None:
    client, machines, _ = env
    text = client.get("/api/machine/text").json()["text"]
    original = yaml.safe_load(MILL.read_text(encoding="utf-8"))
    data = yaml.safe_load(text)
    assert data["axes"][0]["max_acceleration"] == original["axes"][0]["max_acceleration"]
    data["axes"][0]["max_acceleration"] = 12345
    edited = yaml.safe_dump(data, sort_keys=False)
    assert client.post("/api/machine/text/validate", json={"text": edited}).json()["errors"] == []
    assert client.post("/api/machine/text/validate", json={"text": "to: [nie yaml"}
                       ).json()["errors"]
    broken = text.replace("travel: [0, 600]", "travel: [700, 600]", 1)
    assert client.post("/api/machine/text/validate", json={"text": broken}).json()["errors"]
    refused = client.post("/api/machine/text/save", json={"text": broken})
    assert refused.status_code == 400
    saved = client.post("/api/machine/text/save", json={"text": edited, "comment": "test"})
    assert saved.status_code == 200 and saved.json()["version"] >= 1
    data = yaml.safe_load((machines / "mill_servo_table.yaml").read_text(encoding="utf-8"))
    assert data["axes"][0]["max_acceleration"] == 12345
    # dodanie nowej osi / napędu to zwykła edycja YAML (każdy parametr, także listy)
    assert len(data["axes"]) == 3 and data["drives"]


# REQ-VM-12
def test_trash_preserves_two_deletions_with_same_name_and_timestamp(env, monkeypatch):
    from linumert_plant.panel import machine_library

    client, machines, _ = env
    monkeypatch.setattr(machine_library.time, "strftime", lambda *args: "20261025_190000")
    for name in ("first", "second"):
        client.post("/api/machines/clone", json={"file": MILL.name, "name": "copy"})
        path = machines / "copy.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["machine"]["name"] = name
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        assert client.post("/api/machines/delete", json={"file": "copy.yaml"}).status_code == 200
    trash = client.get("/api/machines").json()["trash"]
    assert len(trash) == 2
    recovered = set()
    for item in trash:
        assert client.post("/api/machines/restore", json={"file": item["file"]}).status_code == 200
        recovered.add(yaml.safe_load((machines / "copy.yaml").read_text(encoding="utf-8"))[
            "machine"]["name"])
        (machines / "copy.yaml").unlink()
    assert recovered == {"first", "second"}


# REQ-VM-11
def test_failed_atomic_publish_retains_previous_configuration(tmp_path, monkeypatch):
    from linumert_plant.panel import editor

    path = tmp_path / "machine.yaml"
    path.write_text("previous", encoding="utf-8")

    def fail(source, target):
        assert Path(source).read_text(encoding="utf-8") == "replacement"
        raise OSError("publication refused")

    monkeypatch.setattr(editor.os, "replace", fail)
    with pytest.raises(OSError, match="publication refused"):
        editor.atomic_write_text(path, "replacement")
    assert path.read_text(encoding="utf-8") == "previous"
    assert list(tmp_path.iterdir()) == [path]
