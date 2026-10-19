"""Grzyb E-STOP w HMI jako dodatkowy element łańcucha E-STOP w HAL (D35). Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later

Statycznie: obie konfiguracje ładują config/hal/linumert_hmi_estop.hal, obejście jest wyłączone,
postgui łączy piny ekranu, łańcuch Plant ma wejście HMI szeregowo. W halrun (marker `linuxcnc`,
bez GUI): grzyb wciśnięty otwiera łańcuch, brak sygnału życia > limit otwiera go na stałe do
ponownego uzbrojenia, zatrzask E-STOP nie daje się zresetować przy otwartym łańcuchu.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import configparser
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HMI_HAL = ROOT / "config" / "hal" / "linumert_hmi_estop.hal"
INIS = [ROOT / "config/sim/linumert_xyz/linumert_xyz.ini",
        ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini",
        ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz_vfd.ini"]


def _ini(path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser(strict=False, interpolation=None, inline_comment_prefixes=None)
    cfg.optionxform = str
    cfg.read(path, encoding="utf-8")
    return cfg


@pytest.mark.parametrize("ini", INIS, ids=lambda p: p.name)
def test_configs_load_hmi_estop(ini: Path) -> None:
    text = ini.read_text(encoding="utf-8")
    halfiles = re.findall(r"^HALFILE = (.+)$", text, re.M)
    assert "../../hal/linumert_hmi_estop.hal" in halfiles
    assert (ini.parent / "../../hal/linumert_hmi_estop.hal").resolve() == HMI_HAL
    lin = _ini(ini)["LINUMERT"]
    assert lin["HMI_ESTOP_BYPASS"] == "0"  # obejście tylko w testach bez ekranu
    assert 0.5 <= float(lin["HMI_HEARTBEAT_TIMEOUT"]) <= 5.0
    postgui = (ini.parent / re.search(r"^POSTGUI_HALFILE = (.+)$", text, re.M).group(1)).read_text()
    for pin, target in (("linumert.hmi-estop-ok", "lrt_hmi_ok.in-00"),
                        ("linumert.hmi-heartbeat", "watchdog.input-0"),
                        ("linumert.hmi-wd-enable", "watchdog.enable-in")):
        assert re.search(rf"^net \S+\s+{re.escape(pin)}\s+=> {re.escape(target)}$", postgui, re.M)


def test_chains_take_hmi_in_series() -> None:
    sim = (ROOT / "config/sim/linumert_xyz/linumert_sim.hal").read_text(encoding="utf-8")
    assert "net linumert.hmi.estop-ok      => estop_latch.ok-in" in sim
    assert "estop_latch.ok-out => iocontrol.0.emc-enable-in" in sim
    assert "iocontrol.0.user-enable-out => iocontrol.0.emc-enable-in" not in sim  # bez obejścia
    plant = (ROOT / "config/plant/linumert_plant_xyz/linumert_plant.hal").read_text(
        encoding="utf-8")
    assert "loadrt logic names=estop_chain personality=0x103" in plant  # AND 3 wejść
    for line in ("lrt-net.0.din-00 => estop_chain.in-00",
                 "lrt-net.0.connected => estop_chain.in-01",
                 "net linumert.hmi.estop-ok    => estop_chain.in-02",
                 "estop_chain.and => estop_latch.ok-in"):
        assert line in plant, line
    hmi = HMI_HAL.read_text(encoding="utf-8")
    assert "personality=0x102" in hmi  # grzyb ∧ watchdog
    assert "net linumert.hmi.estop-ok       lrt_hmi_bypass.out" in hmi


def test_screen_creates_pins_and_hides_qtdragon_reset() -> None:
    handler = (ROOT / "screens/linumert/linumert_handler.py").read_text(encoding="utf-8")
    for name in ("hmi-estop-ok", "hmi-heartbeat", "hmi-wd-enable"):
        assert f'"{name}"' in handler
    assert "self.w.action_estop.hide()" in handler
    assert "def on_keycall_ESTOP" in handler


# ---- halrun: logika łańcucha bez ekranu ----------------------------------------------------------

def _halrun_script(bypass: int = 0, timeout: float = 0.3) -> str:
    hmi = HMI_HAL.read_text(encoding="utf-8")
    hmi = hmi.replace("[LINUMERT]HMI_HEARTBEAT_TIMEOUT", str(timeout))
    hmi = hmi.replace("[LINUMERT]HMI_ESTOP_BYPASS", str(bypass))
    return ("loadrt threads name1=servo-thread period1=1000000\n" + hmi + """
loadrt estop_latch names=estop_latch
addf estop_latch servo-thread
net linumert.hmi.estop-ok => estop_latch.ok-in
net reset estop_latch.reset
net button lrt_hmi_ok.in-00
net beat watchdog.input-0
net wd watchdog.enable-in
start
""")


@pytest.mark.linuxcnc
def test_hmi_chain_in_halrun(tmp_path: Path) -> None:
    if shutil.which("halrun") is None:
        pytest.skip("brak halrun (LinuxCNC)")
    hal = tmp_path / "hmi.hal"
    hal.write_text(_halrun_script(), encoding="utf-8")
    subprocess.run(["halrun", "-U"], capture_output=True)
    proc = subprocess.Popen(["halrun", "-I", "-f", str(hal)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def cmd(line: str) -> None:
        proc.stdin.write(line + "\n")
        proc.stdin.flush()

    def get(name: str) -> bool:
        out = subprocess.run(["halcmd", "getp", name], capture_output=True, text=True).stdout
        if not out.strip():
            out = subprocess.run(["halcmd", "gets", name], capture_output=True, text=True).stdout
        return out.strip().upper() in ("TRUE", "1")

    def beat(seconds: float) -> None:
        end, value = time.monotonic() + seconds, False
        while time.monotonic() < end:
            value = not value
            cmd(f"sets beat {int(value)}")
            time.sleep(0.05)

    def reset() -> None:
        cmd("sets reset 1")
        time.sleep(0.05)
        cmd("sets reset 0")
        time.sleep(0.05)

    try:
        time.sleep(1.0)
        assert not get("estop_latch.ok-out")  # bez ekranu (piny 0): łańcuch otwarty
        cmd("sets button 1")
        beat(0.2)
        cmd("sets wd 1")  # zbocze: uzbrojenie watchdoga
        beat(0.3)
        assert get("watchdog.ok-out") and get("lrt_hmi_bypass.out")
        reset()
        beat(0.2)
        assert get("estop_latch.ok-out")  # grzyb zwolniony, HMI żyje → zezwolenie
        cmd("sets button 0")  # grzyb wciśnięty
        beat(0.1)
        assert not get("estop_latch.ok-out")
        reset()
        beat(0.1)
        assert not get("estop_latch.ok-out")  # reset przy wciśniętym grzybie nieskuteczny
        cmd("sets button 1")
        beat(0.1)
        reset()
        beat(0.1)
        assert get("estop_latch.ok-out")
        time.sleep(0.6)  # brak sygnału życia > 0,3 s
        assert not get("watchdog.ok-out") and not get("estop_latch.ok-out")
        beat(0.3)
        reset()
        assert not get("watchdog.ok-out")  # wznowiony sygnał życia nie wystarcza: zatrzask
        cmd("sets wd 0")
        beat(0.1)
        cmd("sets wd 1")  # ponowne uzbrojenie (potwierdzenie grzybem w HMI)
        beat(0.2)
        reset()
        beat(0.1)
        assert get("watchdog.ok-out") and get("estop_latch.ok-out")
    finally:
        cmd("exit")
        proc.wait(timeout=10)
        subprocess.run(["halrun", "-U"], capture_output=True)
