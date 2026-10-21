"""Estymator czasu obróbki (sesja 053): profil trapezowy, limity INI, łuki, kroki .lnx.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import pytest
from linumert.programs.estimate import (
    Limits,
    estimate_canon,
    estimate_ngc,
    limits_from_ini,
    trapezoid,
)

ROOT = Path(__file__).resolve().parents[1]
SIM_INI = ROOT / "config/sim/linumert_xyz/linumert_xyz.ini"
LIM = Limits({"X": 100, "Y": 100, "Z": 50}, {"X": 800, "Y": 800, "Z": 600}, 100, 8)


def _canon(*calls: str) -> str:
    return "\n".join(f"{i + 1:5d} N..... {c}" for i, c in enumerate(calls))


def test_trapezoid_reaches_speed_or_not():
    assert trapezoid(100, 100, 800) == pytest.approx(100 / 100 + 100 / 800)
    assert trapezoid(1, 100, 800) == pytest.approx(2 * math.sqrt(1 / 800))
    assert trapezoid(0, 100, 800) == 0 and trapezoid(10, 5, math.inf) == 2


def test_limits_from_sim_ini():
    lim = limits_from_ini(SIM_INI)
    assert lim.max_vel["Z"] == 50 and lim.max_acc["X"] == 800 and lim.max_linear == 100
    assert lim.tool_change == 10  # brak [LINUMERT]TOOL_CHANGE_TIME → domyślnie
    v, a = lim.along((0.0, 0.0, 1.0))
    assert (v, a) == (50, 600)
    v, _ = lim.along((math.sqrt(0.5), math.sqrt(0.5), 0.0))
    assert v == pytest.approx(100)  # TRAJ ogranicza ukos (osie pozwalają 141 mm/s)


def test_rapid_feed_dwell_and_tool_change():
    est = estimate_canon(_canon(
        "USE_LENGTH_UNITS(CANON_UNITS_MM)", "CHANGE_TOOL(3)",
        "STRAIGHT_TRAVERSE(100.0000, 0.0000, 0.0000, 0, 0, 0)",
        "SET_FEED_RATE(600.0000)", "STRAIGHT_FEED(100.0000, 50.0000, 0.0000, 0, 0, 0)",
        "DWELL(1.5000)", "STRAIGHT_FEED(100.0000, 50.0000, -10.0000, 0, 0, 0)"), LIM)
    rapid = trapezoid(100, 100, 800)
    feed = trapezoid(50, 10, 800) + trapezoid(10, 10, 600)
    assert est.rapid == pytest.approx(rapid) and est.feed == pytest.approx(feed)
    assert est.dwell == 1.5 and est.tool_change == 8
    assert est.total == pytest.approx(rapid + feed + 1.5 + 8)
    assert est.per_tool == {3: pytest.approx(est.total)}
    assert est.rapid_length == 100 and est.feed_length == 60


def test_arc_length_and_centripetal_limit():
    half = estimate_canon(_canon(
        "STRAIGHT_TRAVERSE(10.0000, 10.0000, 0.0000, 0, 0, 0)", "SET_FEED_RATE(6000.0000)",
        "ARC_FEED(20.0000, 10.0000, 15.0000, 10.0000, -1, 0.0000, 0, 0, 0)"), LIM)
    assert half.feed_length == pytest.approx(math.pi * 5)
    v = math.sqrt(0.5 * 800 * 5)  # 44.7 mm/s < F 100 mm/s
    assert half.feed == pytest.approx(trapezoid(math.pi * 5, v, 800))
    full = estimate_canon(_canon(
        "STRAIGHT_TRAVERSE(10.0000, 10.0000, 0.0000, 0, 0, 0)", "SET_FEED_RATE(600.0000)",
        "ARC_FEED(10.0000, 10.0000, 15.0000, 10.0000, 1, -2.0000, 0, 0, 0)"), LIM)
    assert full.feed_length == pytest.approx(math.hypot(2 * math.pi * 5, 2))


def test_inch_program_scaled():
    est = estimate_canon(_canon(
        "USE_LENGTH_UNITS(CANON_UNITS_INCHES)", "SET_FEED_RATE(10.0000)",
        "STRAIGHT_FEED(1.0000, 0.0000, 0.0000, 0, 0, 0)"), LIM)
    assert est.feed_length == pytest.approx(25.4)
    assert est.feed == pytest.approx(trapezoid(25.4, 254 / 60, 800))


def test_time_per_lnx_step():
    est = estimate_canon(_canon(
        'COMMENT("krok 1: tool_change v1")', "CHANGE_TOOL(1)",
        'COMMENT("krok 2: face_mill v1 - plyta")',
        "STRAIGHT_TRAVERSE(50.0000, 0.0000, 0.0000, 0, 0, 0)"), LIM)
    assert est.per_step[1] == 8 and est.per_step[2] == pytest.approx(trapezoid(50, 100, 800))


def test_steep_helix_respects_z_velocity_and_acceleration():
    limits = Limits({"X": 100, "Y": 100, "Z": 1}, {"X": 800, "Y": 800, "Z": 2}, 100)
    result = estimate_canon(_canon("SET_FEED_RATE(6000)",
        "STRAIGHT_TRAVERSE(1, 0, 0, 0, 0, 0)",
        "ARC_FEED(1, 0, 0, 0, 1, -20, 0, 0, 0)"), limits)
    assert result.feed >= 20  # sama oś Z wymaga minimum 20 s przy 1 mm/s


@pytest.mark.parametrize("call", ["SELECT_PLANE(CANON_PLANE_XZ)", "SET_FEED_MODE(0, 1)"])
def test_refuses_unsupported_time_model(call):
    with pytest.raises(ValueError):
        estimate_canon(_canon(call, "SET_FEED_RATE(600)",
                              "ARC_FEED(1, 0, 0, 0, 1, -20, 0, 0, 0)"), LIM)


def test_refuses_missing_axis_limits(tmp_path):
    path = tmp_path / "missing.ini"
    with pytest.raises(ValueError):
        limits_from_ini(path)
    path.write_text("[TRAJ]\nMAX_LINEAR_VELOCITY=100\n")
    with pytest.raises(ValueError):
        limits_from_ini(path)


@pytest.mark.linuxcnc
def test_estimate_compiled_program_in_rs274(tmp_path):
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "bin" / "rs274").exists():
        pytest.skip(f"brak rs274 w {root}")
    ngc = tmp_path / "p.ngc"
    ngc.write_text("G21 G90 G17\n( krok 1: test )\nG0 X100 Y0 Z0\nG1 X100 Y50 F600\n"
                   "o100 repeat [3]\nG1 Z-1\nG1 Z0\no100 endrepeat\nG4 P2\nM2\n")
    est = estimate_ngc(ngc, SIM_INI, root)
    assert est.feed_length == pytest.approx(50 + 6, abs=1e-6) and est.dwell == 2
    assert est.rapid_length == pytest.approx(100, abs=1e-6)
    assert est.per_step[1] == pytest.approx(est.total)
