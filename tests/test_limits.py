"""Kontrola limitów osi przed startem (zakres 031/051)."""

import os
from pathlib import Path

import pytest
from linumert.programs.limits import (
    analyze_canon,
    check_canon,
    check_ngc,
    limits_from_ini,
    number_lines,
)

ROOT = Path(__file__).resolve().parents[1]
SIM_INI = ROOT / "config/sim/linumert_xyz/linumert_xyz.ini"
LIM = {"X": (0.0, 600.0), "Y": (0.0, 400.0), "Z": (-120.0, 0.0)}


def _canon(*calls: str) -> str:
    return "\n".join(f"{i + 1:5d} N{9 + i:05d} {c}" for i, c in enumerate(calls))


def test_limits_from_sim_ini():
    assert limits_from_ini(SIM_INI)["Z"] == (-120.0, 0.0)


def test_inside_limits_is_clean():
    assert check_canon(_canon("STRAIGHT_FEED(10.0, 10.0, -5.0, 0, 0, 0)"), LIM) == []


def test_reports_line_axis_and_side():
    got = check_canon(_canon("STRAIGHT_TRAVERSE(0, 0, -130.0, 0, 0, 0)",
                             "STRAIGHT_FEED(700.0, 0, -1.0, 0, 0, 0)"), LIM)
    assert [(v.line, v.axis, v.side) for v in got] == [(9, "Z", "min"), (10, "X", "max")]
    assert "linia 9" in got[0].message() and "-130.000" in got[0].message()


def test_g54_offset_and_tool_length_are_added():
    canon = _canon("SET_G5X_OFFSET(1, 0.0, 0.0, -150.0, 0, 0, 0)",
                   "STRAIGHT_TRAVERSE(0, 0, 20.0, 0, 0, 0)",
                   "USE_TOOL_LENGTH_OFFSET(0.0, 0.0, 30.0, 0, 0, 0, 0, 0, 0)",
                   "STRAIGHT_FEED(0, 0, -15.0, 0, 0, 0)")
    got = check_canon(canon, LIM)
    assert [(v.line, v.value, v.side, v.count) for v in got] == [(10, -130.0, "min", 2)]
    assert "i 1 kolejnych" in got[0].message()


def test_cutting_without_tool_length_offset_is_flagged():
    cut = _canon("STRAIGHT_TRAVERSE(0, 0, 20.0, 0, 0, 0)", "STRAIGHT_FEED(5, 0, -1.0, 0, 0, 0)")
    assert analyze_canon(cut, LIM).cuts_without_tlo
    with_tlo = _canon("USE_TOOL_LENGTH_OFFSET(0, 0, 80.0, 0, 0, 0, 0, 0, 0)",
                      "STRAIGHT_FEED(5, 0, -100.0, 0, 0, 0)")
    assert not analyze_canon(with_tlo, LIM).cuts_without_tlo
    assert analyze_canon(_canon("STRAIGHT_TRAVERSE(0, 0, -5.0, 0, 0, 0)"), LIM).ok


def test_axis_not_yet_moved_is_not_judged():
    limits = {"X": (1.0, 599.0), "Z": (-119.0, -1.0)}
    first = _canon("STRAIGHT_TRAVERSE(0.0, 0, -5.0, 0, 0, 0)")  # X zostaje w zerze interpretera
    assert check_canon(first, limits) == []
    later = _canon("STRAIGHT_TRAVERSE(50.0, 0, -5.0, 0, 0, 0)",
                   "STRAIGHT_TRAVERSE(0.0, 0, -5.0, 0, 0, 0)")
    assert [(v.line, v.axis) for v in check_canon(later, limits)] == [(10, "X")]


def test_inches_are_converted():
    canon = _canon("USE_LENGTH_UNITS(CANON_UNITS_INCHES)",
                   "STRAIGHT_FEED(30.0, 0, 0, 0, 0, 0)")
    assert [v.axis for v in check_canon(canon, LIM)] == ["X"]  # 30 in = 762 mm


def test_arc_endpoint_is_checked():
    assert check_canon(_canon("ARC_FEED(700.0, 0.0, 650.0, 0.0, 1, -1.0)"), LIM)[0].axis == "X"


def test_ccw_arc_detects_y_max_between_endpoints():
    limits = {"X": (0.0, 50.0), "Y": (0.0, 15.0)}
    canon = _canon("STRAIGHT_TRAVERSE(30, 10, 0, 0, 0, 0)",
                   "ARC_FEED(10, 10, 20, 10, 1, 0)")
    got = check_canon(canon, limits)
    assert [(v.line, v.axis, v.side) for v in got] == [(10, "Y", "max")]
    assert got[0].value == pytest.approx(20.0)


