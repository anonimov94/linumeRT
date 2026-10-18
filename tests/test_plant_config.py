"""Konfiguracja LinuxCNC dla Plant zgodna z machine.yaml (sesja 018, bez LinuxCNC).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 018.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "plant" / "linumert_plant_xyz"
INI = CFG / "linumert_plant_xyz.ini"
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"


def _ini() -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None, inline_comment_prefixes=None)
    cp.optionxform = str
    cp.read(INI, encoding="utf-8")
    return cp


def _machine() -> dict:
    return yaml.safe_load(MACHINE.read_text(encoding="utf-8"))


def _joints(data: dict) -> list[tuple[dict, str]]:
    """Jointy LinuxCNC = napędy osi w kolejności drives: bez wrzeciona (kolejność ramki LRT-NET)."""
    owner = {d: a for a in data["axes"] for d in a["drives"]}
    return [(owner[d["id"]], d["id"]) for d in data["drives"] if d["id"] in owner]


def test_joints_follow_drive_order_and_plant_axes():
    cp, data = _ini(), _machine()
    joints = _joints(data)
    assert int(cp["KINS"]["JOINTS"]) == len(joints) == int(cp["PLANT"]["AXES"])
    assert cp["TRAJ"]["COORDINATES"] == "".join(a["letter"] for a, _ in joints)
    for j, (axis, _) in enumerate(joints):
        assert cp[f"JOINT_{j}"]["AXIS"] == axis["letter"]


def test_scale_matches_plant_model():
    from linumert_plant.build_machine import build_machine

    model = build_machine(MACHINE)
    cp = _ini()
    for j, (_, drive) in enumerate(_joints(_machine())):
        assert float(cp[f"JOINT_{j}"]["SCALE"]) == pytest.approx(model.counts_per_unit[drive],
                                                                  rel=1e-8)


def test_limits_and_homing_match_machine_yaml():
    cp, data = _ini(), _machine()
    for axis in data["axes"]:
        sec = cp[f"AXIS_{axis['letter']}"]
        assert (float(sec["MIN_LIMIT"]), float(sec["MAX_LIMIT"])) == tuple(axis["soft_limits"])
        assert float(sec["MAX_VELOCITY"]) == axis["max_velocity"]
        assert float(sec["MAX_ACCELERATION"]) == axis["max_acceleration"]
    for j, (axis, _) in enumerate(_joints(data)):
        sec, h = cp[f"JOINT_{j}"], axis["homing"]
        assert float(sec["HOME_SEARCH_VEL"]) == h["direction"] * h["search_speed"]
        latch_sign = 1 if h.get("latch", "approach") == "approach" else -1
        assert float(sec["HOME_LATCH_VEL"]) == latch_sign * h["direction"] * h["latch_speed"]
        side = "limit_min" if h["direction"] < 0 else "limit_max"
        assert axis["home_sensor"]["shared_with"] == side
        switch = axis["limits"]["min" if side == "limit_min" else "max"]
        assert float(sec["HOME_OFFSET"]) == switch["position"]
        assert sec["HOME_IGNORE_LIMITS"] == "YES"  # czujnik bazy = krańcówka


def test_hal_uses_inputs_from_machine_yaml():
    hal = (CFG / "linumert_plant.hal").read_text(encoding="utf-8")
    inputs = _machine()["io"]["inputs"]
    for name in ("lim_x_min", "lim_x_max", "lim_y_min", "lim_y_max", "lim_z_max"):
        assert re.search(rf"lrt-net\.0\.din-{inputs[name]:02d} => nc_{name[4:]}\.in", hal), name
    assert f"lrt-net.0.din-{inputs['estop']:02d} => estop_chain.in0" in hal
    assert f"lrt-net.0.din-{inputs['probe']:02d} => motion.probe-input" in hal
    assert "loadrt lrt_net personality=[PLANT]AXES ip=[PLANT]IP port=[PLANT]PORT" in hal


def test_screen_and_plant_yaml():
    cp = _ini()
    assert cp["DISPLAY"]["DISPLAY"] == "qtvcp linumert"
    assert (CFG / "qtvcp" / "screens" / "linumert" / "linumert.ui").is_file()
    plant = yaml.safe_load((CFG / "plant.yaml").read_text(encoding="utf-8"))
    assert (CFG / plant["machine"]).resolve() == MACHINE.resolve()
    assert plant["network"]["port"] == int(cp["PLANT"]["PORT"])
