# SPDX-License-Identifier: GPL-2.0-or-later
"""Napędy rzeczywiste: sekcja real: szablonów i plan sprzętu z machine.yaml (sesja 061).

Model-Author: Claude · 2026-10-24. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import pytest
import yaml

from linumert.machine.schema import MachineConfigError, parse_machine
from linumert_plant.drive_library import load_library
from linumert_plant.drive_real import counts_per_unit, hardware_plan
from linumert_plant.drive_template import template_issues
from linumert_plant.machine_drives import resolve_machine_drives

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "config/machines/router_gantry_steppers.yaml"
MILL = ROOT / "config/machines/mill_servo_table.yaml"


@pytest.fixture(scope="module")
def library():
    return load_library()


def _machine(path: Path, **extra) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(extra)
    return data


def test_template_real_mapping(library):  # REQ-VD-06
    """Ten sam machine.yaml daje Plant i plan sprzętu; skala z mechaniki szablonu."""
    assert all("real" in tpl for tpl in library.values()), "każdy szablon ma sekcję real:"
    hw = {"interface": "parport", "address": "0x378",
          "channels": {"drv_x": 0, "drv_y1": 1, "drv_y2": 2, "drv_z": 3},
          "spindle_device": "/dev/ttyUSB0"}
    plant_cfg = parse_machine(_machine(ROUTER))
    hw_cfg = parse_machine(_machine(ROUTER, target="hardware", hardware=hw))
    assert plant_cfg.target == "plant" and hw_cfg.target == "hardware"
    # Poza celem i sekcją hardware opis maszyny jest ten sam.
    assert plant_cfg.model_dump(exclude={"target", "hardware"}) == hw_cfg.model_dump(
        exclude={"target", "hardware"})
    drives = resolve_machine_drives(hw_cfg, library)
    plan = hardware_plan(hw_cfg, drives)
    axes = [p for p in plan if p["axis"] != "S"]
    assert [(p["axis"], p["drive"], p["joint"], p["channel"]) for p in axes] == [
        ("X", "drv_x", 0, 0), ("Y", "drv_y1", 1, 1), ("Y", "drv_y2", 2, 2), ("Z", "drv_z", 3, 3)]
    # NEMA 23: 3200 mikrokroków/obr, śruba 5 mm/obr → 640 kroków/mm.
    assert all(p["driver"] == "stepgen" for p in axes)
    assert axes[0]["scale"] == pytest.approx(640.0, rel=1e-4)
    assert axes[0]["timing_ns"]["dirsetup"] >= axes[0]["timing_ns"]["steplen"]
    # oczekiwane przyspieszenia pochodzą z machine.yaml (zestrojone narzędziem tune_accel)
    expected = {a.letter: a.max_acceleration for a in plant_cfg.axes}
    assert axes[0]["max_velocity"] == 200 and axes[3]["max_acceleration"] == expected["Z"]
    spindle = plan[-1]
    assert spindle["driver"] == "vfd_modbus" and spindle["vfd"]["protocol"] == "hy_vfd"
    assert spindle["device"] == "/dev/ttyUSB0" and spindle["max_rpm"] == 24000


def test_servo_machine_maps_to_ethercat(library):  # REQ-VD-06
    data = _machine(MILL)
    names = [d["id"] for d in data["drives"] if d["id"] != data["spindle"]["drive"]]
    hw = {"interface": "ethercat", "channels": {n: i for i, n in enumerate(names)},
          "spindle_device": "/dev/ttyUSB0"}
    cfg = parse_machine({**data, "target": "hardware", "hardware": hw})
    plan = hardware_plan(cfg, resolve_machine_drives(cfg, library))
    axes = [p for p in plan if p["axis"] != "S"]
    assert axes and all(p["driver"] == "ethercat_cia402" for p in axes)
    assert all({"6040h", "6041h", "607Ah", "6064h"} <= set(p["pdo"]) for p in axes)
    # Skala serwa = impulsy enkodera na mm z tego samego szablonu co model Plant.
    tpl = resolve_machine_drives(cfg, library)[axes[0]["drive"]].params
    expected = tpl["motor"]["encoder_counts_per_rev"] / (
        tpl["mechanics"]["ratio"] * math.tau * 1000)
    assert axes[0]["scale"] == pytest.approx(expected)
    # Krokowiec na EtherCAT nie przejdzie z interfejsem parport (i odwrotnie).
    bad = parse_machine({**data, "target": "hardware",
                         "hardware": {**hw, "interface": "parport"}})
    with pytest.raises(ValueError) as exc:
        hardware_plan(bad, resolve_machine_drives(bad, library))
    assert any("ethercat_cia402 wymaga" in e for e in exc.value.args[0])


def test_hardware_section_rules(library):
    with pytest.raises(MachineConfigError, match="target: hardware wymaga"):
        parse_machine(_machine(ROUTER, target="hardware"))
    with pytest.raises(MachineConfigError, match="board"):
        parse_machine(_machine(ROUTER, target="hardware",
                               hardware={"interface": "mesa", "channels": {"drv_x": 0}}))
    with pytest.raises(MachineConfigError, match="nieznane napędy"):
        parse_machine(_machine(ROUTER, target="hardware",
                               hardware={"interface": "parport", "channels": {"drv_q": 0}}))
    cfg = parse_machine(_machine(ROUTER, target="hardware", hardware={
        "interface": "mesa", "board": "7i96s", "address": "10.10.10.10",
        "channels": {"drv_x": 0, "drv_y1": 1, "drv_y2": 1}}))
    with pytest.raises(ValueError) as exc:
        hardware_plan(cfg, resolve_machine_drives(cfg, library))
    messages = " ".join(exc.value.args[0])
    assert "brak kanału napędu drv_z" in messages and "tym samym kanale" in messages
    assert "spindle_device" in messages


def test_real_section_validation(library):
    tpl = copy.deepcopy(library["stepper_nema23_3nm"])
    tpl["real"] = {"driver": "vfd_modbus", "vfd": {"protocol": "hy_vfd", "baud": 19200,
                                                   "address": 1}}
    assert any("nie może mieć sterownika" in i.message for i in template_issues(tpl))
    tpl["real"] = {"driver": "stepgen", "timing_ns": {"steplen": 50, "stepspace": 5000,
                                                      "dirsetup": 1, "dirhold": 1}}
    paths = {i.path for i in template_issues(tpl)}
    assert {"real.timing_ns.steplen", "real.timing_ns.dirsetup"} <= paths
    tpl["real"] = {"driver": "stepgen", "timing_ns": {"steplen": 5000, "stepspace": 5000,
                                                      "dirsetup": 20000, "dirhold": 20000},
                   "pdo": ["6040h"]}
    assert any(i.path == "real.pdo" for i in template_issues(tpl))
    servo = copy.deepcopy(library["servo_400w"])
    servo["real"] = {"driver": "ethercat_cia402", "pdo": ["6040h", "6041h"]}
    assert any("607Ah" in i.message for i in template_issues(servo))
    rotary = library["rotary_table_worm_1_90"]
    # Stół obrotowy: impulsy na stopień.
    assert counts_per_unit(rotary) == pytest.approx(
        rotary["motor"]["encoder_counts_per_rev"] / (rotary["mechanics"]["ratio"] * 360))
