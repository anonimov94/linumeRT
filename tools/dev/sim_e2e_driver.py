#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Sterownik testu end-to-end symulacji HMI (wywołuje go tools/dev/sim-e2e.sh w kontenerze).

Model-Author: Claude · 2026-10-19.

Reset E-STOP (konfiguracja testowa z HMI_ESTOP_BYPASS = 1), maszyna WŁ., bazowanie na krańcówkach,
program demonstracyjny (wymiany narzędzi potwierdzane pinem okna ręcznej wymiany), potem program
kolizji: oczekiwane zdarzenie K-302 i E-STOP. Zrzuty ekranu i podsumowanie w katalogu wyników.
"""

import json
import os
import subprocess
import sys
import time

import linuxcnc

OUT, NC = sys.argv[1], sys.argv[2]
LOG = os.path.join(OUT, "events.jsonl")
s = c = None  # linuxcnc.stat() przed startem LinuxCNC jest bezużyteczny (SystemError w poll)
result = {"steps": []}


def step(name, ok=True, **extra):
    result["steps"].append({"step": name, "ok": ok, **extra})
    print(("OK   " if ok else "BŁĄD ") + name, extra or "", flush=True)


def shot(name):
    subprocess.run(f"xwd -root -silent | convert xwd:- {OUT}/{name}.png", shell=True, check=False)


def poll():
    try:
        s.poll()
        return True
    except linuxcnc.error:
        return False


def _getp(pin):
    r = subprocess.run(["halcmd", "getp", pin], capture_output=True, text=True)
    return r.stdout.strip()


def toolchange():
    """Okno ręcznej wymiany narzędzia: potwierdzenie jak przycisk operatora."""
    if _getp("iocontrol.0.tool-change") == "TRUE" and \
            _getp("iocontrol.0.tool-changed") == "FALSE":
        subprocess.run(["halcmd", "setp", "hal_manualtoolchange.change_button", "1"], check=False)
        time.sleep(0.3)
        subprocess.run(["halcmd", "setp", "hal_manualtoolchange.change_button", "0"], check=False)


def wait(cond, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        if poll() and cond():
            return True
        toolchange()
        time.sleep(0.2)
    step(what, False, reason="limit czasu")
    return False


def events():
    try:
        with open(LOG, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    except OSError:
        return []


def run_program(name, timeout):
    c.mode(linuxcnc.MODE_AUTO)
    c.wait_complete()
    c.program_open(os.path.join(NC, name))
    time.sleep(3)
    c.auto(linuxcnc.AUTO_RUN, 0)
    wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 10, f"{name}: start")
    t0 = time.time()
    n = 0
    while time.time() - t0 < timeout:
        poll()
        toolchange()
        if s.interp_state == linuxcnc.INTERP_IDLE or s.task_state != linuxcnc.STATE_ON:
            break
        if time.time() - t0 > 15 * (n + 1):
            n += 1
            shot(f"{name[:-4]}_{n:02d}")
        time.sleep(0.2)
    poll()
    return time.time() - t0


def main():
    global s, c
    end = time.time() + 120
    while subprocess.run(["halcmd", "getp", "iocontrol.0.user-enable-out"],
                         capture_output=True).returncode != 0:
        if time.time() > end:
            step("LinuxCNC działa", False)
            return 1
        time.sleep(1)
    time.sleep(3)
    s, c = linuxcnc.stat(), linuxcnc.command()
    if not wait(lambda: True, 30, "LinuxCNC działa"):
        return 1
    time.sleep(20)  # ekran i proces symulacji
    shot("00_start")
    c.state(linuxcnc.STATE_ESTOP_RESET)
    wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 10, "reset E-STOP")
    c.state(linuxcnc.STATE_ON)
    if not wait(lambda: s.task_state == linuxcnc.STATE_ON, 10, "maszyna WŁ."):
        return 1
    step("reset E-STOP i maszyna WŁ.")
    c.mode(linuxcnc.MODE_MANUAL)
    c.wait_complete()
    c.home(-1)
    if wait(lambda: all(j["homed"] for j in s.joint[:3]), 180, "bazowanie"):
        step("bazowanie na krańcówkach", pos=[round(v, 2) for v in s.actual_position[:3]])
    shot("01_po_bazowaniu")
    ev0 = events()
    step("proces symulacji", any(e.get("ev") == "ready" for e in ev0),
         stock=[e.get("line") for e in ev0 if e.get("ev") == "stock"][-1:])
    dt = run_program("linumert_demo.ngc", 900)
    stops = [e for e in events() if e.get("ev") == "event" and e.get("stop")]
    step("program demo bez kolizji", s.task_state == linuxcnc.STATE_ON and not stops,
         czas_s=round(dt), zdarzenia=[e["code"] for e in stops])
    vols = [e.get("volume") for e in events() if e.get("ev") == "map"]
    step("materiał usunięty", bool(vols), objetosc_cm3=round((vols or [0])[-1] / 1000, 1))
    shot("02_po_demo")
    if s.task_state != linuxcnc.STATE_ON:
        c.state(linuxcnc.STATE_ESTOP_RESET)
        wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 10, "reset po demo")
        c.state(linuxcnc.STATE_ON)
        wait(lambda: s.task_state == linuxcnc.STATE_ON, 10, "WŁ. po demo")
    c.mode(linuxcnc.MODE_MANUAL)
    c.wait_complete()
    if not all(j["homed"] for j in s.joint[:3]):
        c.home(-1)
        wait(lambda: all(j["homed"] for j in s.joint[:3]), 180, "bazowanie po demo")
    run_program("linumert_kolizja.ngc", 120)
    time.sleep(2)
    poll()
    codes = [e["code"] for e in events() if e.get("ev") == "event"]
    step("kolizja G0 → K-302 diagnostycznie, bez E-STOP",
         "K-302" in codes and s.task_state == linuxcnc.STATE_ON, zdarzenia=codes,
         stan=s.task_state)  # symulacja nie steruje stanem LinuxCNC
    shot("03_kolizja")
    with open(os.path.join(OUT, "wynik.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    subprocess.run(["pkill", "-f", "linuxcnc"], check=False)
    return 0 if all(x["ok"] for x in result["steps"]) else 1


if __name__ == "__main__":
    sys.exit(main())
