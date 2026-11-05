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
import sys
import time
from pathlib import Path

import pytest
import rip_support as rip
from linumert.machine.config_build import main

ROOT = Path(__file__).resolve().parents[1]
# Zatrzask diagnostyczny (estop_latch) → sygnał HAL ogniwa łańcucha E-STOP.
DIAG_LATCHES = {"lrt_diag_conn": "lrt.connected", "lrt_diag_2ch": "linumert.io.estop-2ch",
                "lrt_diag_chain": "lrt.estop-ok-in"}

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
    now = time.time()                           # znacznik czasu jak w logu Plant
    print("MDI %s.%03d %s" % (time.strftime("%H:%M:%S", time.localtime(now)),
                              int(now % 1 * 1000), cmd), flush=True)
    c.mode(linuxcnc.MODE_MDI); c.wait_complete()
    c.mdi(cmd)
    serial = c.serial
    # Lockstep Plant spowalnia LinuxCNC: poczekaj na przyjęcie komendy, potem na koniec ruchu.
    t0 = time.time()
    echo = wait(lambda: s.echo_serial_number >= serial, timeout)
    quiet, busy = [0], [0]
    def settled():
        still = abs(s.current_vel) < 1e-4 and idle()
        busy[0] += not still
        quiet[0] = quiet[0] + 1 if still else 0
        return quiet[0] >= 15                       # ~0,3 s bez ruchu
    ok = wait(settled, timeout)
    # Diagnoza: busy=0 przy komendzie ruchu znaczy, że koniec wykryto przed startem ruchu.
    print("WAIT echo=%s ok=%s busy=%d t=%.2f state=%d interp=%d tripped=%d" % (
        echo, ok, busy[0], time.time() - t0, s.state, s.interp_state, s.probe_tripped),
        flush=True)
    return ok
