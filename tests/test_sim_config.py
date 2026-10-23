"""Konfiguracja symulatora linumert_xyz: INI, kontrakt sygnałów D05, programy testowe (sesja 004).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 004.
"""

from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from rip_support import cleanup_linuxcnc, stop_linuxcnc

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "config" / "sim" / "linumert_xyz"
INI = CFG / "linumert_xyz.ini"
NC = REPO / "config" / "sim" / "nc_files"

CONTRACT = [
    *(f"linumert.j{n}.{s}" for n in range(3)
      for s in ("pos-cmd", "pos-fb", "enable", "fault", "home-sw")),
    "linumert.spindle.on", "linumert.spindle.cw", "linumert.spindle.ccw",
    "linumert.spindle.speed-cmd", "linumert.spindle.speed-fb", "linumert.spindle.revs",
    "linumert.spindle.index", "linumert.spindle.at-speed", "linumert.spindle.inhibit",
    "linumert.io.estop-ok", "linumert.io.tool-prepare", "linumert.io.tool-change",
    "linumert.io.tool-changed", "linumert.io.tool-number",
    "linumert.io.coolant-flood", "linumert.io.coolant-mist",
]


def _ini() -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None, inline_comment_prefixes=None)
    cp.optionxform = str
    cp.read(INI, encoding="utf-8")
    return cp


def _hal_text() -> str:
    # Kilka wpisów HALFILE (D35: plik grzyba HMI); configparser zostawiłby tylko ostatni.
    files = re.findall(r"^(?:POSTGUI_)?HALFILE = (.+)$", INI.read_text(encoding="utf-8"), re.M)
    return "\n".join((CFG / f).read_text(encoding="utf-8") for f in files)


def test_ini_ranges_and_display():
    cp = _ini()
    assert cp["DISPLAY"]["DISPLAY"] == "qtvcp linumert"
    assert cp["KINS"]["KINEMATICS"].startswith("trivkins")
    assert int(cp["KINS"]["JOINTS"]) == 3
    ranges = {"X": (0.0, 600.0), "Y": (0.0, 400.0), "Z": (-120.0, 0.0)}
    for axis, (lo, hi) in ranges.items():
        sec = cp[f"AXIS_{axis}"]
        assert (float(sec["MIN_LIMIT"]), float(sec["MAX_LIMIT"])) == (lo, hi)
    for f in ("HALFILE", "POSTGUI_HALFILE"):
        assert (CFG / cp["HAL"][f]).is_file()
    assert (CFG / cp["EMCIO"]["TOOL_TABLE"]).is_file()


def test_homing_latch_on_release():
    """Bazowanie: wolny zjazd z krańcówki, baza na zwolnieniu styku (homing.latch: release)."""
    cp = _ini()
    for j in range(3):
        sec = cp[f"JOINT_{j}"]
        search, latch = float(sec["HOME_SEARCH_VEL"]), float(sec["HOME_LATCH_VEL"])
        assert search * latch < 0  # przeciwne znaki: zjazd z czujnika
        assert abs(latch) <= 0.1 * abs(search)


def _documented(signal: str, doc: str) -> bool:
    """Sygnał w tabeli wprost, jako jN albo w skrócie `prefiks` / `.przyrostek`."""
    generic = re.sub(r"\.j\d\.", ".jN.", signal)
    family, last = signal.rsplit(".", 1)
    return generic in doc or (f"`{family}." in doc and last.split("-")[-1] in doc)


def test_contract_signals_present_and_documented():
    hal = _hal_text()
    nets = set(re.findall(r"^net\s+(\S+)", hal, flags=re.M))
    doc = (REPO / "docs" / "HAL_KONTRAKT.md").read_text(encoding="utf-8")
    missing = [s for s in CONTRACT if s not in nets]
    assert not missing, f"brak w HAL: {missing}"
    undocumented = [s for s in CONTRACT if not _documented(s, doc)]
    assert not undocumented, f"brak w HAL_KONTRAKT.md: {undocumented}"
    assert all(n.startswith("linumert.") for n in nets), "sygnały spoza kontraktu"


def test_tool_table_and_programs():
    tools = [line for line in (CFG / "tool.tbl").read_text().splitlines() if line.strip()]
    tool_ids = [t.split()[0] for t in tools]
    assert tool_ids[:11] == [f"T{n}" for n in range(1, 12)]
    assert len(tool_ids) == len(set(tool_ids))
    programs = [NC / f"linumert_{name}.ngc"
                for name in ("demo", "kolizja", "kwadrat", "rowek", "wiercenie")]
    assert all(path.is_file() for path in programs)
    for p in programs:
        text = p.read_text(encoding="utf-8")
        assert "M98" not in text and text.rstrip().endswith("M2")


@pytest.mark.linuxcnc
def test_headless_run_20s(tmp_path):
    """LinuxCNC z konfiguracją bez ekranu (zastępczy DISPLAY): 20 s pracy, sygnały kontraktu."""
    if shutil.which("linuxcnc") is None:
        pytest.skip("brak LinuxCNC")
    cleanup_linuxcnc(cwd=tmp_path)  # resztki poprzedniego testu blokują start
    work = tmp_path / "linumert_xyz"
    shutil.copytree(CFG, work)
    ini = work / "linumert_xyz.ini"
    text = ini.read_text(encoding="utf-8")
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    # Bez ekranu nie ma grzyba HMI ani sygnału życia (D35): jawne obejście tylko tutaj;
    # plik HAL grzyba z repozytorium (ścieżka względna nie działa w kopii konfiguracji).
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    text = text.replace("HALFILE = ../../hal/", f"HALFILE = {CFG.parent.parent / 'hal'}/")
    text = re.sub(r"^POSTGUI_HALFILE.*$", "", text, flags=re.M)
    text = text.replace("PROGRAM_PREFIX = ../nc_files", f"PROGRAM_PREFIX = {NC}")
    ini.write_text(text, encoding="utf-8")
    (work / "linumert_bez_ekranu").write_text("#!/bin/sh\nexec sleep 3600\n")
    (work / "linumert_bez_ekranu").chmod(0o755)
    env = {**os.environ, "PATH": f"{work}:{os.environ.get('PATH', '/usr/bin:/bin')}"}
    proc = subprocess.Popen(["linuxcnc", str(ini)], cwd=work, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    try:
        time.sleep(20)
        assert proc.poll() is None, proc.stdout.read()
        sig = subprocess.run(["halcmd", "show", "sig", "linumert."], env=env,
                             capture_output=True, text=True, check=True).stdout
        for s in CONTRACT:
            if s.startswith(("linumert.io.tool-change", "linumert.io.tool-number",
                             "linumert.spindle.inhibit")):
                continue  # postgui (ekran)
            assert s in sig
    finally:
        stop_linuxcnc(proc, cwd=work)
