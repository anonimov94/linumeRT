"""Sesja 043: rowki, czopy i kontur — geometria materiału, walidacja, golden, LinuxCNC.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Pliki golden: tests/golden/contours_<nazwa>.ngc (odświeżenie: LINUMERT_UPDATE_GOLDEN=1).
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path

import numpy as np
import pytest
from linumert.generators.contours import (
    Contour,
    SlotArc,
    SlotLinear,
    StudCircle,
    StudRect,
    parse_segments,
    register,
)
from linumert.generators.registry import GeneratorRegistry

GOLDEN = Path(__file__).with_name("golden")
CASES = {
    "slot_linear": (SlotLinear, {"x1": 10, "y1": 10, "x2": 40, "y2": 25, "width": 12,
                                 "tool_d": 6, "depth": 2, "step_down": 1, "entry": "ramp"}),
    "slot_arc": (SlotArc, {"cx": 30, "cy": 5, "radius": 20, "start_angle": 30, "sweep": 100,
                           "width": 10, "tool_d": 6, "depth": 2}),
    "stud_rect": (StudRect, {"cx": 30, "cy": 20, "width": 24, "height": 14, "corner_radius": 4,
                             "tool_d": 6, "depth": 2, "margin": 5}),
    "stud_circle": (StudCircle, {"cx": 25, "cy": 25, "diameter": 20, "tool_d": 6,
                                 "depth": 2, "margin": 5, "milling": "conventional"}),
    "contour": (Contour, {"segments": "L 0,0 40,0; A 40,0 40,20 40,10 CCW; L 40,20 0,20; "
                                      "L 0,20 0,0", "tool_d": 6, "depth": 2,
                          "compensation": "right", "lead": 5}),
}


def _values(name):
    cls, params = CASES[name]
    gen = cls()
    assert gen.validate(params) == []
    return gen, gen.normalize(params)[0]


def _cut_program(stock, tool, lines):
    pos = (0.0, 0.0, 5.0)
    for line in lines:
        if not line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
            continue
        words = {k: float(v) for k, v in re.findall(r"([XYZIJ])(-?[0-9.]+)", line)}
        end = tuple(words.get(k, pos[i]) for i, k in enumerate("XYZ"))
        if line.startswith(("G2 ", "G3 ")):
            center = (pos[0] + words["I"], pos[1] + words["J"])
            radius = math.hypot(words["I"], words["J"])
            a = math.atan2(pos[1] - center[1], pos[0] - center[0])
            b = math.atan2(end[1] - center[1], end[0] - center[0])
            sign = 1 if line.startswith("G3 ") else -1
            sweep = ((sign * (b - a)) % math.tau or math.tau) * sign
            start = pos
            for i in range(1, 129):
                t = i / 128
                point = (center[0] + radius * math.cos(a + sweep * t),
                         center[1] + radius * math.sin(a + sweep * t),
                         start[2] + (end[2] - start[2]) * t)
                stock.cut(tool, pos, point)
                pos = point
        else:
            result = stock.cut(tool, pos, end)
            if line.startswith("G0 "):
                assert result.removed == 0, f"G0 w materiale: {line}"
        pos = end


def _material(name, size=(60, 50)):
    from linumert_sim.cutter import make_cutter
    from linumert_sim.zmap import StockMap

    gen, v = _values(name)
    stock = StockMap("BOX", 0, 0, size[0], size[1], -10, 0, cell=0.25)
    tool = make_cutter(1, 80, 6, "flat", {"d": 6, "l": 40, "flute_length": 20})
    _cut_program(stock, tool, gen.generate(v))
    xx, yy = np.meshgrid(stock.xs, stock.ys)
    return stock.h, xx, yy


def _assert_cut(h, distance, cut_until, keep_from, depth=-2.0, tol=0.4):
    """Bliżej niż cut_until − tol: wycięte do `depth`; dalej niż keep_from + tol: nietknięte."""
    inside = distance < cut_until - tol
    outside = distance > keep_from + tol
    assert inside.any() and outside.any()
    assert np.allclose(h[inside], depth, atol=0.02)
    assert np.allclose(h[outside], 0.0)


def test_all_generators_valid_deterministic_and_registered():
    registry = GeneratorRegistry()
    register(registry)
    register(registry)                                     # bez dublowania
    assert set(registry.names()) == set(CASES)
    for name in CASES:
        gen, v = _values(name)
        lines = gen.generate(v)
        assert lines == gen.generate(v)
        assert lines[1] == "G17 G90 G91.1 G94 G40 G80" and lines[-1] == "G0 Z5"
        assert gen.preview_2d(v) and all(len(p) >= 2 for p in gen.preview_2d(v))
        assert all(ord(c) < 128 for line in lines for c in line)


def test_linear_slot_cuts_exact_width_and_ramps_without_plunge():
    h, xx, yy = _material("slot_linear")
    p1, p2 = np.array((10.0, 10.0)), np.array((40.0, 25.0))
    d = p2 - p1
    t = np.clip(((xx - p1[0]) * d[0] + (yy - p1[1]) * d[1]) / (d @ d), 0, 1)
    dist = np.hypot(xx - (p1[0] + t * d[0]), yy - (p1[1] + t * d[1]))
    _assert_cut(h, dist, 6, 6)
    gen, v = _values("slot_linear")
    pos = (0.0, 0.0, 5.0)
    for line in gen.generate(v):
        words = dict(re.findall(r"([XYZ])(-?[0-9.]+)", line))
        end = tuple(float(words.get(k, pos[i])) for i, k in enumerate("XYZ"))
        if line.startswith("G1") and end[2] < min(0.0, pos[2]) - 1e-9:
            assert end[:2] != pos[:2], f"zagłębienie pionowe w materiał: {line}"
        pos = end


def test_arc_slot_follows_arc_and_never_cuts_chord():
    h, xx, yy = _material("slot_arc")
    rho = np.hypot(xx - 30, yy - 5)
    ang = (np.degrees(np.arctan2(yy - 5, xx - 30)) - 30) % 360
    on_arc = ang <= 100
    ends = [np.hypot(xx - (30 + 20 * math.cos(math.radians(a))),
                     yy - (5 + 20 * math.sin(math.radians(a)))) for a in (30, 130)]
    dist = np.where(on_arc, np.abs(rho - 20), np.minimum(*ends))
    _assert_cut(h, dist, 5, 5)


def test_rect_stud_stays_intact_and_margin_is_cleared():
    h, xx, yy = _material("stud_rect")
    qx, qy = np.abs(xx - 30) - (12 - 4), np.abs(yy - 20) - (7 - 4)
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
    wall = outside - 4                                        # odległość od ściany czopu
    assert np.allclose(h[wall < -0.4], 0.0)                   # czop nietknięty
    band = (wall > 0.4) & (wall < 5 + 6 - 0.4)                # margines + D frezu
    assert band.any() and np.allclose(h[band], -2.0, atol=0.02)


def test_circle_stud_conventional_milling_and_clearing():
    h, xx, yy = _material("stud_circle")
    wall = np.hypot(xx - 25, yy - 25) - 10
    assert np.allclose(h[wall < -0.4], 0.0)
    band = (wall > 0.4) & (wall < 11 - 0.4)
    assert np.allclose(h[band], -2.0, atol=0.02)
    gen, v = _values("stud_circle")
    assert any(line.startswith("G3 ") for line in gen.generate(v))     # przeciwbieżnie = CCW
    climb = gen.generate({**v, "milling": "climb"})
    assert any(line.startswith("G2 ") for line in climb)


def test_contour_compensation_lead_in_and_out():
    gen, v = _values("contour")
    lines = gen.generate(v)
    comp = lines.index("G42.1 D6")
    assert lines[comp - 1] == "G1 Z-1 F100" and lines[comp - 2] == "G0 X-5 Y0"    # warstwa 1
    assert lines[comp + 1] == "G1 X0 Y0 F400"                  # styczny dojazd od -X
    assert "G3 X40 Y20 I0 J10 F400" in lines
    assert lines[lines.index("G40") - 1] == "G1 X0 Y-5 F400"    # styczny odjazd w kierunku -Y
    none = gen.generate({**v, "compensation": "none"})
    assert not any(line.startswith(("G41", "G42")) for line in none) and "G40" not in none[3:]


@pytest.mark.parametrize("text,code,needle", [
    ("L 0,0 10,0; L 10,2 20,0", "P-5010", "segmencie 2 (przerwa 2 mm)"),
    ("L 0,0 10,0; A 10,0 20,0 14,1 CW", "P-5003", "promień łuku segmentu 2"),
    ("L 0,0 10,0; X 1,2", "P-5015", "segment 2"),
    ("L 0,0 0,0", "P-5003", "długość segmentu 1"),
])
def test_contour_validation_reports_segment(text, code, needle):
    issues = Contour().validate({"segments": text, "tool_d": 6, "depth": 1})
    assert any(i.code == code and needle in i.message() for i in issues), \
        [i.message() for i in issues]


@pytest.mark.parametrize("cls,params,field", [
    (Contour, {"segments": "L 0,0 10,0", "compensation": "left", "lead": 3}, "lead"),
    (SlotLinear, {"x2": 20, "width": 5}, "tool_d"),
    (SlotLinear, {"x2": 0, "width": 8}, "x2"),
    (SlotArc, {"radius": 2, "sweep": 90, "width": 12}, "radius"),
    (StudRect, {"width": 10, "height": 10, "corner_radius": 6}, "corner_radius"),
    (StudCircle, {"diameter": 10, "safe_z": -1}, "safe_z"),
])
def test_invalid_geometry_is_rejected(cls, params, field):
    issues = cls().validate({"tool_d": 6, "depth": 1, **params})
    assert any(i.field == field for i in issues), [(i.field, i.message()) for i in issues]


def test_parse_segments_formats():
    segs = parse_segments("L 0,0 1,0\nA 1,0 2,1 1,1 ccw; l -1.5,.5 2,3")
    assert segs[1] == ((1.0, 0.0), (2.0, 1.0), (1.0, 1.0), True)
    assert segs[2][0] == (-1.5, 0.5)


@pytest.mark.parametrize("name", sorted(CASES))
def test_golden(name):
    cls, params = CASES[name]
    program = cls().generate_ngc(params, f"{name}.ngc")
    path = GOLDEN / f"contours_{name}.ngc"
    if os.environ.get("LINUMERT_UPDATE_GOLDEN") == "1":
        path.write_text(program)
    assert program == path.read_text()


@pytest.mark.linuxcnc
@pytest.mark.parametrize("name,patch", [(n, {}) for n in sorted(CASES)] +
                         [("contour", {"compensation": "left"}),
                          ("contour", {"compensation": "none", "lead": 0})])
def test_programs_accepted_by_linuxcnc_interpreter(tmp_path, name, patch):
    from linumert.programs.linuxcnc_check import check_with_linuxcnc

    cls, params = CASES[name]
    path = tmp_path / f"{name}.ngc"
    # Odziedziczone tryby nie mogą zmienić ścieżki (generator ustawia G17 G90 G91.1 G94 G40).
    path.write_text("G18 G91 G90.1 G93\n" + cls().generate_ngc({**params, **patch}, path.name))
    result = check_with_linuxcnc(path)
    assert result.ok, result.messages
