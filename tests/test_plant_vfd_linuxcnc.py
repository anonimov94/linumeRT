"""LinuxCNC + hy_vfd + falownik Plant: config/plant/linumert_plant_xyz wariant _vfd (sesja 021).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 021.
Prawdziwy komponent `hy_vfd` z RIP rozmawia z emulatorem falownika Plant przez pseudoterminal
(plant_vfd.yaml `vfd.device` = INI [VFD]DEVICE).
Po bazowaniu: M3 S6000 → at-speed, M4 → wstecz, M5 → 0.
Bez ekranu; marker `linuxcnc`. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import pytest
import yaml
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
PORT = 47793

DRIVER = r'''
import json, time
import linuxcnc, hal
c, s = linuxcnc.command(), linuxcnc.stat()
_comp = hal.component("vfd_test_driver"); _comp.ready()  # hal.get_value wymaga komponentu
out = {}
def wait(cond, timeout):
    t = time.time()
    while time.time() - t < timeout:
        s.poll()
        if cond():
            return True
        time.sleep(0.05)
    return False
def pin(name):
    return hal.get_value(name)
c.state(linuxcnc.STATE_ESTOP_RESET); wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 5)
c.state(linuxcnc.STATE_ON); out["on"] = wait(lambda: s.task_state == linuxcnc.STATE_ON, 5)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.teleop_enable(0); c.wait_complete()
c.home(-1)
out["homed"] = wait(lambda: all(s.homed[:4]), 120)  # MDI wymaga bazowania
c.teleop_enable(1); c.wait_complete()
c.mode(linuxcnc.MODE_MDI); c.wait_complete()
t0 = time.time()
c.mdi("M3 S6000"); c.wait_complete(30)
out["m3_at_speed"] = wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE
                          and pin("vfd.spindle-at-speed"), 30)
out["m3_s"] = round(time.time() - t0, 1)
time.sleep(0.5)
out["m3"] = [pin("vfd.spindle-speed-fb"), pin("lrt-net.0.spindle-speed-fb"), pin("vfd.hycomm-ok")]
c.mdi("M4 S3000"); c.wait_complete(30)
# hy_vfd porównuje obroty bez znaku: przy nawrocie at-speed jest chwilowo prawdziwe w przejściu
# przez |S| podczas hamowania, więc czekamy na obroty wstecz z Plant.
out["m4_at_speed"] = wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE
                          and pin("lrt-net.0.spindle-speed-fb") < -2900
                          and pin("vfd.spindle-at-speed"), 30)
time.sleep(0.5)
out["m4"] = [pin("vfd.spindle-speed-fb"), pin("lrt-net.0.spindle-speed-fb")]
c.mdi("M5"); c.wait_complete(30)
out["m5_stopped"] = wait(lambda: abs(pin("lrt-net.0.spindle-speed-fb")) < 1, 20)
out["m5"] = [pin("vfd.spindle-speed-fb"), pin("vfd.spindle-at-speed")]
print("RESULT " + json.dumps(out))
'''


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    root = rip_root()
    work = tmp_path_factory.mktemp("plant_vfd")
    cfg = work / "cfg"
    shutil.copytree(CFG, cfg, symlinks=True)
    device = work / "hy_vfd"
    ini = cfg / "linumert_plant_xyz_vfd.ini"
    text = ini.read_text(encoding="utf-8")
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    # Bez ekranu nie ma grzyba HMI ani sygnału życia (D35): jawne obejście tylko tutaj;
    # plik HAL grzyba z repozytorium (ścieżka względna nie działa w kopii konfiguracji).
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    text = text.replace("HALFILE = ../../hal/", f"HALFILE = {CFG.parent.parent / 'hal'}/")
    text = "\n".join(x for x in text.splitlines() if not x.startswith("POSTGUI_HALFILE")) + "\n"
    text = text.replace("PORT = 47700", f"PORT = {PORT}")
    text = text.replace("DEVICE = /tmp/linumert-hy_vfd", f"DEVICE = {device}")
    text = text.replace("PROGRAM_PREFIX = ../../sim/nc_files",
                        f"PROGRAM_PREFIX = {ROOT / 'config/sim/nc_files'}")
    text = text.replace("TOOL_TABLE = ../../sim/linumert_xyz/tool.tbl",
                        f"TOOL_TABLE = {ROOT / 'config/sim/linumert_xyz/tool.tbl'}")
    ini.write_text(text, encoding="utf-8")
    script = cfg / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    plant = yaml.safe_load((CFG / "plant_vfd.yaml").read_text(encoding="utf-8"))
    plant["machine"] = str((CFG / plant["machine"]).resolve())
    plant["vfd"] = {"device": str(device)}
    plant_yaml = work / "plant.yaml"
    plant_yaml.write_text(yaml.safe_dump(plant), encoding="utf-8")
    (work / "driver.py").write_text(DRIVER, encoding="utf-8")
    report = work / "report.json"
    with installed_modules(root, work, ("lrt_net", "lrt_cia402")), \
            plant_server(plant_yaml, PORT, "--report", str(report)):
        env = {**os.environ, "PATH": f"{cfg}:{os.environ.get('PATH', '')}"}
        cnc = start_linuxcnc(root, ini, env)
        try:
            ready = False
            for _ in range(60):
                time.sleep(0.5)
                if cnc.poll() is not None:
                    break
                probe = rip_run(root, "halcmd getp lrt-net.0.connected", cfg, env=env)
                if probe.stdout.strip() == "TRUE":
                    ready = True
                    break
            assert ready, (cnc.stdout.read() if cnc.poll() is not None else "brak połączenia")
            time.sleep(1.0)
            run = rip_run(root, f"python3 {work / 'driver.py'}", cfg, timeout=180, env=env)
        finally:
            stop_linuxcnc(cnc, root, cfg)
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, run.stdout + run.stderr
    res = json.loads(line[len("RESULT "):])
    res["plant"] = json.loads(report.read_text(encoding="utf-8"))
    return res


def test_hy_vfd_m3_at_speed(session):  # REQ-VD-01: wrzeciono VFD z prawdziwym hy_vfd
    assert session["on"] and session["homed"] and session["m3_at_speed"], session
    fb, plant_rpm, ok = session["m3"]
    assert ok
    assert fb == pytest.approx(6000, rel=0.02)
    assert plant_rpm == pytest.approx(6000, rel=0.02)


def test_hy_vfd_m4_reverse(session):  # REQ-VD-01
    assert session["m4_at_speed"], session
    fb, plant_rpm = session["m4"]
    assert fb == pytest.approx(3000, rel=0.02)  # hy_vfd podaje obroty bez znaku
    assert plant_rpm == pytest.approx(-3000, rel=0.02)


def test_hy_vfd_m5_stops(session):  # REQ-VD-01
    assert session["m5_stopped"], session
    assert session["m5"] == [0.0, False]
    assert session["plant"]["spindle"]["fault"] == 0
