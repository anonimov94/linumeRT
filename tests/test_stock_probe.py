"""Przygotówka ;@STOCK → cel sondy Plant w machine.yaml (sesja 054 p.2).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest
from linumert.machine.schema import load_machine

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
_spec = importlib.util.spec_from_file_location("stock_probe", ROOT / "tools/stock_probe.py")
stock_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stock_probe)


def test_box_top_front_left_from_origin(tmp_path, capsys):
    machine = tmp_path / "m.yaml"
    shutil.copy(MILL, machine)
    before = machine.read_text(encoding="utf-8")
    code = stock_probe.main([str(machine), "--stock", ";@STOCK BOX X100 Y80 Z20 TOP=1",
                             "--origin", "250", "350", "-90", "--write"])
    assert code == 0
    assert capsys.readouterr().out.strip() == \
        "{type: box, min: [250, 350, -109], max: [350, 430, -89]}"
    after = machine.read_text(encoding="utf-8")
    changed = [(a, b) for a, b in zip(before.splitlines(), after.splitlines(), strict=True)
               if a != b]
    assert len(changed) == 1 and changed[0][1].strip().startswith("target: {type: box")
    target = load_machine(machine).probe.target
    assert list(target.min) == [250, 350, -109] and list(target.max) == [350, 430, -89]


def test_cylinder_center_from_var_and_ngc(tmp_path, capsys):
    var = tmp_path / "linumert.var"
    var.write_text("5221 10.0\n5222 20.0\n5223 -50.0\n5241 1.0\n5242 2.0\n5243 3.0\n")
    ngc = tmp_path / "p.ngc"
    ngc.write_text("( detal )\n;@STOCK CYL D40 H10 ORIGIN=TOP_CENTER OFFSET=G55\nG0 X0\nM2\n")
    assert stock_probe.main([str(MILL), "--ngc", str(ngc), "--var", str(var)]) == 0
    assert capsys.readouterr().out.strip() == \
        "{type: box, min: [-19, -18, -7], max: [21, 22, 3]}"


@pytest.mark.parametrize("args", [
    ["--stock", ";@STOCK BOX X0 Y1 Z1", "--origin", "0", "0", "0"],
    ["--ngc", "brak.ngc", "--origin", "0", "0", "0"],
    ["--stock", ";@STOCK BOX X1 Y1 Z1", "--var", "brak.var"],
])
def test_bad_input_exits_2(args, capsys):
    assert stock_probe.main([str(MILL), *args]) == 2
    assert "błąd" in capsys.readouterr().err


def test_machine_without_probe_is_not_changed(tmp_path):
    machine = tmp_path / "m.yaml"
    machine.write_text("name: x\n")
    assert stock_probe.main([str(machine), "--stock", ";@STOCK BOX X1 Y1 Z1",
                             "--origin", "0", "0", "0", "--write"]) == 2
    assert machine.read_text() == "name: x\n"
