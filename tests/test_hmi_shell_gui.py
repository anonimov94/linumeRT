"""Nakładka linumeRT w działającym GUI: LinuxCNC RIP + ekran pod Xvfb (marker `linuxcnc`).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · HMI-PoC.

Samotest (`screens/linumert/linumert_shell_selftest.py`) klika przyciski nakładki w procesie GUI:
E-STOP → Maszyna → Bazuj → MDI → program w AUTO → Wstrzymaj/Wznów → Stop → JOG → obszary szyny
→ Diagnostyka.
Zrzuty kroków: katalog z `LINUMERT_HMI_SHOTS` (domyślnie tmp_path).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from rip_support import cleanup_linuxcnc, stop_linuxcnc

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "sim" / "linumert_xyz"
NC = ROOT / "config" / "sim" / "nc_files"


def test_shell_selftest_in_gui(tmp_path) -> None:
    if shutil.which("linuxcnc") is None:
        pytest.skip("brak LinuxCNC")
    if not os.environ.get("DISPLAY"):
        pytest.skip("brak DISPLAY (xvfb-run)")
    cleanup_linuxcnc(cwd=tmp_path)
    work = tmp_path / "linumert_xyz"
    shutil.copytree(CFG, work, symlinks=True)
    link = work / "qtvcp" / "screens" / "linumert"
    link.unlink()
    link.symlink_to(ROOT / "screens" / "linumert")  # tokeny i ikony z repozytorium
    ini = work / "linumert_xyz.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace(
        "PROGRAM_PREFIX = ../nc_files", f"PROGRAM_PREFIX = {NC}"), encoding="utf-8")
    out = Path(os.environ.get("LINUMERT_HMI_SHOTS", tmp_path / "hmi"))
    shutil.rmtree(out, ignore_errors=True)
    env = {**os.environ, "LINUMERT_SHELL_SELFTEST": str(out)}
    proc = subprocess.Popen(["linuxcnc", str(ini)], cwd=work, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
    result = out / "wynik.json"
    try:
        deadline = time.monotonic() + 300
        while not result.exists() and time.monotonic() < deadline:
            assert proc.poll() is None, proc.stdout.read()
            time.sleep(1)
        assert result.exists(), "samotest nie zakończył się w 300 s"
    finally:
        stop_linuxcnc(proc, cwd=work)
    data = json.loads(result.read_text(encoding="utf-8"))
    steps = {s["step"]: s for s in data["steps"]}
    assert data["errors"] == [], data["errors"]
    assert len(steps) == 19 and all(s["ok"] for s in steps.values())
    # QtDragon zgłaszał „Hard limits tripped” przy starcie i przy bazowaniu na krańcówce (handler)
    assert not any("Hard limits" in s["alarm"] or "krańcówka" in s["alarm"] for s in steps.values())
    assert steps["01_start"]["estop"] and not steps["01_start"]["start_enabled"]
    assert steps["03_maszyna_wl"]["machine_on"]
    assert steps["04_bazowanie"]["homed"] == ["X", "Y", "Z"]
    mdi = steps["06_mdi_g0"]
    assert (mdi["x"], mdi["y"], mdi["z"]) == (100.0, 80.0, -10.0)
    assert steps["09_cykl_start"]["interp"] == "run" and steps["09_cykl_start"]["line"] >= 4
    assert steps["10_wstrzymany"]["interp"] == "paused"
    assert steps["12_stop"]["interp"] == "idle"
    assert steps["14_jog_x_plus"]["x"] > steps["13_tryb_jog"]["x"] + 1.0
    assert steps["15_obszar_program"]["area"] == 1 and steps["18_maszyna"]["area"] == 0
    assert steps["19_diagnostyka"]["diag_joints"] == 3  # symulator: bez napędów Plant
    assert steps["19_diagnostyka"]["diag_drives"] == 0
    assert all((out / f"{name}.png").stat().st_size > 20000 for name in steps)
