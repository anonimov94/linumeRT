# SPDX-License-Identifier: GPL-2.0-or-later
"""Odbiór serwera linumertd (REST + WebSocket) na LinuxCNC RIP + Plant: klient jak GUI.

Model-Author: Claude. Deadman jogu, E-STOP w trakcie jogu, odczyty równoległe, komunikaty
LinuxCNC i obieg narzędzi aż do tabeli LinuxCNC. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

BETA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BETA.parent / "tests"))
import plant_session  # noqa: E402
import rip_support  # noqa: E402

DRIVER = r'''
import subprocess, threading
from pathlib import Path
from websockets.sync.client import connect
from linumert_headless.sdk import Client, RemoteError

PORT, TOKEN = @PORT@, "odbior"
log = open("serwer.log", "w")
server = subprocess.Popen(
    [sys.executable, "-m", "linumert_headless", "serve", "--backend", "linuxcnc",
     "--port", str(PORT), "--token", TOKEN], stdout=log, stderr=subprocess.STDOUT)
api = Client(f"http://127.0.0.1:{PORT}", token=TOKEN)
out = {"on": on, "homed": homed}
def moving():
    return abs(s.current_vel) > 1e-3
def rest(name, **params):
    try:
        return api.call(name, **params)
    except RemoteError as exc:
        return {"refused": exc.code, "message": str(exc), "details": exc.details}
def session():
    ws = connect(f"ws://127.0.0.1:{PORT}/ws?token={TOKEN}", max_size=None)
    json.loads(ws.recv())
    ws.send(json.dumps({"type": "hello", "topics": ["health"]}))
    return ws
def reply(ws, wanted, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        msg = json.loads(ws.recv(timeout=timeout))
        if msg.get("id") == wanted:
            return msg
    raise TimeoutError(wanted)
def jog(ws, wanted, speed=10):
    ws.send(json.dumps({"id": wanted, "command": "machine.jog",
                        "params": {"axis": "X", "speed": speed}}))
def stop_time(limit=15):
    start = time.time()
    return round(time.time() - start, 3) if wait(lambda: not moving(), limit) else None
try:
    for _ in range(100):
        try:
            api.health(); break
        except Exception:
            time.sleep(0.2)
    assert mdi("G53 G0 Z-20")
    assert mdi("G53 G0 X300 Y400")

    # Deadman: pojedyncze polecenie bez odświeżania
    ws = session()
    jog(ws, 1)
    out["once_reply"] = reply(ws, 1)["ok"]
    out["once_started"] = wait(moving, 5)
    out["once_stop_s"] = stop_time()

    # Deadman: odświeżanie co 100 ms trzyma ruch, brak odświeżania zatrzymuje
    x0 = (s.poll(), s.position[0])[1]
    latencies, held = [], []
    for i in range(15):
        sent = time.time()
        jog(ws, 100 + i)
        out["refresh_ok"] = reply(ws, 100 + i)["ok"]
        latencies.append(round(time.time() - sent, 3))
        time.sleep(max(0.0, 0.1 - (time.time() - sent)))
        s.poll()
        if i >= 3:
            held.append(moving())
    out["refresh_held"] = sum(held) / len(held)
    out["refresh_latency_max"] = max(latencies)
    out["refresh_stop_s"] = stop_time()
    out["refresh_moved"] = round(s.position[0] - x0, 3)

    # Zamknięcie połączenia i zerwanie gniazda
    jog(ws, 2)
    reply(ws, 2)
    wait(moving, 5)
    ws.close()
    out["close_stop_s"] = stop_time()
    ws = session()
    jog(ws, 3)
    reply(ws, 3)
    wait(moving, 5)
    ws.socket.close()
    out["drop_stop_s"] = stop_time()

    # E-STOP w trakcie jogu; druga sesja przejmuje stop mimo limitera
    ws = session()
    jog(ws, 4)
    reply(ws, 4)
    wait(moving, 5)
    ws.send(json.dumps({"id": 5, "command": "machine.estop"}))
    out["estop_reply"] = reply(ws, 5)["ok"]
    out["estop"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP, 10)
    out["estop_stop_s"] = stop_time()
    out["reset"] = rest("machine.estop_reset")
    out["reset_state"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 10)
    out["power"] = rest("machine.power_on")
    out["power_state"] = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)
    ws.close()

    # Odczyty równoległe w trakcie poleceń: wspólne obiekty linuxcnc w wątkach serwera
    failures, bad_state = [], []
    def reader():
        for _ in range(60):
            try:
                state = api.call("machine.state")
                if not state["fresh"] or state["backend"] != "linuxcnc":
                    bad_state.append(state["age_s"])
            except Exception as exc:
                failures.append(repr(exc))
    threads = [threading.Thread(target=reader) for _ in range(4)]
    start = time.time()
    for t in threads:
        t.start()
    x0 = (s.poll(), s.position[0])[1]
    for _ in range(5):
        out["inc"] = rest("machine.jog_increment", axis="X", speed=20, distance=1)
        time.sleep(0.2)
    for t in threads:
        t.join()
    out["parallel"] = {"failures": failures[:3], "stale": len(bad_state),
                       "seconds": round(time.time() - start, 2)}
    wait(lambda: not moving(), 10)
    out["parallel_moved"] = round((s.poll(), s.position[0])[1] - x0, 3)

    # Komunikat LinuxCNC: odmowa asynchroniczna dochodzi do klienta odpytującego przez REST
    out["bad_mdi"] = rest("machine.mdi", text="G999")
    time.sleep(1.0)
    out["errors"] = api.call("machine.state")["errors"]

    # Obieg narzędzi: baza -> tabela LinuxCNC -> M6 -> korekta długości
    table = linuxcnc.ini(os.environ["INI_FILE_NAME"]).find("EMCIO", "TOOL_TABLE")
    tool = rest("tool.get", number=5)
    fields = {k: tool[k] for k in ("pocket", "type", "description", "diameter", "params")}
    out["upsert"] = rest("tool.upsert", number=5, offsets={"Z": 33.0}, **fields)
    out["table"] = [line for line in Path(table).read_text().splitlines()
                    if line.startswith("T5 ")]
    assert mdi("G53 G0 Z-5")
    out["change"] = rest("machine.tool_change", tool=5, confirm=True)
    wait(idle, 60); time.sleep(0.5); s.poll()
    out["tool"] = [s.tool_in_spindle, s.tool_offset[2]]
    out["wear"] = rest("tool.set_wear", number=5, axis="Z", value=0.25)
    rest("machine.tool_change", tool=0, confirm=True)
    wait(idle, 60); time.sleep(0.5)
    rest("machine.tool_change", tool=5, confirm=True)
    wait(idle, 60); time.sleep(0.5); s.poll()
    out["tool_wear"] = [s.tool_in_spindle, s.tool_offset[2]]
    out["export"] = rest("tool.export_tbl").get("path") == str(Path(table).resolve())
    out["errors_after_tools"] = api.call("machine.state")["errors"]
    out["doctor_ok"] = rest("diag.doctor").get("ok")
    out["journal"] = len(rest("diag.journal", limit=20).get("entries", []))
    print("RESULT " + json.dumps(out))
finally:
    server.terminate()
    try:
        server.wait(15)
    except subprocess.TimeoutExpired:
        server.kill()
    log.close()
    print(Path("serwer.log").read_text()[-2500:], file=sys.stderr)
'''


@pytest.mark.linuxcnc
@pytest.mark.timeout(420)
def test_server_rest_and_websocket_on_linuxcnc_plant(tmp_path, monkeypatch):
    monkeypatch.setattr(plant_session, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "HAL", BETA / "hal")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(
        filter(None, [str(BETA / "src"), os.environ.get("PYTHONPATH", "")])))
    machine = BETA / "config/machines/mill_servo_table.yaml"
    r, log, _ = plant_session.run_generated_plant(
        tmp_path, machine, DRIVER.replace("@PORT@", "47861"),
        port=47859, timeout=360, copy_macros=False)
    if os.environ.get("LINUMERT_BETA_REPORT"):
        Path(os.environ["LINUMERT_BETA_REPORT"]).write_text(
            json.dumps(r, indent=2), encoding="utf-8")
    assert r["on"] and r["homed"], r
    # Deadman: JOG_HOLD_S 0,4 s + zwłoka pętli stanu + hamowanie.
    assert r["once_started"] and r["once_stop_s"] is not None and r["once_stop_s"] < 1.5, r
    assert r["refresh_held"] == 1.0 and r["refresh_stop_s"] < 1.5, r
    assert r["close_stop_s"] < 1.5 and r["drop_stop_s"] < 1.5, r
    assert r["estop"] and r["estop_stop_s"] < 1.5, r
    assert r["reset_state"] and r["power_state"], r
    assert r["parallel"]["failures"] == [] and r["parallel"]["stale"] == 0, r
    assert r["parallel_moved"] == pytest.approx(5, abs=1e-3), r
    assert "Ignoring task mode change while jogging" not in r["errors"], r
    assert any("G-code" in text for text in r["errors"]), r
    assert r["tool"] == pytest.approx([5, 33.0], abs=1e-6), r
    assert r["tool_wear"] == pytest.approx([5, 33.25], abs=1e-6), r
    assert r["export"] and r["doctor_ok"], r


PIPELINE = r'''
from pathlib import Path
from linumert_headless.app import build_application
from linumert_headless.config import AppConfig
app = build_application(AppConfig(root=Path.cwd(), backend="linuxcnc", autostart=False))
call = app.call_json
out = {"on": on, "homed": homed}
table = linuxcnc.ini(os.environ["INI_FILE_NAME"]).find("EMCIO", "TOOL_TABLE")
call("tool.import_tbl", {"text": Path(table).read_text()})
length = call("tool.get", {"number": 1})["offsets"]["Z"]
# Powierzchnia detalu 80 mm pod bazą Z, narzędzie T1 z korektą długości.
assert mdi(f"G10 L2 P1 X200 Y300 Z{-80 - length}")
def gen(operation, **params):
    return call("cam.generate", {"operation": operation, "parameters": params})
parts = [gen("header", title="odbior"),
         gen("tool_change", tool=1, rpm=6000, safe_z=10),
         gen("pocket_rect", cx=20, cy=15, width=30, height=20, depth=2, step_down=1, tool_d=6,
             feed=1500, plunge=600, safe_z=5),
         gen("program_end", retract="z_home")]
text = "\n".join(p["gcode"] for p in parts) + "\nM2\n"   # generatory zwracają fragmenty
out["program"] = text[:1500]
call("program.write", {"name": "cam.ngc", "text": text, "overwrite": True})
check = call("program.check", {"name": "cam.ngc"})
out["check"] = {k: check[k] for k in ("ok", "violations", "interpreter", "moves")}
estimate = call("program.estimate", {"name": "cam.ngc"})
out["estimate"] = {k: estimate[k] for k in ("ok", "source", "seconds", "feed_mm", "rapid_mm")}
path = call("program.toolpath", {"name": "cam.ngc"})
over = call("program.check", {"text": "G21 G90 G54\nG0 X9000\nM2\n"})
out["over"] = [[v["axis"], v["side"]] for v in over["violations"]]
out["toolpath"] = {k: path[k] for k in ("ok", "source", "bounds", "length_mm", "notes")}
sim = call("sim.run", {"name": "cam.ngc", "stock": "BOX X60 Y50 Z10",
                       "tools": [[1, length, 6.0]]})
out["sim"] = {k: sim[k] for k in ("ok", "source", "seconds", "volume_removed_mm3", "length_mm",
                                  "collisions", "notes")}
call("program.load", {"name": "cam.ngc"})
start = time.time()
call("machine.run", {})
assert wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 20)
low, high, spindle, line = [1e9] * 3, [-1e9] * 3, 0.0, 0
while time.time() - start < 200:
    s.poll()
    if s.interp_state == linuxcnc.INTERP_IDLE:
        break
    line = max(line, s.motion_line)
    spindle = max(spindle, abs(s.spindle[0]["speed"]))
    if s.tool_in_spindle == 1 and s.spindle[0]["enabled"]:
        work = [s.position[i] - s.g5x_offset[i] - s.tool_offset[i] for i in range(3)]
        low = [min(a, b) for a, b in zip(low, work)]
        high = [max(a, b) for a, b in zip(high, work)]
    time.sleep(0.01)
out["run"] = {"seconds": round(time.time() - start, 2),
              "idle": s.interp_state == linuxcnc.INTERP_IDLE,
              "low": [round(v, 3) for v in low], "high": [round(v, 3) for v in high],
              "spindle": spindle, "tool": s.tool_in_spindle, "line": line,
              "errors": call("machine.state")["errors"]}
print("RESULT " + json.dumps(out))
'''


@pytest.mark.linuxcnc
@pytest.mark.timeout(420)
def test_cam_program_pipeline_on_linuxcnc_plant(tmp_path, monkeypatch):
    """CAM -> zapis -> sprawdzenie -> szacunek -> symulacja -> wczytanie -> przebieg."""
    monkeypatch.setattr(plant_session, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "HAL", BETA / "hal")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(
        filter(None, [str(BETA / "src"), os.environ.get("PYTHONPATH", "")])))
    machine = BETA / "config/machines/mill_servo_table.yaml"
    r, log, _ = plant_session.run_generated_plant(
        tmp_path, machine, PIPELINE, port=47862, timeout=360, copy_macros=False)
    if os.environ.get("LINUMERT_BETA_REPORT"):
        Path(os.environ["LINUMERT_BETA_REPORT"]).write_text(
            json.dumps(r, indent=2), encoding="utf-8")
    assert r["check"]["ok"] and not r["check"]["violations"], r
    assert r["run"]["idle"] and r["run"]["errors"] == [], r
    assert r["run"]["tool"] == 1 and r["run"]["spindle"] > 0, r
    assert "G53 G0 Z-1" in r["program"] and "G53 G0 Z0" not in r["program"], r
    assert r["over"] == [["X", "max"]], r
    # Kieszeń 30x20 wokół (20, 15), frez 6 mm, głębokość 2: to samo w podglądzie i na maszynie.
    bounds = r["toolpath"]["bounds"]
    assert [bounds["max_x"], bounds["max_y"], bounds["min_z"]] == pytest.approx([32, 22, -2]), r
    assert r["run"]["high"][:2] == pytest.approx([32, 22], abs=0.3), r
    assert r["run"]["low"][2] == pytest.approx(-2, abs=0.05), r
    assert r["estimate"]["source"] == "rs274" and r["sim"]["source"] == "rs274", r
    # 30x20x2 minus zaokrąglenia naroży: objętość kieszeni 1200 mm3.
    assert r["sim"]["volume_removed_mm3"] == pytest.approx(1200, rel=0.1), r
