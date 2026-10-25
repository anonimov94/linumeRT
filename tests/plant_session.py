# SPDX-License-Identifier: GPL-2.0-or-later
"""Wspólna sesja: wygenerowana konfiguracja Plant + LinuxCNC RIP + serwer Plant (lockstep).

Model-Author: Claude · 2026-10-25. Pomocnik testów z markerem `linuxcnc` (sesje 062, 033).
`run_generated_plant` generuje `linumert-config build --target plant`, uruchamia LinuxCNC bez ekranu
i serwer Plant, wykonuje skrypt kierowcy pod rip-environment i zwraca słownik
z linii `RESULT {json}`.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import rip_support as rip
from linumert.machine.config_build import main

ROOT = Path(__file__).resolve().parents[1]

# Początek skryptu kierowcy: gotowy NML, `c`, `s`, `wait`, `mdi`, włączenie i bazowanie.
DRIVER_PRELUDE = r"""
import json, os, sys, time
import linuxcnc
for _ in range(240):          # NML bywa niegotowy; poll() mapuje narzędzia (~/.tool.mmap)
    try:
        if not os.path.exists(os.path.expanduser("~/.tool.mmap")):
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
        time.sleep(0.02)
    return False
def idle():
    return s.interp_state == linuxcnc.INTERP_IDLE and s.state == linuxcnc.RCS_DONE
def mdi(cmd, timeout=90):
    print("MDI", cmd, flush=True)
    c.mode(linuxcnc.MODE_MDI); c.wait_complete()
    c.mdi(cmd)
    serial = c.serial
    # Lockstep Plant spowalnia LinuxCNC: poczekaj na przyjęcie komendy, potem na koniec ruchu.
    wait(lambda: s.echo_serial_number >= serial, timeout)
    quiet = [0]
    def settled():
        still = abs(s.current_vel) < 1e-4 and idle()
        quiet[0] = quiet[0] + 1 if still else 0
        return quiet[0] >= 15                       # ~0,3 s bez ruchu
    return wait(settled, timeout)
c.state(linuxcnc.STATE_ESTOP_RESET); c.wait_complete()
c.state(linuxcnc.STATE_ON); c.wait_complete()
on = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.home(-1)
homed = wait(lambda: all(s.homed[j] for j in range(s.joints)), 240)
c.teleop_enable(1); c.wait_complete()
"""


def run_generated_plant(tmp_path: Path, machine: Path, driver_body: str, *, port: int,
                        timeout: float = 300) -> tuple[dict, str, Path]:
    """Zwraca (wynik kierowcy, log LinuxCNC, katalog konfiguracji). Pomija test, gdy zajęte."""
    root = rip.rip_root()
    if rip.leftovers():
        pytest.skip(f"działa inny LinuxCNC: {rip.leftovers()}")
    out = tmp_path / "plant_cfg"
    assert main(["build", str(machine), "--target", "plant", "--out", str(out), "--port",
                 str(port), "--write"]) == 0
    ini = next(out.glob("*.ini"))
    text = ini.read_text(encoding="utf-8")
    assert "lrt_net" in (out / "linumert_plant.hal").read_text(encoding="utf-8")
    # Bez ekranu: zastępczy DISPLAY i jawne obejście grzyba HMI (tylko w teście bez ekranu).
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    # Katalog tymczasowy: ścieżki względne z repozytorium zamieniamy na bezwzględne.
    text = text.replace("../../hal/", f"{ROOT / 'config/hal'}/")
    text = text.replace("../../sim/", f"{ROOT / 'config/sim'}/")
    ini.write_text(text, encoding="utf-8")
    shutil.copy(ROOT / "config/sim/linumert_xyz/linumert.var.default", out / "linumert.var")
    shutil.copytree(ROOT / "config/sim/linumert_xyz/macros", out / "macros")
    script = out / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    driver = tmp_path / "driver.py"
    driver.write_text(DRIVER_PRELUDE + driver_body, encoding="utf-8")
    env = {**os.environ, "PATH": f"{out}{os.pathsep}{os.environ['PATH']}",
           "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(out)}
    with contextlib.ExitStack() as stack:
        stack.enter_context(rip.installed_modules(root, tmp_path,
                                                  ("lrt_net", "lrt_cia402", "lrt_estop2")))
        stack.enter_context(rip.plant_server(machine, port, "--seed", "5"))
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
            try:
                run = rip.rip_run(root, "python3 " + shlex.quote(str(driver)), out,
                                  timeout=timeout, env=env)
            except subprocess.TimeoutExpired as exc:
                tail = (exc.stdout or b"")[-2500:]
                text = tail.decode(errors="replace") if isinstance(tail, bytes) else tail
                pytest.fail(f"kierowca przekroczył czas {timeout}s; ostatnie wyjście:\n{text}")
        finally:
            rip.stop_linuxcnc(cnc, root, out)
            log = cnc.stdout.read() if cnc.stdout else ""
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, f"{run.stdout}{run.stderr}\n--- LinuxCNC ---\n{log[-3000:]}"
    return json.loads(line[7:]), log, out
