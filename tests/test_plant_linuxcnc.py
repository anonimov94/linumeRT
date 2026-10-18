"""LinuxCNC + Plant od końca do końca: config/plant/linumert_plant_xyz (sesja 018).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 018.
Bez ekranu (zastępczy DISPLAY), Plant lockstep na localhost. Bazowanie wszystkich osi z losowego
startu (krańcówki NC z Plant, portal Y synchronicznie), ruch G1, błąd nadążania z napędów Plant.
Marker `linuxcnc`; wymaga RIP (tools/ci/build-linuxcnc.sh) i rdzenia Plant (make -C plant/core
shared).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

import pytest
from rip_support import (
    installed_modules,
    plant_server,
    rip_root,
    rip_run,
    start_linuxcnc,
    stop_linuxcnc,
)

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "plant" / "linumert_plant_xyz"
PORT = 47792


def _prepare(work: Path) -> Path:
    cfg = work / "cfg"
    shutil.copytree(CFG, cfg, symlinks=True)
    ini = cfg / "linumert_plant_xyz.ini"
    text = ini.read_text(encoding="utf-8")
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    text = re.sub(r"^POSTGUI_HALFILE.*$", "", text, flags=re.M)
    text = text.replace("PORT = 47700", f"PORT = {PORT}")
    text = text.replace("PROGRAM_PREFIX = ../../sim/nc_files",
                        f"PROGRAM_PREFIX = {ROOT / 'config/sim/nc_files'}")
    text = text.replace("TOOL_TABLE = ../../sim/linumert_xyz/tool.tbl",
                        f"TOOL_TABLE = {ROOT / 'config/sim/linumert_xyz/tool.tbl'}")
    ini.write_text(text, encoding="utf-8")
    script = cfg / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    return ini


DRIVER = r'''
import json, sys, time
import linuxcnc
c, s, e = linuxcnc.command(), linuxcnc.stat(), linuxcnc.error_channel()
out = {"errors": []}
def wait(cond, timeout):
    t = time.time()
    while time.time() - t < timeout:
        s.poll()
        msg = e.poll()
        if msg:
            out["errors"].append(msg[1])
        if cond():
            return True
        time.sleep(0.05)
    return False
c.state(linuxcnc.STATE_ESTOP_RESET)
out["estop_reset"] = wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 5)
c.state(linuxcnc.STATE_ON)
out["machine_on"] = wait(lambda: s.task_state == linuxcnc.STATE_ON, 5)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.teleop_enable(0); c.wait_complete()
t0 = time.time()
c.home(-1)
out["homed"] = wait(lambda: all(s.homed[:4]), 120)
out["home_s"] = round(time.time() - t0, 1)
time.sleep(0.5); s.poll()
out["after_home"] = [round(v, 3) for v in s.actual_position[:3]]
c.teleop_enable(1); c.wait_complete()
c.mode(linuxcnc.MODE_MDI); c.wait_complete()
c.mdi("G90 G1 X100 Y200 Z-20 F3000"); c.wait_complete(60)
out["moved"] = wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 60)
time.sleep(0.5); s.poll()
out["pos"] = [round(v, 4) for v in s.actual_position[:3]]
out["joint_ferror_max"] = max(abs(s.joint[i]["ferror_highmark"]) for i in range(4))
out["task_state"] = s.task_state
out["errors_motion"] = list(out["errors"]); out["errors"] = []
# softlimit_oracle: MDI poza soft limit X (599) — LinuxCNC powinien odrzucić
c.mdi("G90 G0 X700"); c.wait_complete(30)
wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 30)
time.sleep(0.3); s.poll()
out["softlimit_errors"] = list(out["errors"]); out["errors"] = []
out["after_softlimit"] = [round(v, 3) for v in s.actual_position[:3]]
c.state(linuxcnc.STATE_ON); c.mode(linuxcnc.MODE_MDI); c.wait_complete()
# forbidden_zone_oracle: wjazd w strefę magazynu (LinuxCNC jej nie zna)
c.mdi("G53 G0 Z-5"); c.wait_complete(30)
c.mdi("G53 G0 X560 Y860"); c.wait_complete(60)
wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 60)
time.sleep(0.3); s.poll()
out["zone_pos"] = [round(v, 3) for v in s.actual_position[:3]]
out["zone_task"] = [s.task_state, s.task_mode, s.interp_state]
c.mdi("G53 G0 X100 Y200"); c.wait_complete(60)
wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 60)
time.sleep(0.5); s.poll()
out["zone_pos_back"] = [round(v, 3) for v in s.actual_position[:3]]
out["zone_errors"] = list(out["errors"])
print("RESULT " + json.dumps(out))
'''


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    """Jedna sesja LinuxCNC + Plant dla wszystkich testów modułu (ok. 90 s)."""
    root = rip_root()
    tmp_path = tmp_path_factory.mktemp("plant_cnc")
    ini = _prepare(tmp_path)
    (tmp_path / "driver.py").write_text(DRIVER, encoding="utf-8")
    report = tmp_path / "plant_report.json"
    plant_yaml = CFG / "plant.yaml"  # ścieżka machine względem oryginału
    with installed_modules(root, tmp_path, ("lrt_net", "lrt_cia402")), \
            plant_server(plant_yaml, PORT, "--seed", "5", "--report", str(report)):
        env = {**os.environ, "PATH": f"{ini.parent}:{os.environ.get('PATH', '')}"}
        cnc = start_linuxcnc(root, ini, env)
        try:
            ready = False
            for _ in range(60):  # LinuxCNC gotowy, gdy halcmd widzi połączenie lrt-net
                time.sleep(0.5)
                if cnc.poll() is not None:
                    break
                probe = rip_run(root, "halcmd getp lrt-net.0.connected", ini.parent, env=env)
                if probe.stdout.strip() == "TRUE":
                    ready = True
                    break
            assert ready, (cnc.stdout.read() if cnc.poll() is not None else "brak połączenia")
            time.sleep(1.0)
            run = rip_run(root, f"python3 {tmp_path / 'driver.py'}", ini.parent, timeout=300,
                          env=env)
            hal = rip_run(root, "halcmd getp lrt-net.0.axis.0.ferror; "
                          "halcmd getp lrt-net.0.plant-lost; halcmd getp lrt-net.0.bad-frames",
                          ini.parent, env=env).stdout.split()
        finally:
            stop_linuxcnc(cnc, root, ini.parent)
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, run.stdout + run.stderr
    res = json.loads(line[len("RESULT "):])
    res["hal"] = hal
    res["plant"] = json.loads(report.read_text(encoding="utf-8"))
    return res


def test_plant_linuxcnc_home_and_move(session):  # REQ-VM-02, REQ-VM-07
    res = session
    assert res["estop_reset"] and res["machine_on"], res
    assert res["homed"], res  # bazowanie na krańcówkach Plant, portal Y synchronicznie
    assert res["after_home"] == pytest.approx([5.0, 5.0, -5.0], abs=0.01)
    assert res["moved"], res
    assert res["pos"] == pytest.approx([100.0, 200.0, -20.0], abs=0.005)
    assert res["joint_ferror_max"] < 0.5, res  # MIN_FERROR = 0,5 mm
    assert res["errors_motion"] == [], res
    assert abs(float(res["hal"][0])) < 0.01  # napęd X Plant stoi bez błędu nadążania
    assert res["hal"][1:] == ["0", "0"]  # utracone ramki, odrzucone odpowiedzi


def _violations(res, kind):
    return [v for v in res["plant"]["oracle"]["violations"] if v["kind"] == kind]


def test_softlimit_oracle(session):  # REQ-VM-06: scenariusz softlimit_oracle
    res = session
    assert res["softlimit_errors"], "LinuxCNC powinien odrzucić G0 X700 (soft limit 599)"
    assert res["after_softlimit"][0] == pytest.approx(100.0, abs=0.01)  # bez ruchu
    assert _violations(res, "soft_limit") == []  # wyrocznia: żadna pozycja zadana poza zakresem
    assert res["plant"]["oracle"]["frames_checked"] > 1000  # uzbrojona po bazowaniu


def test_forbidden_zone_oracle(session):  # REQ-VM-06: scenariusz forbidden_zone_oracle
    res = session
    zone = _violations(res, "zone")
    assert [v["name"] for v in zone] == ["magazyn_narzedzi"], (  # wjazd wykryty, raz
        res.get("zone_pos"), res.get("zone_task"), res.get("zone_errors"), res["plant"]["oracle"])
    x, y, _ = zone[0]["position"]
    assert 520 < x < 600 and 820 < y < 900
    assert res["plant"]["oracle"]["result"] == "FAIL"  # scenariusz z wjazdem = FAIL raportu
    assert res["zone_pos_back"][:2] == pytest.approx([100.0, 200.0], abs=0.01)
