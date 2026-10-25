# SPDX-License-Identifier: GPL-2.0-or-later
"""Wygenerowana konfiguracja Plant uruchomiona bezpośrednio w LinuxCNC (sesja 062, odbiór).

Model-Author: Claude · 2026-10-25. `linumert-config build --target plant` → LinuxCNC RIP + serwer
Plant (lockstep, localhost, `lrt_net`) → włączenie, bazowanie wszystkich osi na wirtualnych
czujnikach i ruch MDI. Wcześniej wynik sprawdzano tylko przez równość z ręczną konfiguracją.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import shutil
import time
from pathlib import Path

import pytest
from linumert.machine.config_build import main

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
PORT = 47851

DRIVER = r"""
import json, os, sys, time
import linuxcnc
for _ in range(240):          # NML bywa niegotowy; poll() mapuje narzędzia
    try:
        if not os.path.exists(os.path.expanduser("~/.tool.mmap")):   # tworzy go iocontrol
            raise SystemError("brak danych narzedzi")
        s = linuxcnc.stat(); s.poll(); break
    except (linuxcnc.error, SystemError):
        time.sleep(0.5)
c = linuxcnc.command()
def wait(cond, timeout):
    end = time.time() + timeout
    while time.time() < end:
        s.poll()
        if cond():
            return True
        time.sleep(0.05)
    return False
c.state(linuxcnc.STATE_ESTOP_RESET); c.wait_complete()
c.state(linuxcnc.STATE_ON); c.wait_complete()
on = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.home(-1)
homed = wait(lambda: all(s.homed[j] for j in range(s.joints)), 240)
s.poll()
home_pos = [round(v, 3) for v in s.joint_actual_position[:s.joints]]
c.teleop_enable(1); c.wait_complete()
c.mode(linuxcnc.MODE_MDI); c.wait_complete()
c.mdi("G21 G90 G53 G1 X50 F1200"); c.wait_complete()
at_x = lambda: abs(s.actual_position[0] - 50) < 0.05
moved = wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE and at_x(), 60)
s.poll()
print("RESULT " + json.dumps({"on": on, "homed": homed, "joints": s.joints, "home": home_pos,
      "moved": moved, "x": round(s.actual_position[0], 3), "estop": s.estop}))
"""


# REQ-VM-01
@pytest.mark.linuxcnc
def test_generated_plant_config_runs_homes_and_moves_in_linuxcnc(tmp_path):
    import rip_support as rip

    root = rip.rip_root()
    if rip.leftovers():
        pytest.skip(f"działa inny LinuxCNC: {rip.leftovers()}")
    out = tmp_path / "plant_cfg"
    assert main(["build", str(MILL), "--target", "plant", "--out", str(out), "--port", str(PORT),
                 "--write"]) == 0
    ini = out / "mill_servo_table.ini"
    text = ini.read_text(encoding="utf-8")
    assert "lrt_net" in (out / "linumert_plant.hal").read_text(encoding="utf-8")
    # Bez ekranu: zastępczy DISPLAY i jawne obejście grzyba HMI (tylko w teście bez ekranu).
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    # Katalog tymczasowy: ścieżki względne z repozytorium zamieniamy na bezwzględne.
    text = text.replace("../../hal/", f"{ROOT / 'config/hal'}/")
    text = text.replace("../../sim/", f"{ROOT / 'config/sim'}/")
    shutil.copy(ROOT / "config/sim/linumert_xyz/linumert.var.default", out / "linumert.var")
    shutil.copytree(ROOT / "config/sim/linumert_xyz/macros", out / "macros")
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    ini.write_text(text, encoding="utf-8")
    script = out / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    driver = tmp_path / "driver.py"
    driver.write_text(DRIVER, encoding="utf-8")
    env = {**os.environ, "PATH": f"{out}{os.pathsep}{os.environ['PATH']}",
           "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(out)}
    with contextlib.ExitStack() as stack:
        stack.enter_context(rip.installed_modules(root, tmp_path,
                                                  ("lrt_net", "lrt_cia402", "lrt_estop2")))
        stack.enter_context(rip.plant_server(MILL, PORT, "--seed", "5"))
        cnc = rip.start_linuxcnc(root, ini, env)
        try:
            for _ in range(120):
                time.sleep(0.5)
                if cnc.poll() is not None:
                    break
                link = rip.rip_run(root, "halcmd getp lrt-net.0.connected", out, env=env)
                if link.stdout.strip() == "TRUE":
                    break
            assert cnc.poll() is None, cnc.stdout.read() if cnc.stdout else "LinuxCNC zakończony"
            time.sleep(1)                       # początkowa informacja zwrotna Plant
            run = rip.rip_run(root, "python3 " + shlex.quote(str(driver)), out, timeout=420,
                              env=env)
        finally:
            rip.stop_linuxcnc(cnc, root, out)
            log = cnc.stdout.read() if cnc.stdout else ""
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, f"{run.stdout}{run.stderr}\n--- LinuxCNC ---\n{log[-3000:]}"
    result = json.loads(line[7:])
    assert result["on"] and result["homed"], result
    assert result["moved"] and result["x"] == pytest.approx(50, abs=0.05), result
    assert not result["estop"], result
