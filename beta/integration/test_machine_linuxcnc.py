# SPDX-License-Identifier: GPL-2.0-or-later
"""Odbiór operacji domeny machine na LinuxCNC RIP + Plant (portal: osie X Y Z, jointy 0 1 2 3).

Model-Author: Claude. Każdy krok idzie przez kontrakt (`call_json`), jak z GUI. Bez GUI.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

BETA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BETA.parent / "tests"))
import plant_session  # noqa: E402
import rip_support  # noqa: E402

DRIVER = r'''
from pathlib import Path
from linumert_headless.app import build_application
from linumert_headless.config import AppConfig
app = build_application(AppConfig(root=Path.cwd(), backend="linuxcnc", autostart=False))
out = {"on": on, "homed": homed, "errors": {}}
def call(name, params=None):
    """Wynik operacji albo opis błędu: jeden błąd nie przykrywa kolejnych kroków."""
    try:
        reply = app.call_json(name, params or {})
    except Exception as exc:
        out["errors"].setdefault(name, []).append(f"{type(exc).__name__}: {exc}")
        return None
    time.sleep(0.2)
    return reply
def pos():
    """Pozycja zadana: uchyb nadążania Plant nie jest przedmiotem tego odbioru."""
    s.poll()
    return [round(p, 4) for p in s.position[:3]]
def refused(name, params):
    try:
        app.call_json(name, params)
    except Exception as exc:
        return getattr(exc, "code", type(exc).__name__)
    return None
def settle(timeout=60):
    quiet = [0]
    def still():
        ok = abs(s.current_vel) < 1e-4 and s.inpos
        quiet[0] = quiet[0] + 1 if ok else 0
        return quiet[0] >= 15
    return wait(still, timeout)
def state():
    return app.call_json("machine.state")

first = state()
out["state"] = {k: first[k] for k in ("task_state", "mode", "all_homed", "backend", "fresh")}
out["axes"] = [a["name"] for a in first["axes"]]

# Tryby
out["modes"] = {}
for name in ("manual", "mdi", "auto", "manual"):
    call("machine.set_mode", {"mode": name})
    out["modes"][name] = state()["mode"]

# JOG przyrostowy w obie strony, każda oś osobno
for axis, index, speed, distance in (("X", 0, 10, 5), ("X", 0, -10, 2), ("Y", 1, 10, 5),
                                     ("Z", 2, -10, 3)):
    start = pos()
    call("machine.jog_increment", {"axis": axis, "speed": speed, "distance": distance})
    settle()
    end = pos()
    out[f"inc_{axis}_{speed}"] = [round(e - b, 4) for b, e in zip(start, end)]

# JOG ciągły i stop
start = pos()
call("machine.jog", {"axis": "Z", "speed": -5, "session": "t"})
time.sleep(0.6)
call("machine.jog_stop", {"axis": "Z"})
settle()
end = pos()
out["jog_z"] = [round(e - b, 4) for b, e in zip(start, end)]

# MDI i układ detalu
call("machine.mdi", {"text": "G90 G53 G0 X50 Y60"})
settle()
out["mdi"] = pos()[:2]
call("machine.set_work_offset", {"name": "G55", "values": {"X": 12.5}})
settle()
s.poll()
call("machine.mdi", {"text": "G55"})
settle()
s.poll()
out["g55"] = [state()["work_offset_name"], round(s.g5x_offset[0], 4)]
call("machine.mdi", {"text": "G54"})
settle()

# Nastawy i wrzeciono
call("machine.set_override", {"feed": 0.5, "rapid": 0.25, "spindle": 0.8})
time.sleep(0.3)
s.poll()
out["override"] = [round(s.feedrate, 3), round(s.rapidrate, 3), round(s.spindle[0]["override"], 3)]
call("machine.set_override", {"feed": 1.0, "rapid": 1.0, "spindle": 1.0})
call("machine.spindle", {"speed": 1200, "direction": 1})
wait(lambda: s.spindle[0]["direction"] == 1, 10)
out["spindle_on"] = [s.spindle[0]["speed"], s.spindle[0]["direction"]]
call("machine.spindle", {"speed": 0, "direction": 0})
wait(lambda: s.spindle[0]["direction"] == 0, 10)
out["spindle_off"] = s.spindle[0]["direction"]

# Program: wczytanie, start, pauza, wznowienie, stop, przebieg do końca
text = "G21 G90 G54\nG1 F600 X60\nG1 X100\nG1 X140\nG1 X60\nM2\n"
call("program.write", {"name": "odbior.ngc", "text": text})
out["load"] = call("program.load", {"name": "odbior.ngc"})
s.poll()
out["loaded_file"] = s.file
call("machine.run", {"from_line": 0})
out["started"] = wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE and s.current_vel > 0, 20)
call("machine.pause")
out["paused"] = wait(lambda: s.paused or s.task_paused, 10)
settle(10)
paused_at = pos()[0]
time.sleep(0.5)
out["pause_holds"] = abs(pos()[0] - paused_at) < 0.001
call("machine.resume")
out["resumed"] = wait(lambda: not (s.paused or s.task_paused) and s.current_vel > 0, 10)
call("machine.stop")
out["stopped"] = wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 20)
settle()
s.poll()
offset_x = s.g5x_offset[0]
call("machine.run")
wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 20)
out["finished"] = wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 120)
settle()
out["end_x"] = round(pos()[0] - offset_x, 4)

# Zasilanie i E-STOP
call("machine.power_off")
# LinuxCNC po STATE_OFF raportuje ESTOP_RESET (brak aktywnego E-STOP i wyłączone osie).
out["off"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 10)
call("machine.power_on")
out["on2"] = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)
call("machine.estop")
out["estop"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP, 10)
out["refused_when_estop"] = refused("machine.jog_increment",
                                    {"axis": "X", "speed": 10, "distance": 1})
out["power_on_in_estop"] = refused("machine.power_on", {})
time.sleep(1.0)
s.poll()
out["estop_latched"] = s.task_state == linuxcnc.STATE_ESTOP
call("machine.estop_reset")
out["estop_reset"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 10)
call("machine.power_on")
out["on3"] = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)

# Bazowanie przez API: po każdej osi właściwe jointy (portal Y = 1 i 2, Z = 3)
for name, joints in (("Z", [3]), ("Y", [1, 2])):
    c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
    c.teleop_enable(0); c.wait_complete()
    for j in joints:
        c.unhome(j); c.wait_complete()
    wait(lambda: not any(s.homed[j] for j in joints), 10)
    out[f"all_homed_without_{name}"] = state()["all_homed"]
    c.mode(linuxcnc.MODE_MDI); c.wait_complete()   # usługa sama przełącza tryb i teleop
    call("machine.home", {"axis": name})
    out[f"home_{name}"] = wait(lambda: all(s.homed[j] for j in joints), 120)
    settle()
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.teleop_enable(0); c.wait_complete()
c.unhome(-1); c.wait_complete()
wait(lambda: not any(s.homed[j] for j in range(s.joints)), 10)
# Przed bazowaniem: Z (sekwencja 0) jeździ jointem, X (sekwencja -1, razem z portalem) odmawia
# w LinuxCNC, a portal już w usłudze. Odmowa LinuxCNC musi dojść do klienta odpytującego stan.
before = s.joint[3]["output"]
call("machine.jog_increment", {"axis": "Z", "speed": -10, "distance": 1})
wait(lambda: abs(s.joint[3]["output"] - before) >= 0.9995, 20)
out["joint_jog"] = round(s.joint[3]["output"] - before, 4)
call("machine.jog_increment", {"axis": "X", "speed": 10, "distance": 1})
c.wait_complete(2)
call("machine.jog_stop", {"axis": "Z"})             # własna migawka usługi nie kasuje komunikatu
out["x_refusal"] = state()["errors"]
out["gantry_jog"] = refused("machine.jog_increment", {"axis": "Y", "speed": 10, "distance": 1})
call("machine.jog_stop")
c.mode(linuxcnc.MODE_MDI); c.wait_complete()
call("machine.home")
out["home_all"] = wait(lambda: all(s.homed[j] for j in range(s.joints)), 240)
settle()
start = pos()
call("machine.jog_increment", {"axis": "X", "speed": 10, "distance": 1})
settle()
out["jog_after_home"] = round(pos()[0] - start[0], 4)
print("RESULT " + json.dumps(out))
'''


SIM_DRIVER = r'''
from pathlib import Path
from linumert_headless.app import build_application
from linumert_headless.config import AppConfig
app = build_application(AppConfig(root=Path.cwd(), backend="linuxcnc", autostart=False))
out = {"on": on, "homed": homed}
app.call_json("machine.estop")
out["estop"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP, 10)
app.call_json("machine.estop_reset")
out["reset"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 10)
app.call_json("machine.power_on")
out["on2"] = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)
print("RESULT " + json.dumps(out))
'''


@pytest.fixture
def beta_paths(monkeypatch):
    monkeypatch.setattr(plant_session, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "HAL", BETA / "hal")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(
        filter(None, [str(BETA / "src"), os.environ.get("PYTHONPATH", "")])))


@pytest.mark.linuxcnc
@pytest.mark.timeout(240)
def test_beta_sim_config_runs_without_screen(tmp_path, beta_paths):
    """Wygenerowana symulacja startuje bez ekranu; E-STOP z API zatrzaskuje się i resetuje."""
    root = rip_support.rip_root()
    if rip_support.leftovers():
        pytest.skip(f"działa inny LinuxCNC: {rip_support.leftovers()}")
    out = tmp_path / "sim_cfg"
    machine = BETA / "config/machines/mill_servo_table.yaml"
    assert plant_session.main(["build", str(machine), "--target", "sim", "--out", str(out),
                               "--write"]) == 0
    ini = next(out.glob("*.ini"))
    text = ini.read_text(encoding="utf-8")
    ini.write_text(text.replace("DISPLAY = linumert_headless", "DISPLAY = linumert_bez_ekranu")
                   .replace("../../hal/", f"{BETA / 'config/hal'}/")
                   .replace("../../sim/", f"{BETA / 'config/sim'}/"), encoding="utf-8")
    shutil.copy(BETA / "config/sim/linumert_xyz/linumert.var.default", out / "linumert.var")
    script = out / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    driver = tmp_path / "driver.py"
    driver.write_text(plant_session.DRIVER_PRELUDE + SIM_DRIVER, encoding="utf-8")
    env = {**os.environ, "PATH": f"{out}{os.pathsep}{os.environ['PATH']}",
           "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(out)}
    cnc = rip_support.start_linuxcnc(root, ini, env)
    try:
        run = rip_support.rip_run(root, f"python3 {driver}", out, timeout=180, env=env)
    finally:
        rip_support.stop_linuxcnc(cnc, root, out)
        log = cnc.stdout.read() if cnc.stdout else ""
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, f"{run.stdout}{run.stderr}\n--- LinuxCNC ---\n{log[-3000:]}"
    assert json.loads(line[7:]) == {"on": True, "homed": True, "estop": True, "reset": True,
                                    "on2": True}


@pytest.mark.linuxcnc
@pytest.mark.timeout(600)
def test_beta_machine_operations_on_linuxcnc_plant(tmp_path, beta_paths):
    machine = BETA / "config/machines/mill_servo_table.yaml"
    r, log, _ = plant_session.run_generated_plant(
        tmp_path, machine, DRIVER, port=47858, timeout=480, copy_macros=False)
    if os.environ.get("LINUMERT_BETA_REPORT"):
        Path(os.environ["LINUMERT_BETA_REPORT"]).write_text(
            json.dumps(r, indent=2), encoding="utf-8")
    assert r["errors"] == {}, r
    assert r["on"] and r["homed"], r
    assert r["state"] == {"task_state": "on", "mode": r["state"]["mode"], "all_homed": True,
                          "backend": "linuxcnc", "fresh": True}, r
    assert r["axes"] == ["X", "Y", "Z"], r
    assert r["inc_X_10"] == pytest.approx([5, 0, 0], abs=1e-3), r
    assert r["inc_X_-10"] == pytest.approx([-2, 0, 0], abs=1e-3), r
    assert r["inc_Y_10"] == pytest.approx([0, 5, 0], abs=1e-3), r
    assert r["inc_Z_-10"] == pytest.approx([0, 0, -3], abs=1e-3), r
    assert r["jog_z"][2] < -0.5 and r["jog_z"][:2] == pytest.approx([0, 0], abs=1e-3), r
    assert r["mdi"] == pytest.approx([50, 60], abs=1e-3), r
    assert r["g55"] == ["G55", 12.5], r
    assert r["override"] == [0.5, 0.25, 0.8], r
    assert r["spindle_on"] == [1200, 1] and r["spindle_off"] == 0, r
    for key in ("started", "paused", "pause_holds", "resumed", "stopped", "finished",
                "off", "on2", "estop", "estop_reset", "on3",
                "home_Z", "home_Y", "home_all"):
        assert r[key], (key, r)
    assert r["refused_when_estop"] == "safety_refused", r
    assert r["power_on_in_estop"] == "safety_refused" and r["estop_latched"], r
    assert r["all_homed_without_Z"] is False and r["all_homed_without_Y"] is False, r
    assert r["joint_jog"] == pytest.approx(-1, abs=1e-3), r
    assert any("synchronized" in text for text in r["x_refusal"]), r
    assert r["gantry_jog"] == "safety_refused", r
    assert r["loaded_file"].endswith("odbior.ngc"), r
    assert r["end_x"] == pytest.approx(60, abs=1e-3), r
    assert r["jog_after_home"] == pytest.approx(1, abs=1e-3), r
