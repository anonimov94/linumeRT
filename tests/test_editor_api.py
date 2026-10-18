"""Edytor wirtualnej obrabiarki i napędów w panelu Plant (sesja 023, REQ-VM-12, REQ-VD-03).

Model-Author: Claude

Wymaga rdzenia C i grupy zależności `panel` (fastapi, httpx); inaczej pomijany. Maszyna
i biblioteka napędów są kopiowane do katalogu tymczasowego — repozytorium się nie zmienia.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from linumert_plant.server import PlantConfig, PlantServer
from test_master import Master

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config" / "machines" / "mill_servo_table.yaml"
ATC = ROOT / "config" / "machines" / "router_atc_rack.yaml"
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
    """(serwer, klient, ścieżka machine.yaml, katalog biblioteki) na kopiach plików."""
    from fastapi.testclient import TestClient
    from linumert_plant.build_machine import build_model
    from linumert_plant.machine_drives import load_machine_drives
    from linumert_plant.panel.app import create_app

    def make(source: Path = MILL):
        machine = tmp_path / source.name
        shutil.copy(source, machine)
        lib = tmp_path / "drives"
        if not lib.exists():
            shutil.copytree(LIBRARY, lib)
        mcfg, drives = load_machine_drives(machine, lib)
        server = PlantServer(core.PlantMachine(build_model(mcfg, drives, seed=1)),
                             PlantConfig(machine=machine),
                             drive_params={n: i.params for n, i in drives.items()})
        app = create_app(server, tmp_path / "state")
        app.state.editor.library_dir = lib
        return server, TestClient(app), machine, lib

    return make


def test_machine_tree_and_validation(env) -> None:  # REQ-VM-12, REQ-VM-11
    _server, client, _path, _lib = env()
    res = client.get("/api/machine").json()
    assert res["errors"] == [] and res["data"]["machine"]["name"] == "mill_servo_table"
    titles = [n["title"] for n in res["tree"]]
    assert titles[0] == "Kinematyka" and "Oś X" in titles and "Magazyn" in titles
    assert any(t.startswith("Oś Y (") for t in titles)  # gantry: dwa napędy
    data = res["data"]
    data["axes"][0]["soft_limits"] = [-50, 599]  # poza krańcówką min (0,5)
    errors = client.post("/api/machine/validate", json={"data": data}).json()["errors"]
    assert errors and any("axes" in e and "soft" in e for e in errors), errors
    res = client.post("/api/machine/save", json={"data": data})
    assert res.status_code == 400 and res.json()["detail"]["errors"]


def test_save_writes_history_and_file(env) -> None:  # REQ-VM-12
    _server, client, path, _lib = env()
    data = client.get("/api/machine").json()["data"]
    data["axes"][0]["max_velocity"] = 150
    res = client.post("/api/machine/save", json={"data": data, "comment": "wolniejszy X"})
    assert res.status_code == 200, res.text
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["axes"][0]["max_velocity"] == 150
    hist = client.get("/api/machine/history").json()
    assert [h["number"] for h in hist] == [0, 1] and hist[1]["comment"] == "wolniejszy X"
    original = client.get(f"/api/machine/history/{hist[0]['file']}").json()["text"]
    assert "max_velocity: 200" in original
    assert client.get("/api/machine/history/..%2Fzly.yaml").status_code in (400, 404)


def test_reload_only_with_drives_disabled(env) -> None:  # REQ-VM-12
    server, client, _path, _lib = env()
    master = Master(len(server.drives), transport=server.handle)
    master.enable()
    data = client.get("/api/machine").json()["data"]
    data["drives"][0].setdefault("overrides", {})["mechanics"] = {"load": 160.0}
    assert client.post("/api/machine/save", json={"data": data}).status_code == 200
    res = client.post("/api/machine/reload")
    assert res.status_code == 400 and "wyłączonych" in res.json()["detail"]["errors"][0]
    for axis in master.axes:
        axis.controlword = 0x0006  # shutdown: napędy bez momentu
    for _ in range(5):
        master.exchange()
    res = client.post("/api/machine/reload")
    assert res.status_code == 200, res.text
    assert server.live_values()["drv_x"]["mechanics.load"] == 160.0  # nowy model działa
    master.enable()  # LRT-NET dalej działa po przeładowaniu, bez restartu
    assert all(s == "OPERATION_ENABLED" for s in master.states())


def test_scene_from_model(env) -> None:  # REQ-VM-12
    _server, client, _path, _lib = env(ATC)
    scene = client.get("/api/machine/scene").json()
    kinds = {b["kind"] for b in scene["boxes"]}
    assert {"travel", "soft"} <= kinds
    pockets = [c for c in scene["cylinders"] if c["kind"] == "pocket"]
    assert len(pockets) == 6 and all(  # router_atc_rack: 6 gniazd
        c["edit"] == "toolchanger.base_position" for c in pockets)
    assert any(p["kind"] == "limit" and p["axis"] == "X" for p in scene["points"])
    assert len(scene["tool"]) == 3


def test_drive_templates_clone_and_diff(env) -> None:  # REQ-VD-03
    _server, client, _path, lib = env()
    names = [t["id"] for t in client.get("/api/drives/templates").json()]
    assert "servo_400w" in names
    inst = client.get("/api/drives/instances").json()
    assert [i["axis"] for i in inst if i["id"] == "drv_x"] == ["X"]
    res = client.post("/api/drives/clone", json={"source": "drv_z", "new_id": "servo_z_ciezki"})
    assert res.status_code == 200, res.text
    assert (lib / "servo_z_ciezki.yaml").is_file()
    detail = client.get("/api/drives/templates/servo_z_ciezki").json()
    assert detail["template"]["based_on"] == res.json()["based_on"]
    assert any(d["path"] == "mechanics.load" for d in detail["diff"])  # nadpisanie z maszyny
    again = client.post("/api/drives/clone", json={"source": "servo_400w",
                                                   "new_id": "servo_z_ciezki"})
    assert again.status_code == 400 and "istnieje" in again.text


def test_faults_tab_api(env) -> None:
    server, client, _path, _lib = env()
    cat = client.get("/api/faults").json()
    assert len(cat["catalog"]) == 8 and cat["drives"]["drv_x"]
    assert client.post("/api/faults/estop", json={}).status_code == 200
    assert [f["kind"] for f in client.get("/api/faults").json()["active"]] == ["estop"]
    assert client.post("/api/faults/estop/clear", json={}).status_code == 200
    assert client.post("/api/faults/nie_ma", json={}).status_code == 400
