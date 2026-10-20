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
                        ("linumert.hmi-wd-enable", "watchdog.enable-in"),
                        ("linumert.hmi-ack", "lrt_ack_edge.in")):
        assert re.search(rf"^net \S+\s+{re.escape(pin)}\s+=> {re.escape(target)}$", postgui, re.M)


def test_chains_take_hmi_in_series() -> None:
    sim = (ROOT / "config/sim/linumert_xyz/linumert_sim.hal").read_text(encoding="utf-8")
    assert "net linumert.hmi.estop-ok      => estop_latch.ok-in" in sim
    assert "estop_latch.ok-out => iocontrol.0.emc-enable-in" in sim
    assert "iocontrol.0.user-enable-out => iocontrol.0.emc-enable-in" not in sim  # bez obejścia
    plant = (ROOT / "config/plant/linumert_plant_xyz/linumert_plant.hal").read_text(
        encoding="utf-8")
    assert "loadrt and2 names=estop_chain,estop_chain_hmi" in plant  # (din ∧ łącze) ∧ HMI
    for line in ("lrt-net.0.din-00 => lrt-estop2.0.ch-a", "lrt-estop2.0.ok => estop_chain.in0",
                 "lrt-net.0.connected => estop_chain.in1",
                 "estop_chain.out => estop_chain_hmi.in0",
                 "net linumert.hmi.estop-ok    => estop_chain_hmi.in1",
                 "estop_chain_hmi.out => estop_latch.ok-in"):
        assert line in plant, line
    hmi = HMI_HAL.read_text(encoding="utf-8")
    assert "personality=0x103" in hmi  # grzyb ∧ watchdog ∧ potwierdzenie
    assert "iocontrol.0.user-enable-out => lrt_estop_edge.in" in hmi  # każdy E-STOP kasuje ack
    assert "lrt_ack_edge.out => lrt_hmi_ack.set" in hmi
    assert "lrt_hmi_ack.out => lrt_hmi_ok.in-02" in hmi
    assert "net linumert.hmi.estop-ok       lrt_hmi_bypass.out" in hmi


def test_screen_creates_pins_and_hides_qtdragon_reset() -> None:
    handler = (ROOT / "screens/linumert/linumert_handler.py").read_text(encoding="utf-8")
    for name in ("hmi-estop-ok", "hmi-heartbeat", "hmi-wd-enable", "hmi-ack"):
        assert f'"{name}"' in handler
    assert "self.w.action_estop.hide()" in handler
    assert "def on_keycall_ESTOP" in handler


# ---- halrun: logika łańcucha bez ekranu ----------------------------------------------------------

def _halrun_script(bypass: int = 0, timeout: float = 0.3) -> str:
    """Plik HMI + łańcuch jak w Plant: ok-in = pętla sprzętowa (sygnał hw) ∧ HMI. iocontrol
    emulowany sygnałem linumert.io.user-enable (spada przy każdym wejściu LinuxCNC w E-STOP)."""
    hmi = HMI_HAL.read_text(encoding="utf-8")
    hmi = hmi.replace("[LINUMERT]HMI_HEARTBEAT_TIMEOUT", str(timeout))
    hmi = hmi.replace("[LINUMERT]HMI_ESTOP_BYPASS", str(bypass))
    hmi = hmi.replace("iocontrol.0.user-enable-out => ", "")
    return ("loadrt threads name1=servo-thread period1=1000000\n" + hmi + """
loadrt estop_latch names=estop_latch
loadrt and2 names=chain
addf chain servo-thread
addf estop_latch servo-thread
net hw chain.in0
net linumert.hmi.estop-ok => chain.in1
net chain-ok chain.out => estop_latch.ok-in
net reset estop_latch.reset
net button lrt_hmi_ok.in-00
net beat watchdog.input-0
net wd watchdog.enable-in
net ack lrt_ack_edge.in
start
""")


@pytest.mark.linuxcnc
def test_hmi_chain_in_halrun(tmp_path: Path) -> None:  # D35 + przegląd Codexa P1
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

    def pulse(sig: str) -> None:
        cmd(f"sets {sig} 1")
        beat(0.1)
        cmd(f"sets {sig} 0")
        beat(0.1)

    def estop_event() -> None:
        """LinuxCNC wchodzi w E-STOP: user-enable-out 1 → 0 (zbocze kasuje potwierdzenie HMI)."""
        cmd("sets linumert.io.user-enable 1")
        beat(0.1)
        cmd("sets linumert.io.user-enable 0")
        beat(0.1)

    def acknowledge() -> None:
        """Zwolnienie grzyba w HMI: impuls ack + zbocze wd-enable, potem reset zatrzasku."""
        cmd("sets wd 0")
        pulse("ack")
        cmd("sets wd 1")
        beat(0.2)
        pulse("reset")

    try:
        time.sleep(1.0)
        assert not get("estop_latch.ok-out")  # bez ekranu (piny 0): łańcuch otwarty
        cmd("sets hw 1")
        cmd("sets button 1")
        beat(0.2)
        pulse("reset")
        assert not get("estop_latch.ok-out")  # bez potwierdzenia HMI reset nieskuteczny
        acknowledge()
        assert get("watchdog.ok-out") and get("lrt_hmi_ack.out") and get("estop_latch.ok-out")

        # P1: pętla sprzętowa (albo łącze Plant) przerwana i przywrócona
        cmd("sets hw 0")
        beat(0.1)
        assert not get("estop_latch.ok-out")
        estop_event()
        cmd("sets hw 1")
        beat(0.2)
        pulse("reset")  # reset inną drogą (iocontrol / komenda LinuxCNC) bez grzyba
        assert not get("lrt_hmi_ack.out") and not get("estop_latch.ok-out")
        acknowledge()
        assert get("estop_latch.ok-out")

        # grzyb wciśnięty: reset nieskuteczny nawet z impulsem ack
        cmd("sets button 0")
        beat(0.1)
        assert not get("estop_latch.ok-out")
        estop_event()
        acknowledge()
        assert not get("estop_latch.ok-out")
        cmd("sets button 1")
        acknowledge()
        assert get("estop_latch.ok-out")

        # brak sygnału życia > 0,3 s: E-STOP; wznowienie bez potwierdzenia nie wystarcza
        time.sleep(0.6)
        assert not get("watchdog.ok-out") and not get("estop_latch.ok-out")
        estop_event()
        beat(0.3)
        pulse("reset")
        assert not get("watchdog.ok-out") and not get("estop_latch.ok-out")
        acknowledge()
        assert get("watchdog.ok-out") and get("estop_latch.ok-out")
    finally:
        cmd("exit")
        proc.wait(timeout=10)
        subprocess.run(["halrun", "-U"], capture_output=True)
