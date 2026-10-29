# SPDX-License-Identifier: GPL-2.0-or-later
"""Generator: wyjście sprzętowe step/dir (Mesa, port równoległy) i kontrakt bezpieczeństwa (062).

Model-Author: Claude · 2026-10-24. Kontrola deklaracji i statyczny audyt HAL Codex
(`linumert.machine.deployment --hal-from-ini`) na wygenerowanych plikach.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from linumert.machine import deployment
from linumert.machine.config_build import main as config_main
from linumert.machine.configgen import Options, render
from linumert.machine.configgen_hw import HardwareConfigError
from linumert.machine.schema import parse_machine

ROOT = Path(__file__).resolve().parents[1]
MESA = ROOT / "config/hardware/router_gantry_mesa.example.yaml"
OPT = Options(hal_dir=str(ROOT / "config/hal"))


def _data() -> dict:
    return yaml.safe_load(MESA.read_text(encoding="utf-8"))


def _parport(data: dict) -> dict:
    data = copy.deepcopy(data)
    # Dwa porty nie są modelowane; przykład z jednym LPT: X, Z i brama Y bez krańcówek max.
    data["hardware"] = {
        "interface": "parport", "address": "0x378", "base_period_ns": 30000,
        "channels": {"drv_x": 0, "drv_y1": 1, "drv_y2": 2, "drv_z": 3},
        "step_dir": {"drv_x": [2, 3], "drv_y1": [4, 5], "drv_y2": [6, 7], "drv_z": [8, 9]},
        "inputs": {"estop": "parport.0.pin-15-in", "lim_x_min": "parport.0.pin-10-in",
                   "lim_y_min": "parport.0.pin-11-in", "lim_z_max": "parport.0.pin-12-in"},
        "outputs": {"spindle_on": "parport.0.pin-14-out"},
        "heartbeat_output": "parport.0.pin-16-out",
        "watchdog_monitor": "parport.0.pin-13-in",
        "spindle_device": "/dev/ttyUSB0"}
    for axis in data["axes"]:
        axis["limits"].pop("max", None) if axis["letter"] != "Z" else None
    return data


def _write(tmp: Path, files: dict[str, str]) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (tmp / name).parent.mkdir(parents=True, exist_ok=True)  # macros/lrt_probe.ngc
        (tmp / name).write_text(text, encoding="utf-8")
    return next(tmp / n for n in files if n.endswith(".ini"))


def _audit(ini: Path, capsys) -> dict:
    code = deployment.main([str(ini), "--hal-from-ini"])
    report = json.loads(capsys.readouterr().out)
    report["code"] = code
    return report


def test_mesa_example_passes_safety_declaration_and_hal_audit(tmp_path, capsys):
    files = render(parse_machine(_data()), "hardware", OPT)
    ini = _write(tmp_path / "mesa", files)
    report = _audit(ini, capsys)
    assert report["code"] == 0 and report["declaration_complete"], report["errors"]
    assert report["static_hal_passed"] and report["hardware_verified"] is False
    hal = files["linumert_hw.hal"]
    assert 'loadrt hm2_eth board_ip="10.10.10.10"' in hal
    assert "hm2_7i96s.0.stepgen.03.position-cmd" in hal and "base-thread" not in hal
    # E-STOP: monitor wprost do LinuxCNC, bez grzyba HMI w torze.
    assert ("net linumert.io.estop-ok     hm2_7i96s.0.inm.00.input-00 => "
            "iocontrol.0.emc-enable-in") in hal
    text = files["router_gantry_mesa.ini"]
    assert "MACHINE_PROFILE = hardware" in text and "VIRTUAL_MODE = 0" in text
    assert "SCALE = 640.00" in text and "BASE_PERIOD = 0" in text
    assert "hm2_7i96s.0.ssr.00.out-01" in files["linumert_hw_postgui.hal"]


def test_parport_uses_base_thread_and_warns(tmp_path, capsys):
    files = render(parse_machine(_parport(_data())), "hardware", OPT)
    hal = files["linumert_hw.hal"]
    assert "Port równoległy" in hal and 'loadrt hal_parport cfg="0x378 out"' in hal
    assert "addf stepgen.make-pulses base-thread" in hal
    assert "net linumert.j3.step      stepgen.3.step => parport.0.pin-08-out" in hal
    assert "BASE_PERIOD = 30000" in files["router_gantry_mesa.ini"]
    report = _audit(_write(tmp_path / "lpt", files), capsys)
    assert report["code"] == 0, report["errors"]


@pytest.mark.parametrize("change, message", [
    (lambda d: d["hardware"]["inputs"].pop("estop"), "bez wejścia E-STOP"),
    (lambda d: d["hardware"].pop("heartbeat_output"), "sygnału życia"),
    (lambda d: d["hardware"].pop("watchdog_monitor"), "watchdoga"),
    (lambda d: d["hardware"]["inputs"].pop("lim_y_max"), "krańcówki Y max"),
    (lambda d: d["hardware"].update(interface="ethercat", board=None), "063"),
])
def test_unsafe_or_incomplete_hardware_is_refused(change, message):
    data = _data()
    change(data)
    with pytest.raises(HardwareConfigError) as exc:
        render(parse_machine(data), "hardware", OPT)
    assert any(message in e for e in exc.value.errors), exc.value.errors


def test_cli_refuses_hardware_target_for_plant_machine(tmp_path, capsys):
    out = tmp_path / "cfg"
    code = config_main(["build", str(ROOT / "config/machines/router_gantry_steppers.yaml"),
                        "--target", "hardware", "--out", str(out), "--write"])
    assert code == 2 and "target: hardware" in capsys.readouterr().err and not out.exists()
