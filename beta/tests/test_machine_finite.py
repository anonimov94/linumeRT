"""Niepoprawne liczby w machine.yaml nie mogą dotrzeć do modelu Plant.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from linumert.machine.schema import MachineConfigError, parse_machine
from linumert.machine.validate import load_valid_machine
from linumert_plant.machine_drives import load_machine_drives

ROOT = Path(__file__).resolve().parents[1]
BASE = yaml.safe_load((ROOT / "config/machines/router_gantry_steppers.yaml").read_text("utf-8"))

# Pola ograniczone zakresem, bez ograniczeń, zagnieżdżone, opcjonalne i wektory.
CASES = [
    ("axes", 0, "max_velocity"),
    ("axes", 0, "max_acceleration"),
    ("axes", 0, "travel", 0),
    ("axes", 0, "soft_limits", 1),
    ("axes", 0, "hardstops", "min", "position"),
    ("axes", 0, "limits", "min", "hysteresis"),
    ("axes", 0, "homing", "offset"),
    ("axes", 0, "homing", "search_speed"),
    ("spindle", "ramp_up_s"),
    ("positions", "manual_change", 0),
    ("positions", "safe_z"),
    ("positions", "tool_setter", "height"),
    ("toolchanger", "base_orientation_deg"),
    ("toolchanger", "slot_positions", 0, 1),
    ("forbidden_zones", 0, "min", 0),
    ("collision_bodies", 0, "size", 0),
    ("kinematics", "chain", 0, "axis", 0),
    ("kinematics", "chain", 0, "offset", 0),
]


def _data(path, value):
    data = copy.deepcopy(BASE)
    data["positions"]["manual_change"] = [100, 100, -10]
    data["positions"]["tool_setter"] = {
        "position": [100, 100, -10], "height": 5, "input": "setter",
    }
    data["toolchanger"] = {"type": "rack_linear", "slots": 1,
                           "slot_positions": [[100, 100, -10]]}
    data["forbidden_zones"] = [{"name": "zone", "min": [0, 0, -50], "max": [1, 1, -40]}]
    data["collision_bodies"] = [{"name": "table", "shape": "box", "attached_to": "table",
                                 "size": [10, 10, 10], "position": [0, 0, -100]}]
    data["kinematics"] = {"chain": [
        {"id": a, "kind": "linear", "axis": v, "offset": [0, 0, 0]}
        for a, v in zip("XYZ", ([1, 0, 0], [0, 1, 0], [0, 0, 1]), strict=True)
    ]}
    parent = data
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    return data


def _field(path):
    return ".".join(str(p) for p in path).replace(".0", "[0]").replace(".1", "[1]")


@pytest.mark.parametrize("path", CASES, ids=_field)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "1e999"])
def test_nonfinite_field_rejected_with_path(path, value):  # REQ-VM-11, REQ-QA-03
    with pytest.raises(MachineConfigError) as caught:
        parse_machine(_data(path, value))
    assert f"{_field(path)}: oczekiwano liczby skonczonej" in caught.value.errors


@pytest.mark.parametrize("loader", [load_valid_machine, load_machine_drives])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_yaml_rejected_before_start(tmp_path, loader, value):  # REQ-VM-01, REQ-QA-03
    data = copy.deepcopy(BASE)
    data["axes"][0]["max_velocity"] = value
    path = tmp_path / "machine.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(MachineConfigError, match="axes\\[0\\].max_velocity"):
        loader(path)
    assert path.read_bytes() == before


def test_multiple_nonfinite_fields_reported_together():  # REQ-VM-11
    data = copy.deepcopy(BASE)
    data["axes"][0]["travel"][0] = float("nan")
    data["spindle"]["max_rpm"] = float("inf")
    with pytest.raises(MachineConfigError) as caught:
        parse_machine(data)
    assert set(caught.value.errors) == {
        "axes[0].travel[0]: oczekiwano liczby skonczonej",
        "spindle.max_rpm: oczekiwano liczby skonczonej",
    }
