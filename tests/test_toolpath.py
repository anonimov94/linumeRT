"""Model ścieżki podglądu Classic × Neon: łuki, strefy, DTG, lokalizacja po motion_line.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from linumert.programs.toolpath import (
    INCH,
    PreviewCanon,
    Toolpath,
    arc_points,
    demo_toolpath,
    make_move,
)

ROOT = Path(__file__).resolve().parents[1]
DEMO_NGC = ROOT / "config/sim/nc_files/linumert_neon_demo.ngc"


def _line_path():
    return Toolpath([
        make_move(1, True, 0, [(0, 0, 0), (10, 0, 0)]),
        make_move(2, False, 600, [(10, 0, 0), (10, 5, 0)]),
        make_move(3, False, 600, [(10, 5, 0), (10, 5, 0)]),   # zerowy
        make_move(4, False, 600, [(10, 5, 0), (0, 5, 0)]),
    ])


def test_arc_direction_length_and_full_turns():
    ccw = arc_points((10, 0, 0), (0, 10, 0), (0, 0), 1)
    cw = arc_points((10, 0, 0), (0, 10, 0), (0, 0), -1)
    assert ccw[len(ccw) // 2][1] > 0 and ccw[len(ccw) // 2][0] > 0     # przez I ćwiartkę
    assert cw[len(cw) // 2][1] < 0                                     # przez III/IV ćwiartkę
    length = lambda p: np.linalg.norm(np.diff(p, axis=0), axis=1).sum()  # noqa: E731
    assert length(ccw) == pytest.approx(10 * math.pi / 2, rel=2e-3)
    assert length(cw) == pytest.approx(10 * 3 * math.pi / 2, rel=2e-3)
    full = arc_points((10, 0, 0), (10, 0, -3), (0, 0), -2)              # helisa, 2 obroty
    assert length(full[:, :2]) == pytest.approx(2 * 2 * math.pi * 10, rel=2e-3)
    assert full[-1] == pytest.approx((10, 0, -3))
    with pytest.raises(ValueError):
        arc_points((1, 0, 0), (0, 1, 0), (0, 0), 0)


def test_zones_seek_dtg_and_skip_zero_moves():
    tp = _line_path()
    assert [tp.zone(i, 1) for i in range(4)] == ["start", "mid", "mid", "end"]
    assert [tp.zone(i, 3) for i in range(4)] == ["start", "start", "start", "end"]
    assert tp.length == pytest.approx(25)
    assert tp.seek(12) == (1, pytest.approx(2))
    assert tp.dtg(1, 2) == pytest.approx(3)
    i, s = tp.seek(15)
    assert i == 3 and s == pytest.approx(0)          # ruch zerowy pominięty
    assert tp.seek(99) == (4, 0.0)
    assert tp.position(1, 2) == pytest.approx((10, 2, 0))
    assert tp.travelled(4, 0) == pytest.approx(25)


def test_locate_by_motion_line_and_geometry():
    tp = _line_path()
    i, s = tp.locate(2, (10.1, 3, 0))
    assert i == 1 and s == pytest.approx(3)
    # linia bez ruchu → następny ruch po niej
    assert tp.locate(3, (0, 0, 0))[0] in (2, 3)
    assert tp.locate(99, (0, 0, 0)) == (4, 0.0)
    # dwa ruchy w jednej linii (cykl): wybiera bliższy geometrycznie
    twin = Toolpath([make_move(7, False, 100, [(0, 0, 0), (0, 0, -5)]),
                     make_move(7, True, 0, [(0, 0, -5), (0, 0, 2)])])
    assert twin.locate(7, (0, 0, 1))[0] == 1
    assert twin.locate(7, (0, 0, -2), hint=0)[0] == 0


def test_preview_canon_collects_lines_inches_offsets_and_arcs():
    c = PreviewCanon()
    c.set_g5x_offset(1, 100 / INCH, 100 / INCH, -150 / INCH)
    c.set_feed_rate(1200 / INCH)
    c.next_line(SimpleNamespace(sequence_number=5))
    c.straight_traverse(0, 0, 5 / INCH, 0, 0, 0, 0, 0, 0)
    c.next_line(SimpleNamespace(sequence_number=6))
    c.straight_feed(10 / INCH, 0, 5 / INCH, 0, 0, 0, 0, 0, 0)
    c.next_line(SimpleNamespace(sequence_number=7))
    c.arc_feed(0, 10 / INCH, 0, 0, 1, 5 / INCH, 0, 0, 0, 0, 0, 0)
    c.comment("dowolne")                 # nieobsłużone wywołania są neutralne
    c.set_plane(2)
    c.next_line(SimpleNamespace(sequence_number=8))
    c.arc_feed(0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0)
    tp = c.toolpath(["a"] * 8)
    assert [m.line for m in tp.moves] == [5, 6, 7, 8]
    assert tp.moves[0].length == 0                       # start nieznany
    assert tp.moves[1].feed == pytest.approx(1200)
    assert tp.moves[1].end == pytest.approx((10, 0, 5))
    assert tp.moves[2].length == pytest.approx(10 * math.pi / 2, rel=2e-3)
    assert tp.offset == pytest.approx((100, 100, -150))
    assert tp.notes and "G18" in tp.notes[0]
    assert c.get_tool(3)[0] == 3 and len(c.get_tool(3)) == 14


def test_demo_program_matches_file_and_has_distinct_zones():
    tp = demo_toolpath()
    assert len(tp) > 60
    assert DEMO_NGC.read_text(encoding="utf-8").splitlines() == list(tp.source)
    for m in tp.moves:                                  # każda linia ruchu to G0..G3
        assert tp.source[m.line - 1].split()[0] in ("G0", "G1", "G2", "G3")
    lo, hi = tp.bounds()
    assert lo == pytest.approx((-20, -20, -14)) and hi[2] == pytest.approx(25)
    t = tp.seconds(6000)
    assert t[-1] > 60 and np.all(np.diff(t) >= 0)
