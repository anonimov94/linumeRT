"""Okablowanie HAL makra ATC (M64/M65/M66) z Plant w generatorze konfiguracji, krok 3 ATC 066.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 066.
"""

import copy
import re
from pathlib import Path

import pytest
import yaml

from linumert.machine.atc_macro import generate_atc_m6
from linumert.machine.configgen import Options, atc_dio, render
from linumert.machine.schema import parse_machine

ROUTER = Path(__file__).resolve().parents[1] / "config" / "machines" / "router_atc_rack.yaml"


def _data():
    return yaml.safe_load(ROUTER.read_text(encoding="utf-8"))


def _hal(data, atc=True):
    files = render(parse_machine(copy.deepcopy(data)), "plant", Options(atc=atc))
    return files["linumert_plant.hal"]


def test_every_macro_pin_is_wired_to_plant():
    data = _data()
    outs, ins = atc_dio(generate_atc_m6(parse_machine(copy.deepcopy(data))))
    assert outs and ins
    hal = _hal(data)
    for p in outs:
        net = rf"motion\.digital-out-{p:02d} => lrt-net\.0\.dout-{p:02d}"
        assert re.search(rf"(?m)^net \S+ +{net}$", hal)
    for p in ins:
        net = rf"lrt-net\.0\.din-{p:02d} => motion\.digital-in-{p:02d}"
        assert re.search(rf"(?m)^net \S+ +{net}$", hal)
    # motmod musi mieć tyle pinów, by M64/M66 Pn istniały w motion
    assert f"num_joints=[KINS]JOINTS num_dio={max(outs + ins) + 1}\n" in hal


def test_without_atc_hal_is_unchanged():
    hal = _hal(_data(), atc=False)
    assert "num_dio" not in hal and "motion.digital" not in hal


def test_pin_collision_is_refused():
    data = _data()
    data["io"]["outputs"]["tool_release"] = 31   # dout-31 zajęte przez wyrocznię bazowania
    with pytest.raises(ValueError, match="dout-31"):
        _hal(data)