c.state(linuxcnc.STATE_ESTOP_RESET); c.wait_complete()
c.state(linuxcnc.STATE_ON); c.wait_complete()
on = wait(lambda: s.task_state == linuxcnc.STATE_ON, 10)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.home(-1)
homed = wait(lambda: all(s.homed[j] for j in range(s.joints)), 240)
c.teleop_enable(1); c.wait_complete()
"""


def run_generated_plant(tmp_path: Path, machine: Path, driver_body: str, *, port: int,
                        timeout: float = 300, copy_macros: bool = True,
                        prelude: str = DRIVER_PRELUDE,
                        hmi_bypass: bool = True) -> tuple[dict, str, Path]:
    """Zwraca (wynik kierowcy, log LinuxCNC, katalog konfiguracji). Pomija test, gdy zajęte.

    ``prelude=""`` oddaje włączenie i bazowanie kierowcy (odbiór G2 robi je przez WebHMI).
    ``hmi_bypass=False`` zostawia łańcuch HMI (D35) aktywny: piny dostarcza kierowca (WebHMI --hal).
    """
    root = rip.rip_root()
    if rip.leftovers():
        pytest.skip(f"działa inny LinuxCNC: {rip.leftovers()}")
    out = tmp_path / "plant_cfg"
    assert main(["build", str(machine), "--target", "plant", "--out", str(out), "--port",
                 str(port), "--write"]) == 0
    ini = next(out.glob("*.ini"))
    text = ini.read_text(encoding="utf-8")
    hal = out / "linumert_plant.hal"
    hal_text = hal.read_text(encoding="utf-8")
    assert "lrt_net" in hal_text
    # Diagnoza: zatrzaski pamiętają, które ogniwo łańcucha E-STOP opadło od ostatniego resetu.
    hal_text = hal_text.replace("loadrt estop_latch names=estop_latch",
                                "loadrt estop_latch names=estop_latch," + ",".join(DIAG_LATCHES))
    hal_text += "".join(f"addf {name} servo-thread\nnet {sig} => {name}.ok-in\n"
                        f"net lrt.estop-reset => {name}.reset\n"
                        for name, sig in DIAG_LATCHES.items())
    # Najdłuższy i najkrótszy okres wątku servo [takty TSC; uspace nie ma last-period-ns]:
    # po wstrzymaniu mastera uspace nadrabia zaległe cykle serią bez przerw.
    hal_text += ("loadrt conv_u32_float names=lrt_diag_period_f\n"
                 "loadrt minmax names=lrt_diag_period\n"
                 "addf lrt_diag_period_f servo-thread\naddf lrt_diag_period servo-thread\n"
                 "net lrt.diag.period motion.servo.last-period => lrt_diag_period_f.in\n"
                 "net lrt.diag.period-f lrt_diag_period_f.out => lrt_diag_period.in\n"
                 "net lrt.estop-reset => lrt_diag_period.reset\n")
    hal.write_text(hal_text, encoding="utf-8")
    # Bez ekranu: zastępczy DISPLAY i jawne obejście grzyba HMI (tylko w teście bez ekranu).
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    text = text.replace("DISPLAY = linumert_headless", "DISPLAY = linumert_bez_ekranu")
    if hmi_bypass:
        text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    # Katalog tymczasowy: ścieżki względne z repozytorium zamieniamy na bezwzględne.
    text = text.replace("../../hal/", f"{ROOT / 'config/hal'}/")
    text = text.replace("../../sim/", f"{ROOT / 'config/sim'}/")
    ini.write_text(text, encoding="utf-8")
    shutil.copy(ROOT / "config/sim/linumert_xyz/linumert.var.default", out / "linumert.var")
    if copy_macros:
        shutil.copytree(ROOT / "config/sim/linumert_xyz/macros", out / "macros", dirs_exist_ok=True)
    script = out / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    driver = tmp_path / "driver.py"
    driver.write_text(prelude + driver_body, encoding="utf-8")
    env = {**os.environ, "PATH": f"{out}{os.pathsep}{os.environ['PATH']}",
           "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(out)}
    with contextlib.ExitStack() as stack:
        stack.enter_context(rip.installed_modules(root, tmp_path,
                                                  ("lrt_net", "lrt_cia402", "lrt_estop2")))
        plant = stack.enter_context(rip.plant_server(machine, port, "--seed", "5"))
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
            # Interpreter testów, nie systemowy python3: kierowca importuje zależności z venv
            # (np. fastapi dla WebHMI); `linuxcnc` daje PYTHONPATH z rip-environment.
            python = shlex.quote(sys.executable)
            timed_out = None
            try:
                run = rip.rip_run(root, f"{python} {shlex.quote(str(driver))}", out,
                                  timeout=timeout, env=env)
            except subprocess.TimeoutExpired as exc:
                tail = (exc.stdout or b"")[-2500:]
                timed_out = tail.decode(errors="replace") if isinstance(tail, bytes) else tail
            # Stan łącza LRT-NET i pętli E-STOP po kierowcy (diagnoza rzadkich czerwonych prób).
            link = rip.rip_run(root, "halcmd show pin lrt-net.0 | grep -vE 'axis|din-|dout-';"
                               " halcmd show pin lrt_diag; halcmd show pin lrt-estop2.0;"
                               " halcmd show pin joint | grep -E 'amp-fault-in|f-errored'",
                               out, env=env).stdout
        finally:
            rip.stop_linuxcnc(cnc, root, out)
            log = cnc.stdout.read() if cnc.stdout else ""
    plant_log = plant.stdout.read() if plant.stdout else ""   # Plant zakończony z ExitStack
    link = f"{link}\n--- Plant ---\n{plant_log}"
    # Log zostaje w katalogu testu (pytest trzyma ostatnie basetemp), też gdy asercja padnie.
    (tmp_path / "linuxcnc.log").write_text(f"{log}\n--- lrt-net.0 ---\n{link}", encoding="utf-8")
    if timed_out is not None:
        pytest.fail(f"kierowca przekroczył czas {timeout}s; ostatnie wyjście:\n{timed_out}\n"
                    f"--- lrt-net.0 ---\n{link}\n--- LinuxCNC ---\n{log[-3000:]}")
    (tmp_path / "driver.out").write_text(run.stdout + run.stderr, encoding="utf-8")
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, f"{run.stdout}{run.stderr}\n--- LinuxCNC ---\n{log[-3000:]}"
    return json.loads(line[7:]), log, out
