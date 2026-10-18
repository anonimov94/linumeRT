"""Czytnik rdzenia `LinuxCNCReader` na prawdziwym LinuxCNC 2.9 RIP (zaległość sesji 006, sesja 008).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 008.
Konfiguracja config/sim/linumert_xyz bez ekranu (zastępczy DISPLAY). Sprawdza mapowanie stanu,
trybu, bazowania, pozycji, limitów programowych z INI, kodów G/M (`gcodes[0]`/`mcodes[0]`),
układu detalu i wrzeciona `spindle[0]`. Marker `linuxcnc`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import pytest
from rip_support import rip_root, rip_run, start_linuxcnc, stop_linuxcnc

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "sim" / "linumert_xyz"

PROBE = (f"'{sys.executable}' -c \"import linuxcnc; s = linuxcnc.stat(); s.poll(); "
         "assert s.joints == 3\"")

DRIVER = r'''
import json, time
import linuxcnc
from linumert.cnc.linuxcnc_reader import LinuxCNCReader

c, s = linuxcnc.command(), linuxcnc.stat()
reader = LinuxCNCReader()
def wait(cond, timeout):
    t = time.time()
    while time.time() - t < timeout:
        s.poll()
        if cond():
            return True
        time.sleep(0.05)
    return False
def snap():
    x = reader.read()
    return {"task": x.task_state.value, "mode": x.mode.value, "interp": x.interp_state.value,
            "axes": [[a.name, round(a.position, 4), round(a.commanded, 4), a.homed,
                      a.soft_min, a.soft_max, a.limit_hit] for a in x.axes],
            "g": list(x.active_gcodes), "m": list(x.active_mcodes),
            "wo": x.work_offset_name, "wo_xyz": x.work_offset,
            "spindle": [x.spindle_speed, x.spindle_direction], "tool": x.tool_number,
            "feed": x.feed_override, "errors": list(x.errors)}
out = {"start": snap()}
c.state(linuxcnc.STATE_ESTOP_RESET); wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 5)
c.state(linuxcnc.STATE_ON); wait(lambda: s.task_state == linuxcnc.STATE_ON, 5)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.home(-1)
out["homed"] = wait(lambda: all(s.homed[:3]), 120)
c.mode(linuxcnc.MODE_MDI); c.wait_complete()
c.mdi("G10 L2 P2 X100 Y50 Z-10"); c.wait_complete(10)
c.mdi("G55 G90 G1 X10 Y20 Z-5 F2000 M3 S1200"); c.wait_complete(60)
wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 60)
time.sleep(0.3)
out["after"] = snap()
c.mdi("M5"); c.wait_complete(10)
c.state(linuxcnc.STATE_OFF); wait(lambda: s.task_state == linuxcnc.STATE_OFF, 5)
print("RESULT " + json.dumps(out))
'''


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    root = rip_root()
    work = tmp_path_factory.mktemp("reader") / "linumert_xyz"
    shutil.copytree(CFG, work)
    ini = work / "linumert_xyz.ini"
    text = ini.read_text(encoding="utf-8")
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    text = re.sub(r"^POSTGUI_HALFILE.*$", "", text, flags=re.M)
    text = text.replace("PROGRAM_PREFIX = ../nc_files",
                        f"PROGRAM_PREFIX = {ROOT / 'config/sim/nc_files'}")
    ini.write_text(text, encoding="utf-8")
    script = work / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    (work / "driver.py").write_text(DRIVER, encoding="utf-8")
    env = {**os.environ, "PATH": f"{work}:{os.environ.get('PATH', '')}",
           "PYTHONPATH": os.pathsep.join([str(ROOT / "core"), os.environ.get("PYTHONPATH", "")])}
    cnc = start_linuxcnc(root, ini, env)
    try:
        # Gotowość sprawdzana w osobnym procesie: nieudany pierwszy poll() zostawia w procesie
        # błąd mmap tabeli narzędzi do jego końca (jak w tests/test_linuxcnc.py).
        deadline = time.monotonic() + 60
        while rip_run(root, PROBE, work, timeout=10, env=env).returncode != 0:
            assert cnc.poll() is None, cnc.stdout.read()
            assert time.monotonic() < deadline, "LinuxCNC nie wystartował"
            time.sleep(0.5)
        run = rip_run(root, f"'{sys.executable}' driver.py", work, timeout=240, env=env)
    finally:
        stop_linuxcnc(cnc, root, work)
    line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
    assert line, run.stdout + run.stderr
    return json.loads(line[len("RESULT "):])


def test_reader_initial_state(result):
    start = result["start"]
    assert start["task"] == "estop" and start["interp"] == "idle"
    assert [a[0] for a in start["axes"]] == ["X", "Y", "Z"]
    assert not any(a[3] for a in start["axes"])  # nic nie jest zbazowane
    limits = {a[0]: (a[4], a[5]) for a in start["axes"]}
    assert limits == {"X": (0.0, 600.0), "Y": (0.0, 400.0), "Z": (-120.0, 0.0)}  # [AXIS_*] z INI
    assert start["wo"] == "G54" and start["tool"] == 0
    assert start["feed"] == pytest.approx(1.0)


def test_reader_after_mdi(result):
    assert result["homed"], result
    after = result["after"]
    assert after["task"] == "on" and after["mode"] == "mdi" and after["interp"] == "idle"
    pos = {a[0]: a[1] for a in after["axes"]}
    assert pos == pytest.approx({"X": 110.0, "Y": 70.0, "Z": -15.0}, abs=0.001)  # układ maszyny
    assert all(a[3] for a in after["axes"]) and not any(a[6] for a in after["axes"])
    assert after["wo"] == "G55"
    assert after["wo_xyz"] == pytest.approx({"X": 100.0, "Y": 50.0, "Z": -10.0})
    assert {"G1", "G55", "G90"} <= set(after["g"]), after["g"]  # gcodes[0] pominięte
    assert "M3" in after["m"], after["m"]
    assert after["spindle"] == [pytest.approx(1200.0), 1]
    assert after["errors"] == []
