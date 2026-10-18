"""Panel Plant z rdzeniem C: API HTTP, WebSocket, parametry live, pulpit przez LRT-NET (sesja 022).

Model-Author: Claude

Wymaga rdzenia C (kompilator, Linux/WSL) oraz grupy zależności `panel` (fastapi, uvicorn,
websockets) i httpx — inaczej testy są pomijane. Serwer HTTP w testach: port 0 (system wybiera
wolny), żadnych stałych portów (prompts/START-PODZIAL.md §2).
NIEZWERYFIKOWANE z LinuxCNC (pulpit w HAL: sesja 029) i na sprzęcie.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from linumert_plant.panel.desk import QUADRATURE, DeskConfig
from linumert_plant.server import PlantConfig, PlantConfigError, PlantServer
from test_master import Master

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")
httpx = pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"
DESK = {"mpg_a": 20, "mpg_b": 21, "axis": {"X": 22, "Y": 23, "Z": 24},
        "step": {1: 25, 10: 26, 100: 27}, "cycle_start": 28, "feed_hold": 29, "key": 30}


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


def _server(core, **cfg) -> PlantServer:
    from linumert_plant.build_machine import build_model
    from linumert_plant.machine_drives import load_machine_drives

    mcfg, drives = load_machine_drives(MACHINE)
    machine = core.PlantMachine(build_model(mcfg, drives, seed=1))
    return PlantServer(machine, PlantConfig(**cfg),
                       drive_params={name: inst.params for name, inst in drives.items()})


def _client(server: PlantServer, tmp_path: Path):
    from fastapi.testclient import TestClient
    from linumert_plant.panel.app import create_app

    return TestClient(create_app(server, tmp_path))


def _max_accel(server: PlantServer, drive: str) -> float:
    cols = server.telemetry.columns()
    t, v = cols["t"], cols["drives"][drive]["vel"]
    return max(abs((v[i] - v[i - 4]) / (t[i] - t[i - 4])) for i in range(4, len(t)))


def _move_x(server: PlantServer) -> Master:
    master = Master(len(server.drives), transport=server.handle)
    master.enable()
    master.move(0, 20_000, 400_000.0, 2e7)  # zadane przyspieszenie ponad możliwości napędu
    for _ in range(300):
        master.exchange()
    return master


# ---- REQ-VD-04: zmiana masy w panelu zmienia przyspieszenie ------------------------------

def test_mass_change_in_panel_changes_acceleration(core, tmp_path) -> None:
    # REQ-VD-04: parametr live z panelu trafia do rdzenia C w trakcie pracy, z dziennikiem
    light = _server(core)
    _move_x(light)
    heavy = _server(core)
    client = _client(heavy, tmp_path)
    drive = heavy.drives[0]
    base = heavy.live_base[drive]["mechanics"]["load"]
    res = client.post("/api/live", json={"drive": drive, "path": "mechanics.load",
                                         "value": base * 10})
    assert res.status_code == 200, res.text
    assert res.json()["old"] == base and res.json()["new"] == base * 10
    _move_x(heavy)
    a_light, a_heavy = _max_accel(light, drive), _max_accel(heavy, drive)
    assert a_heavy < 0.75 * a_light, (a_light, a_heavy)
    log = client.get("/api/live/log").json()
    assert [(r["drive"], r["path"], r["new"]) for r in log] == [(drive, "mechanics.load",
                                                                 base * 10)]


def test_live_change_mid_run_is_logged_with_model_time(core, tmp_path) -> None:
    # REQ-VD-04: zmiana w trakcie ruchu; czas zmiany = czas modelu
    server = _server(core)
    client = _client(server, tmp_path)
    master = Master(len(server.drives), transport=server.handle)
    master.enable()
    for _ in range(100):
        master.exchange()
    t_model = server.machine.time
    drive = server.drives[1]
    rec = client.post("/api/live", json={"drive": drive, "path": "limits.torque_limit_permille",
                                         "value": 800}).json()
    assert rec["t"] == pytest.approx(t_model) and rec["new"] == 800
    assert server.machine.od_read(drive, 0x6072) == 800  # 6072h w napędzie
    assert server.live_values()[drive]["limits.torque_limit_permille"] == 800


def test_live_rejections_leave_model_unchanged(core, tmp_path) -> None:
    # REQ-VD-04: odrzucona zmiana nie zmienia modelu ani dziennika (HTTP 400, komunikat)
    server = _server(core)
    client = _client(server, tmp_path)
    drive = server.drives[0]
    before = server.live_values()
    for body, fragment in (
            ({"drive": drive, "path": "mechanics.load", "value": -5}, "poza zakresem"),
            ({"drive": drive, "path": "motor.rated_torque", "value": 2}, "live"),
            ({"drive": "brak", "path": "mechanics.load", "value": 1}, "bez parametrów live"),
            ({"drive": drive, "path": "electrical.supply_voltage", "value": 1e4}, "poza")):
        res = client.post("/api/live", json=body)
        assert res.status_code == 400 and fragment in res.json()["detail"], res.text
    assert server.live_values() == before and server.live_log() == []


def test_presets_save_and_load(core, tmp_path) -> None:
    server = _server(core)
    client = _client(server, tmp_path)
    drive = server.drives[0]
    base = server.live_base[drive]["mechanics"]["load"]
    res = client.post("/api/presets/ciezki_stol/load")
    assert res.status_code == 200, res.text
    assert server.live_values()[drive]["mechanics.load"] == 2 * base
    client.post("/api/live", json={"drive": drive, "path": "mechanics.load", "value": 12.0})
    assert client.post("/api/presets/moj/save").json()["file"] == "moj.json"
    assert (tmp_path / "presets" / "moj.json").is_file()
    client.post("/api/presets/startowy/load")
    assert server.live_values()[drive]["mechanics.load"] == base
    client.post("/api/presets/moj/load")
    assert server.live_values()[drive]["mechanics.load"] == 12.0
    names = [p["name"] for p in client.get("/api/presets").json()]
    assert "moj" in names and "zuzyty_silnik" in names
    assert client.post("/api/presets/nie_ma/load").status_code == 400


# ---- API przez prawdziwy serwer HTTP (port 0) ---------------------------------------------

def test_panel_http_api_on_localhost(core, tmp_path) -> None:
    from linumert_plant.panel.app import PanelThread

    server = _server(core, desk=DeskConfig.from_dict(DESK))
    panel = PanelThread(server, "127.0.0.1", 0, tmp_path).start()
    try:
        assert panel.port > 0
        with httpx.Client(base_url=f"http://127.0.0.1:{panel.port}", timeout=5.0) as http:
            page = http.get("/")
            assert page.status_code == 200 and "linumeRT" in page.text
            assert http.get("/static/vendor/uPlot.iife.min.js").status_code == 200
            assert http.get("/static/app.js").status_code == 200
            master = Master(len(server.drives), transport=server.handle)
            master.enable()
            master.move(0, 5_000, 200_000.0, 2e6)
            state = http.get("/api/state").json()
            assert state["machine"] == server.machine.model.name
            assert [d["name"] for d in state["drives"]] == server.drives
            assert state["push_hz"] <= 20 and state["window_s"] == 10
            assert state["stats"]["frames"] == master.seq - 1
            load = next(p for p in state["drives"][0]["live"] if p["path"] == "mechanics.load")
            assert load["min"] <= load["value"] <= load["max"] and load["unit"] == "kg"
            tele = http.get("/api/telemetry").json()
            assert tele["next"] == server.telemetry.count > 0
            x = tele["drives"][server.drives[0]]
            assert max(x["cmd"]) > 0 and len(x["ferr"]) == len(tele["t"])
            assert http.get(f"/api/telemetry?since={tele['next']}").json()["t"] == []
            res = http.post("/api/live", json={"drive": server.drives[0],
                                               "path": "mechanics.load", "value": 50.0})
            assert res.status_code == 200, res.text
            assert http.post("/api/desk/axis", json={"axis": "Y"}).json()["axis"] == "Y"
            assert http.post("/api/desk/axis", json={"axis": "Q"}).status_code == 400
    finally:
        panel.close()
    assert not panel.thread.is_alive()


def test_websocket_pushes_telemetry(core, tmp_path) -> None:
    server = _server(core)
    client = _client(server, tmp_path)
    master = Master(len(server.drives), transport=server.handle)
    master.enable()
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        n0 = first["telemetry"]["next"]
        assert n0 == server.telemetry.count and first["stats"]["frames"] == master.seq - 1
        for _ in range(50):
            master.exchange()
        second = ws.receive_json()
        assert second["telemetry"]["first"] == n0  # tylko nowe próbki
        assert len(second["telemetry"]["t"]) == second["telemetry"]["next"] - n0 > 0


def test_record_csv_via_api(core, tmp_path) -> None:
    server = _server(core)
    with _client(server, tmp_path) as client:  # lifespan: pętla zapisu działa
        master = Master(len(server.drives), transport=server.handle)
        master.enable()
        assert client.post("/api/record/start", json={"name": "ruch"}).json()["active"]
        master.move(0, 5_000, 200_000.0, 2e6)
        status = client.post("/api/record/stop").json()
        assert not status["active"] and status["rows"] > 10 and status["dropped"] == 0
        assert client.get("/api/records").json()[0]["name"] == "ruch.csv"
        text = client.get("/api/records/ruch.csv").text
        rows = list(csv.reader(io.StringIO(text)))
        assert rows[0][0] == "t" and f"{server.drives[0]}.ferr" in rows[0]
        assert len(rows) - 1 == status["rows"]
        assert client.get("/api/records/..%2Fsecret.csv").status_code == 404


# ---- pulpit przez atrapę mastera (bity digital_in LRT-NET) ---------------------------------

def test_desk_inputs_reach_master(core, tmp_path) -> None:
    server = _server(core, desk=DeskConfig.from_dict(DESK))
    client = _client(server, tmp_path)
    master = Master(len(server.drives), transport=server.handle)
    master.enable()

    def bits(*nums: int) -> tuple[int, ...]:
        return tuple(master.last.digital_in >> b & 1 for b in nums)

    assert bits(22, 23, 24, 25, 26, 27, 28, 29, 30) == (1, 0, 0, 1, 0, 0, 0, 0, 0)
    client.post("/api/desk/axis", json={"axis": "Z"})
    client.post("/api/desk/step", json={"step": 10})
    client.post("/api/desk/key", json={"on": True})
    master.exchange()
    assert bits(22, 23, 24, 25, 26, 27, 30) == (0, 0, 1, 0, 1, 0, 1)
    # MPG: 3 pozycje = 12 zboczy kwadratury, po jednym na ramkę; dekoder jak `encoder`
    assert client.post("/api/desk/mpg", json={"detents": 3}).json()["mpg_pending"] == 12
    count, prev = 0, bits(20, 21)
    for _ in range(20):
        master.exchange()
        now = bits(20, 21)
        if now != prev:
            step = (QUADRATURE.index(now) - QUADRATURE.index(prev)) % 4
            count += 1 if step == 1 else -1
            assert step in (1, 3)  # nigdy dwa zbocza naraz
        prev = now
    assert count == 12
    client.post("/api/desk/mpg", json={"detents": -2})
    for _ in range(10):
        master.exchange()
    assert server.desk.edges == 4
    # Start: impuls 100 ms czasu modelu (100 ramek po 1 ms)
    client.post("/api/desk/press", json={"button": "cycle_start"})
    high = 0
    for _ in range(150):
        master.exchange()
        high += bits(28)[0]
    assert 99 <= high <= 101 and bits(28, 29) == (0, 0)
    # Wejścia maszyny (E-STOP, krańcówki) bez zmian
    estop = server.machine.model.inputs["estop"]
    assert bits(estop) == (server.machine.inputs >> estop & 1,)


def test_desk_collision_with_machine_input_refuses_start(core) -> None:
    estop = 0
    with pytest.raises(PlantConfigError, match="wejście maszyny estop"):
        _server(core, desk=DeskConfig.from_dict({"key": estop}))


def test_serve_cli_panel_port_zero(core, tmp_path) -> None:
    """`serve --panel 0`: panel i LRT-NET w jednym procesie; `panel` bez fastapi = kod 1."""
    import subprocess
    import sys
    import time

    proc = subprocess.Popen([sys.executable, "-m", "linumert_plant", "serve", str(MACHINE),
                             "--port", "47812", "--panel", "0", "--state-dir", str(tmp_path)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            cwd=ROOT, env=_env())
    try:
        url = None
        deadline = time.monotonic() + 60
        while url is None and time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            if "panel http://" in line:
                url = line.split("panel ", 1)[1].strip()
        assert url, proc.stderr.read()
        assert httpx.get(url + "api/state", timeout=5).json()["mode"] == "lockstep"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _env() -> dict:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(ROOT / p) for p in ("core", "simulation",
                                                                "plant/server"))
    return env
