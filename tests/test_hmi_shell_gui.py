"""Nakładka linumeRT w działającym GUI: LinuxCNC RIP + ekran pod Xvfb (marker `linuxcnc`).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · HMI-PoC.

Samotest (`screens/linumert/linumert_shell_selftest.py`) klika przyciski nakładki w procesie GUI:
Start: E-STOP → Maszyna → Bazuj (lista gotowości) → MDI → program w AUTO → Wstrzymaj/Wznów
→ Stop → JOG → obszary szyny
→ Diagnostyka → Produkcja (korekcja posuwu, start od linii).
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


def _run_selftest(tmp_path: Path, out: Path, extra_env: dict[str, str] | None = None) -> dict:
    """LinuxCNC (symulator) z ekranem i samotestem; zwraca wynik.json."""
    if shutil.which("linuxcnc") is None:
        pytest.skip("brak LinuxCNC")
    if not os.environ.get("DISPLAY"):
        pytest.skip("brak DISPLAY (xvfb-run)")
    cleanup_linuxcnc(cwd=tmp_path)
    work = tmp_path / "linumert_xyz"
    shutil.copytree(CFG, work, symlinks=True)
    # Samotest zakłada G54=0; nie dziedziczy przesunięć zapisanych po lokalnym demo.
    # Usuwamy stan wyłącznie z kopii testowej, nigdy z konfiguracji operatora.
    (work / "linumert.var").unlink(missing_ok=True)
    (work / "linumert.var.bak").unlink(missing_ok=True)
    link = work / "qtvcp" / "screens" / "linumert"
    link.unlink()
    link.symlink_to(ROOT / "screens" / "linumert")  # tokeny i ikony z repozytorium
    ini = work / "linumert_xyz.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace(
        "PROGRAM_PREFIX = ../nc_files", f"PROGRAM_PREFIX = {NC}").replace(
        "HALFILE = ../../hal/", f"HALFILE = {ROOT / 'config' / 'hal'}/"), encoding="utf-8")
    shutil.rmtree(out, ignore_errors=True)
    env = {**os.environ, "LINUMERT_SHELL_SELFTEST": str(out), **(extra_env or {})}
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
    return json.loads(result.read_text(encoding="utf-8"))


def test_classic_mode_rearms_watchdog(tmp_path) -> None:
    # Przegląd Codexa P2: --classic (LINUMERT_SHELL=0) odzyskuje zezwolenie po braku sygnału
    # życia przyciskiem QtDragon, bez BYPASS i bez restartu; reset innym procesem nieskuteczny.
    data = _run_selftest(tmp_path, tmp_path / "classic", {"LINUMERT_SHELL": "0"})
    steps = {s["step"]: s for s in data["steps"]}
    assert data["errors"] == [], data["errors"]
    assert not steps["c02_reset_przyciskiem"]["estop"]
    lost = steps["c03_brak_sygnalu_zycia"]
    assert lost["estop"] and not lost["hmi_alive"]
    assert steps["c04_reset_komenda"]["estop"] and not steps["c04_reset_komenda"]["hmi_chain"]
    back = steps["c05_reset_przyciskiem"]
    assert not back["estop"] and back["hmi_alive"] and back["hmi_acked"]


def test_shell_selftest_in_gui(tmp_path) -> None:
    out = Path(os.environ.get("LINUMERT_HMI_SHOTS", tmp_path / "hmi"))
    data = _run_selftest(tmp_path, out)
    steps = {s["step"]: s for s in data["steps"]}
    assert data["errors"] == [], data["errors"]
    assert len(steps) == 45 and all(s["ok"] for s in steps.values())
    # A fallback QtDragon page must not certify the custom operator screens.
    assert data["pages"] == {"tools": True, "cycles": True}, data["pages"]
    assert steps["04d_wpis_liczb"]["typed_jog_speed"] == 12.3456
    assert steps["04d_wpis_liczb"]["typed_jog_step"] == "2.5"
    assert steps["04e_wpis_pozycji"]["typed_position_x"] == -12.3456
    assert steps["04b_widok_bazowania"]["page"] == "homing"
    assert steps["01_start"]["page"] == "start"  # po uruchomieniu widok Start
    assert steps["04b_start_gotowosc"]["ready"] == "wymaga działań"  # brak programu
    assert steps["04c_maszyna"]["page"] == "machine"
    # QtDragon zgłaszał „Hard limits tripped” przy starcie i przy bazowaniu na krańcówce (handler);
    # E-STOP w trakcie scenariusza byłby błędem (przyczynę podaje nakładka)
    bad = ("Hard limits", "krańcówka", "E-STOP")
    assert not any(word in s["alarm"] for name, s in steps.items() for word in bad
                   if name < "26")  # E-STOP przed częścią D35 byłby błędem
    assert steps["01_start"]["estop"] and not steps["01_start"]["start_enabled"]
    assert steps["03_maszyna_wl"]["machine_on"]
    assert steps["04_bazowanie"]["homed"] == ["X", "Y", "Z"]
    mdi = steps["06_mdi_g0"]
    assert (mdi["x"], mdi["y"], mdi["z"]) == (100.0, 80.0, -10.0)
    assert steps["09_cykl_start"]["interp"] == "run" and steps["09_cykl_start"]["line"] >= 4
    assert steps["10_wstrzymany"]["interp"] == "paused"
    assert steps["12_stop"]["interp"] == "idle"
    assert steps["14_jog_x_plus"]["x"] > steps["13_tryb_jog"]["x"] + 1.0
    assert steps["14a_symulacja"]["page"] == "sim"
    assert steps["14b_mdi_symulacji"]["x"] == 110.0
    assert steps["14c_wrzeciono_m3"]["spindle_dir"] == 1
    assert steps["14d_wrzeciono_m5"]["spindle_dir"] == 0
    assert steps["14e_wymiana_m6"]["tool"] == 1
    assert steps["15_obszar_program"]["page"] == "program"
    assert steps["18_maszyna"]["page"] == "machine"
    assert steps["19_diagnostyka"]["diag_joints"] == 3  # symulator: bez napędów Plant
    assert steps["19_diagnostyka"]["diag_drives"] == 0
    assert steps["21_korekcja_posuwu_80"]["feed_override"] == 80
    assert steps["23_start_od_linii"]["interp"] == "run" and steps["23_start_od_linii"]["line"] >= 6
    assert steps["24_program_koniec"]["interp"] == "idle"
    assert steps["24_program_koniec"]["run_time"] != "00:00"
    assert steps["25_korekcja_100"]["feed_override"] == 100
    # D35: grzyb HMI w łańcuchu HAL, reset tylko grzybem, sygnał życia (watchdog)
    assert steps["01_start"]["hmi_chain"] is not None  # piny i komponenty HAL istnieją
    assert steps["25_korekcja_100"]["hmi_chain"] and steps["25_korekcja_100"]["hmi_alive"]
    pressed = steps["26_grzyb_wcisniety"]
    assert pressed["estop"] and pressed["hmi_pressed"] and not pressed["hmi_chain"]
    assert "grzyb E-STOP w HMI" in pressed["alarm"]
    assert steps["27_reset_obejsciem"]["estop"]  # inna droga resetu nie działa przy wciśniętym
    assert not steps["28_grzyb_zwolniony"]["estop"] and steps["28_grzyb_zwolniony"]["hmi_chain"]
    lost = steps["29_brak_sygnalu_zycia"]
    assert lost["estop"] and not lost["hmi_alive"] and "sygnału życia" in lost["alarm"]
    assert not steps["30_potwierdzenie"]["estop"] and steps["30_potwierdzenie"]["hmi_alive"]
    assert steps["31_maszyna_wl"]["machine_on"]
    # Przegląd Codexa P1: po E-STOP z innej przyczyny reset z pominięciem grzyba nieskuteczny
    assert steps["32_estop_programowy"]["estop"] and not steps["32_estop_programowy"]["hmi_pressed"]
    assert steps["33_reset_komenda"]["estop"] and not steps["33_reset_komenda"]["hmi_chain"]
    assert not steps["34_potwierdzenie_grzybem"]["estop"]
    assert all((out / f"{name}.png").stat().st_size > 20000 for name in steps)
