"""Sesja 049: suite_cycles — przygotowanie programu dla atrapy i przebieg na Plant.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import importlib.util
import math
import re
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("suite_cycles", ROOT / "tools/suite_cycles.py")
sc = importlib.util.module_from_spec(spec)
sys.modules["suite_cycles"] = sc       # @dataclass szuka modułu w sys.modules
spec.loader.exec_module(sc)


def _xyz(line):
    return {k: float(v) for k, v in re.findall(r"([XYZF])(-?[0-9.]+)", line)}


def test_arcs_become_chords_ending_exactly_on_target():
    out = sc.for_mock(["G0 X10 Y0", "G3 X0 Y10 Z-1 I-10 J0 F300"])
    chords = [line for line in out if line.startswith("G1")]
    assert len(chords) == 30                                     # 90° co 3°
    end = _xyz(chords[-1])
    assert (end["X"], end["Y"], end["Z"]) == (0, 10, -1) and end["F"] == 300
    for line in chords:
        p = _xyz(line)
        assert math.hypot(p["X"], p["Y"]) == pytest.approx(10, abs=1e-3)
    full = sc.for_mock(["G0 X5 Y0", "G2 X5 Y0 I-5 J0"])
    assert len([line for line in full if line.startswith("G1")]) == 120


def test_canned_cycles_expand_with_retract_modes_and_pecks():
    out = sc.for_mock(["G0 Z-18", "G99 G83 X110 Y110 Z-26 R-18 Q3 F100", "X120 Y110", "G80"],
                      start=(0, 0, -5))
    feeds = [_xyz(line)["Z"] for line in out if line.startswith("G1 Z")]
    assert feeds[:3] == [-21, -24, -26] and feeds.count(-26) == 2      # dwa otwory
    assert "G0 X120.0000 Y110.0000" in out and out[-1] == "G0 Z-18.0000"   # G99: na R
    g98 = sc.for_mock(["G0 Z-10", "G98 G81 X5 Y5 Z-26 R-18 F100", "G80"], start=(0, 0, -5))
    assert g98[-1] == "G0 Z-10.0000"                                   # G98: na Z początkową
    assert not any(line.startswith(("G8", "G9")) for line in out)


def test_limit_rapids_restores_program_feed():
    out = sc.limit_rapids(["G0 Z-5", "G1 Z-6 F100", "G0 X10", "G1 X20", "G1 X30 F400"], 3000)
    assert out == ["G1 Z-5 F3000.0000", "G1 Z-6 F100", "G1 X10 F3000.0000", "G1 X20 F100",
                   "G1 X30 F400"]


def test_every_case_is_valid_for_its_generator():
    reg = sc.registry()
    for name, params in sc.CASES:
        assert reg.latest(name).validate(params) == [], name


def test_rapid_limited_stud_on_both_machines():
    for machine in sc.MACHINES:
        with tempfile.TemporaryDirectory() as tmp:
            row = sc.run_case("stud_circle", {"cx": 150, "cy": 150, "diameter": 20, "tool_d": 6,
                                              "depth": 1, "margin": 0, **sc.PART},
                              machine, Path(tmp), mode="B")
        assert row.passed, (machine, row.detail)
        assert all(v <= sc.WINDOW_MM for v in row.max_fe.values())