def test_cw_arc_between_same_endpoints_stays_inside_limits():
    limits = {"X": (0.0, 50.0), "Y": (0.0, 15.0)}
    canon = _canon("STRAIGHT_TRAVERSE(30, 10, 0, 0, 0, 0)",
                   "ARC_FEED(10, 10, 20, 10, -1, 0)")
    assert check_canon(canon, limits) == []


def test_full_circle_checks_extrema_on_both_axes():
    limits = {"X": (6.0, 16.0), "Y": (6.0, 14.0)}
    canon = _canon("STRAIGHT_TRAVERSE(15, 10, 0, 0, 0, 0)",
                   "ARC_FEED(15, 10, 10, 10, 1, 0)")
    got = check_canon(canon, limits)
    assert {(v.axis, v.side) for v in got} == {("X", "min"), ("Y", "min"), ("Y", "max")}
    assert {v.line for v in got} == {10}


def test_cw_full_circle_checks_extrema_on_both_axes():
    limits = {"X": (6.0, 16.0), "Y": (6.0, 14.0)}
    canon = _canon("STRAIGHT_TRAVERSE(15, 10, 0, 0, 0, 0)",
                   "ARC_FEED(15, 10, 10, 10, -1, 0)")
    got = check_canon(canon, limits)
    assert {(v.axis, v.side) for v in got} == {("X", "min"), ("Y", "min"), ("Y", "max")}
    assert {v.line for v in got} == {10}


def test_xz_arc_extremum_uses_z_then_x_order():
    limits = {"X": (0.0, 15.0), "Y": (-10.0, 10.0), "Z": (-40.0, 0.0)}
    canon = _canon("SELECT_PLANE(CANON_PLANE_XZ)",
                   "STRAIGHT_TRAVERSE(10, 0, -10, 0, 0, 0)",
                   "ARC_FEED(-30, 10, -20, 10, 1, 0)")
    got = check_canon(canon, limits)
    assert [(v.line, v.axis, v.side) for v in got] == [(11, "X", "max")]
    assert got[0].value == pytest.approx(20.0)


def test_xy_rotation_changes_linear_machine_limits():
    limits = {"X": (-20.0, 20.0), "Y": (-20.0, 5.0)}
    straight = "STRAIGHT_FEED(10, 0, 0, 0, 0, 0)"
    assert check_canon(_canon(straight), limits) == []
    got = check_canon(_canon("SET_XY_ROTATION(90)", straight), limits)
    assert [(v.line, v.axis, v.side) for v in got] == [(10, "Y", "max")]
    assert got[0].value == pytest.approx(10.0)


def test_xy_rotation_applies_g92_before_rotation():
    limits = {"X": (-20.0, 20.0), "Y": (-1.0, 4.0), "Z": (-50.0, 50.0)}
    canon = _canon("SET_G92_OFFSET(5, 0, 0, 0, 0, 0)",
                   "SET_XY_ROTATION(90)",
                   "STRAIGHT_FEED(0, 0, 1, 0, 0, 0)")
    got = check_canon(canon, limits)
    assert [(v.line, v.axis, v.side) for v in got] == [(11, "Y", "max")]
    assert got[0].value == pytest.approx(5.0)


def test_xy_rotated_arc_checks_machine_space_extremum():
    limits = {"X": (-20.0, 20.0), "Y": (-20.0, 9.0)}
    canon = _canon("SET_XY_ROTATION(45)",
                   "STRAIGHT_TRAVERSE(10, 0, 0, 0, 0, 0)",
                   "ARC_FEED(0, 10, 0, 0, 1, 0)")
    got = check_canon(canon, limits)
    assert [(v.line, v.axis, v.side) for v in got] == [(11, "Y", "max")]
    assert got[0].value == pytest.approx(10.0)


def test_number_lines_keeps_file_line_numbers():
    text = "%\nG21\n\nN50 G0 Z20 (x)\n(komentarz)\n"
    assert number_lines(text).splitlines() == ["%", "N2 G21", "", "N4 G0 Z20 (x)",
                                               "N5 (komentarz)"]


@pytest.mark.linuxcnc
def test_g54_offset_reproduces_linuxcnc_error(tmp_path):  # offset -150 + G0 Z20
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    var = tmp_path / "t.var"
    var.write_text("5220\t1.0\n5221\t0.0\n5222\t0.0\n5223\t-150.0\n", encoding="utf-8")
    ngc = tmp_path / "p.ngc"
    ngc.write_text("G21 G90 G54\n(komentarz)\nG0 Z20\nM2\n", encoding="utf-8")
    got = check_ngc(ngc, SIM_INI, var, root)
    assert [(v.line, v.axis, v.side) for v in got] == [(3, "Z", "min")]
    assert got[0].value == pytest.approx(-130.0)
    var.write_text("5220\t1.0\n5223\t-50.0\n", encoding="utf-8")
    assert check_ngc(ngc, SIM_INI, var, root) == []
