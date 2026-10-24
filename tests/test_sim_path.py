# SPDX-License-Identifier: GPL-2.0-or-later
"""Ścieżka z programu: MoveList, łuki z błędem cięciwy, interpreter podzbioru (sesja 051).

Model-Author: Claude · 2026-10-24. Porównanie z interpreterem LinuxCNC: test_rs274_matches_subset
(marker linuxcnc, job CI). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest
from linumert_sim.path import (
    CHORD_TOL,
    KIND_ARC,
    KIND_FEED,
    KIND_RAPID,
    InterpreterUnavailable,
    arc_points,
    chord_count,
    load_path,
    parse_rs274,
    parse_subset,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = sorted((ROOT / "tests/golden").glob("*.ngc"))
_XYZ = re.compile(r"([XYZ])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def _chord_error(pts: np.ndarray, center, radius: float, axes=(0, 1)) -> float:
    mid = (pts[:-1] + pts[1:]) / 2.0
    d = np.hypot(mid[:, axes[0]] - center[0], mid[:, axes[1]] - center[1])
    return float(np.max(np.abs(radius - d)))


def test_ten_programs_cover_m3_generators():
    assert len(GOLDEN) >= 10
    text = "".join(p.read_text(encoding="utf-8") for p in GOLDEN)
    for code in ("G2", "G3", "G81", "G73", "G98", "G42.1"):
        assert code in text, code


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.stem)
def test_golden_program_gives_continuous_path(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    ml = parse_subset(lines)
    assert len(ml) > 0 and ml.source == "subset"
    assert ml.start.dtype == np.float32 and ml.line.dtype == np.int32
    assert ml.kind.dtype == np.int8 and ml.feed.dtype == np.float32
    # Ciągłość: koniec odcinka = początek następnego.
    assert np.allclose(ml.start[1:], ml.end[:-1], atol=1e-4)
    # Każda linia z ruchem to linia z G/X/Y/Z w pliku; G0 bez posuwu, G1/łuk z posuwem.
    for n in ml.lines():
        assert re.search(r"[GXYZ]", lines[n - 1].upper()), (n, lines[n - 1])
    assert np.all(ml.feed[ml.kind == KIND_RAPID] == 0)
    assert np.all(ml.feed[ml.kind != KIND_RAPID] > 0)
    # Koniec linii z pełnym XYZ (G90) = współrzędne z tekstu.
    for n in ml.lines():
        words = dict(_XYZ.findall(lines[n - 1].upper()))
        if len(words) == 3 and "G8" not in lines[n - 1] and "G73" not in lines[n - 1]:
            end = ml.end[ml.segments_of(n)[-1]]
            assert np.allclose(end, [float(words[a]) for a in "XYZ"], atol=1e-4), n


@pytest.mark.parametrize("path", GOLDEN, ids=lambda p: p.stem)
def test_golden_arcs_within_chord_tolerance(path):
    ml = parse_subset(path.read_text(encoding="utf-8"))
    for n in np.unique(ml.line[ml.kind == KIND_ARC]):
        idx = ml.segments_of(n)
        pts = np.vstack((ml.start[idx[:1]], ml.end[idx])).astype(float)
        # Środek okręgu przez trzy punkty łuku (XY).
        a, b, c = pts[0, :2], pts[len(pts) // 2, :2], pts[-1, :2]
        if len(pts) < 3:
            continue
        d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-9:
            continue
        ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
        uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
        r = float(np.hypot(*(a - (ux, uy))))
        assert _chord_error(pts, (ux, uy), r) <= CHORD_TOL + 1e-3, n


@pytest.mark.parametrize("radius,sweep", [(0.5, math.pi), (5, math.tau), (60, 2.0),
                                          (300, 0.3), (0.005, 1.0)])
def test_chord_error_bound(radius, sweep):
    pts = arc_points((radius, 0, 0), (radius * math.cos(sweep), radius * math.sin(sweep), -1),
                     (0, 0), 1)
    assert len(pts) - 1 == chord_count(radius, sweep)
    if radius > CHORD_TOL:
        assert _chord_error(pts, (0, 0), radius) <= CHORD_TOL + 1e-9
    assert np.allclose(pts[-1], (radius * math.cos(sweep), radius * math.sin(sweep), -1))
    assert pts[len(pts) // 2, 2] == pytest.approx(-0.5, abs=1.0 / len(pts))  # linia śrubowa


def test_arc_r_word_short_and_long():
    short = parse_subset("G21 G90\nG0 X0 Y0 Z0\nG2 X10 Y0 R5 F100\n")
    long = parse_subset("G21 G90\nG0 X0 Y0 Z0\nG2 X10 Y0 R-6 F100\n")
    ys = short.end[short.kind == KIND_ARC][:, 1]
    assert ys.max() == pytest.approx(5, abs=0.01)          # półokrąg CW nad osią X
    assert short.length(KIND_ARC) == pytest.approx(math.pi * 5, rel=2e-3)
    assert long.length(KIND_ARC) > math.pi * 6             # dłuższy łuk > półokręgu
    with pytest.raises(ValueError, match="promień"):
        parse_subset("G0 X0 Y0\nG2 X10 Y0 R2 F100\n")


def test_planes_and_full_circle():
    xz = parse_subset("G18 G0 X10 Y0 Z0\nG3 X10 Z0 I-10 K0 F200\n")   # pełny okrąg w XZ
    arc = xz.end[xz.kind == KIND_ARC]
    assert np.allclose(arc[:, 1], 0)
    assert xz.length(KIND_ARC) == pytest.approx(math.tau * 10, rel=2e-3)  # cięciwy krótsze od łuku
    assert arc[:, 2].min() == pytest.approx(-10, abs=0.01) and arc[:, 2].max() == pytest.approx(
        10, abs=0.01)
    # G3 w G18 = CCW patrząc od +Y: z (10, 0) najpierw w stronę -Z.
    assert arc[0, 2] < 0
    yz = parse_subset("G19 G0 X0 Y5 Z0\nG2 Y-5 Z0 J-5 K0 F200\n")
    assert yz.length(KIND_ARC) == pytest.approx(math.pi * 5, rel=2e-3)


def test_incremental_inch_tool_and_absolute_arc_centre():
    ml = parse_subset("G20 G91\nG0 X1 Y1\nT3 M6\nG1 Z-0.5 F10\nG21 G90 G90.1\n"
                      "G0 X35.4 Y25.4 Z0\nG3 X15.4 Y25.4 I25.4 J25.4 F100\nM2\nG0 X999\n")
    assert np.allclose(ml.end[0], (25.4, 25.4, 0))
    assert np.allclose(ml.end[1], (25.4, 25.4, -12.7)) and ml.feed[1] == pytest.approx(254)
    assert ml.tool[0] == 0 and ml.tool[1] == 3
    assert ml.length(KIND_ARC) == pytest.approx(math.pi * 10, rel=2e-3)
    assert ml.bounds()[1][0] < 999                         # po M2 nic


def test_drill_cycles_expand_like_linuxcnc():
    ml = parse_subset("G21 G90\nG0 X0 Y0 Z10\nG98 G81 X5 Y5 Z-3 R2 F100\nX15\nG80\n"
                      "G0 Z10\nG99 G83 X0 Y0 Z-5 R1 Q2 F50\nG80\n")
    l3 = ml.segments_of(3)
    assert [int(k) for k in ml.kind[l3]] == [KIND_RAPID, KIND_RAPID, KIND_FEED, KIND_RAPID]
    assert ml.end[l3[-1]][2] == pytest.approx(10)          # G98: do Z początkowego
    assert np.allclose(ml.end[ml.segments_of(4)[-1]], (15, 5, 10))
    l7 = ml.segments_of(7)
    feeds = ml.end[l7][ml.kind[l7] == KIND_FEED][:, 2]
    assert np.allclose(feeds, (-1, -3, -5))                # Q2 od R1
    assert ml.end[l7[-1]][2] == pytest.approx(1)           # G99: do R


def test_unsupported_features_are_noted_not_guessed():
    ml = parse_subset("o<sub1> sub\nG0 X100\no<sub1> endsub\nG0 X1 Y1\no<sub1> call\n"
                      "G41.1 D6\nG1 X2 F100\nG28\nG5.1 X1\n")
    assert np.allclose(ml.bounds()[1][:2], (2, 1))          # ciało sub pominięte
    notes = " ".join(ml.notes)
    assert "o-word call" in notes and "G41.1" in notes and "G28" in notes and "G5.1" in notes


def test_load_path_falls_back_to_subset(tmp_path):
    prog = tmp_path / "p.ngc"
    prog.write_text("G0 X1 Y2 Z3\nG1 X4 F100\n")
    try:
        import gcode  # type: ignore[import-not-found]  # noqa: F401
        expected = "rs274"
    except ImportError:
        expected = "subset"
        with pytest.raises(InterpreterUnavailable):
            load_path(prog, prefer="rs274")
    assert load_path(prog).source == expected
    assert load_path(prog, prefer="subset").source == "subset"
    with pytest.raises(ValueError):
        load_path(prog, prefer="inny")


@pytest.mark.linuxcnc
@pytest.mark.parametrize("path", [p for p in GOLDEN
                                  if not re.search(r"G4[12]", p.read_text())],
                         ids=lambda p: p.stem)
def test_rs274_matches_subset(path):
    """Interpreter podzbioru daje te same końce linii i długości co rs274 LinuxCNC."""
    pytest.importorskip("gcode")
    ref = parse_rs274(path)
    sub = parse_subset(path.read_text(encoding="utf-8"))
    assert ref.source == "rs274"
    assert sorted(ref.lines()) == sorted(sub.lines())
    for n in ref.lines():
        assert np.allclose(ref.end[ref.segments_of(n)[-1]], sub.end[sub.segments_of(n)[-1]],
                           atol=1e-3), n
    # Pierwszy ruch: rs274 nie zna pozycji startowej (odcinek zerowy), podzbiór startuje z 0,0,0.
    first = ref.line[0]
    rest_ref = ref.lengths[ref.line != first].sum()
    rest_sub = sub.lengths[sub.line != first].sum()
    assert rest_ref == pytest.approx(rest_sub, rel=1e-4)
    for kind in (KIND_RAPID, KIND_FEED, KIND_ARC):
        assert np.count_nonzero(ref.kind == kind) > 0 or np.count_nonzero(sub.kind == kind) == 0
