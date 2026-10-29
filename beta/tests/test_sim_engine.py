"""Symulacja HMI: profile narzędzi, materiał 2.5D, reguły kolizji i przeciążenia (2026-10-19).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from linumert.programs.stock import parse_stock_line
from linumert_sim.cutter import make_cutter
from linumert_sim.engine import Sample, SimEngine
from linumert_sim.machine import Body, Machine, load_machine
from linumert_sim.placement import read_var_offsets, stock_bounds
from linumert_sim.tooldata import cutters, open_db
from linumert_sim.zmap import StockMap

ROOT = Path(__file__).resolve().parents[1]
SIM_MACHINE = ROOT / "config/sim/linumert_xyz/machine.yaml"


# ---- profile narzędzi -------------------------------------------------------------------------

def test_profiles():
    r = np.array([0.0, 2.0, 4.0, 5.0, 6.0])
    flat = make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20})
    assert list(flat.lower(r)[:4]) == [0, 0, 0, 0] and math.isinf(flat.lower(r)[4])
    ball = make_cutter(2, 80, 10, "ball", {"d": 10, "l": 40})
    assert ball.lower(np.array([0.0]))[0] == 0 and ball.lower(np.array([5.0]))[0] == \
        pytest.approx(5.0)
    bull = make_cutter(3, 80, 12, "bull", {"d": 12, "l": 40, "corner_radius": 1})
    assert bull.lower(np.array([4.0]))[0] == 0 and bull.lower(np.array([6.0]))[0] == \
        pytest.approx(1.0)
    cham = make_cutter(4, 80, 10, "chamfer", {"d": 10, "angle": 90})
    assert cham.lower(np.array([5.0]))[0] == pytest.approx(5.0)
    drill = make_cutter(5, 100, 6, "drill_118", {"d": 6, "l": 60})
    assert drill.lower(np.array([3.0]))[0] == pytest.approx(3 / math.tan(math.radians(59)))
    tslot = make_cutter(6, 80, 20, "tslot", {"d": 20, "width": 4, "neck_d": 8, "neck_l": 10})
    assert tslot.undercut and tslot.neck_r == 4 and tslot.cut_top == 4


def test_wear_and_substitute():
    c = make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20, "d_wear": -0.4})
    assert c.diameter == pytest.approx(9.6)
    sub = make_cutter(7, 60, 8, None, {})
    assert sub.substitute and sub.diameter == 8


# ---- materiał ---------------------------------------------------------------------------------

def _stock():
    return StockMap("BOX", 0, 0, 100, 100, -30, 0, cell=0.25)


def test_plunge_volume():
    s = _stock()
    flat = make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20})
    v0 = s.volume()
    res = s.cut(flat, (50, 50, 5), (50, 50, -5))
    assert res.removed == pytest.approx(math.pi * 25 * 5, rel=0.05)
    assert s.volume() == pytest.approx(v0 - res.removed, rel=1e-4)
    assert not res.parts


def test_slot_and_ball_groove():
    s = _stock()
    flat = make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20})
    res = s.cut(flat, (20, 50, -2), (80, 50, -2))
    assert res.removed == pytest.approx(60 * 10 * 2 + math.pi * 25 * 2 / 2, rel=0.06)
    ball = make_cutter(2, 80, 10, "ball", {"d": 10, "l": 40})
    s2 = _stock()
    s2.cut(ball, (20, 30, -5), (80, 30, -5))
    iy = int(30 / s2.cell)
    row = s2.h[iy, int(50 / s2.cell)]
    assert row == pytest.approx(-5, abs=0.15)  # dno rowka kulowego
    edge = s2.h[int(34 / s2.cell), int(50 / s2.cell)]
    assert -5 < edge < 0  # zbocze kuliste


def test_cylinder_stock_mask():
    s = StockMap("CYL", -30, -30, 30, 30, -20, 0, cell=0.5)
    assert np.isinf(s.h[0, 0]) and s.h[60, 60] == 0
    assert s.volume() == pytest.approx(math.pi * 900 * 20, rel=0.02)


def test_neck_in_material():
    s = _stock()
    flat = make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 10})
    assert not s.cut(flat, (50, 50, 1), (50, 50, -15)).parts  # wgłębianie: szyjka w otworze
    res = s.cut(flat, (-10, 20, -15), (30, 20, -15))  # bokiem głębiej niż ostrze
    assert "szyjka" in res.parts


# ---- reguły -----------------------------------------------------------------------------------

def _engine(machine=None):
    e = SimEngine(machine)
    e.set_stock(StockMap("BOX", 0, 0, 100, 100, -30, 0, cell=0.5), "aluminium")
    e.set_tools({1: make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20,
                                                     "max_rpm": 20000}),
                 2: make_cutter(2, 80, 6, "tap", {"d": 6, "l": 40, "pitch": 1}),
                 3: make_cutter(3, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20,
                                                     "hand": -1})})
    return e


def _run(e, points, tool=1, rpm=10000.0, motion="feed", dt=0.01):
    out = []
    for i, p in enumerate(points):
        nose = (p[0], p[1], p[2] + e.tools[tool].gauge)
        out += e.step(Sample(i * dt, nose, tool, rpm, motion, 10 + i))
    return out


def _line(a, b, n=40):
    return [tuple(a[k] + (b[k] - a[k]) * i / n for k in range(3)) for i in range(n + 1)]


def test_normal_cut_no_events():
    e = _engine()
    ev = _run(e, _line((20, 50, 5), (20, 50, -1)) + _line((20, 50, -1), (80, 50, -1), 200))
    assert [x.code for x in ev] == []
    assert e.stock.volume() < 100 * 100 * 30


def test_k301_no_spindle():
    ev = _run(_engine(), _line((20, 50, 5), (20, 50, -1)), rpm=0)
    assert [x.code for x in ev] == ["K-301"] and ev[0].stop


def test_k302_rapid():
    ev = _run(_engine(), _line((20, 50, 5), (20, 50, -1)), motion="rapid")
    assert [x.code for x in ev] == ["K-302"]


def test_k308_wrong_direction_and_tap_both_ways():
    assert [x.code for x in _run(_engine(), _line((20, 50, 5), (20, 50, -1)), rpm=-8000)] \
        == ["K-308"]
    assert [x.code for x in _run(_engine(), _line((20, 50, 5), (20, 50, -1)), tool=3,
                                 rpm=-8000)] == []
    tap = _engine()
    # posuw = obroty × skok (300 obr/min × 1 mm = 5 mm/s)
    assert [x.code for x in _run(tap, _line((20, 50, 5), (20, 50, -6)), tool=2, rpm=300,
                                 dt=0.055)] == []
    assert [x.code for x in _run(tap, _line((20, 50, -6), (20, 50, 5)), tool=2, rpm=-300,
                                 dt=0.055)] == []


def test_k303_neck():
    ev = _run(_engine(), _line((-10, 50, -25), (30, 50, -25), 120))
    assert "K-303" in [x.code for x in ev]


def test_k309_max_rpm():
    ev = _run(_engine(), [(200, 200, 50)], rpm=24000)
    assert [x.code for x in ev] == ["K-309"]


def _table_machine():
    m = Machine(name="test")
    m.bodies = [Body("stol", "box", "table", (300, 300, 40), (50, 50, -50)),
                Body("docisk", "box", "fixture", (10, 20, 10), (-10, 50, -25)),
                Body("wrzeciono", "cylinder", "spindle", (80, 150), (0, 0, 75))]
    return m


def test_k305_table_with_and_without_spindle():
    for rpm in (0.0, 10000.0):
        e = _engine(_table_machine())
        e.set_stock(None)
        ev = _run(e, _line((150, 150, -20), (150, 150, -35)), rpm=rpm)
        assert [x.code for x in ev] == ["K-305"]
        assert ev[0].pair == ("narzedzie", "stol")


def test_k304_fixture_and_spindle_body():
    e = _engine(_table_machine())
    e.set_stock(None)
    ev = _run(e, _line((-40, 50, -25), (-10, 50, -25)))
    assert ev and ev[0].code == "K-304"
    # nos wrzeciona schodzi na stół (narzędzie krótkie): wrzeciono – stół
    e2 = _engine(_table_machine())
    e2.set_stock(None)
    e2.tools[1] = make_cutter(1, 5, 4, "flat", {"d": 4, "l": 3})
    ev2 = _run(e2, _line((150, 150, 0), (150, 150, -45)))
    assert ("wrzeciono", "stol") in [x.pair for x in ev2]


def test_k306_k307_overload():
    m = _table_machine()
    m.spindle_curve = [(0.0, 0.05), (3000.0, 0.05)]
    m.axis_force = {"X": 10.0, "Y": 10.0, "Z": 10.0}
    e = _engine(m)
    e.set_stock(StockMap("BOX", 0, 0, 100, 100, -30, 0, cell=0.5), "stal")
    ev = _run(e, _line((20, 50, -8), (80, 50, -8), 100), rpm=3000, dt=0.01)
    codes = {x.code for x in ev}
    assert {"K-306", "K-307"} <= codes and all(x.stop for x in ev)
    assert e.load.power > 0


def test_events_once_per_entry():
    ev = _run(_engine(), _line((20, 50, 5), (20, 50, -1)) + _line((20, 50, -1), (60, 50, -1)),
              rpm=0)
    assert [x.code for x in ev] == ["K-301"]


# ---- przygotówka, model maszyny, narzędzia ----------------------------------------------------

def test_stock_bounds_origins():
    s = parse_stock_line(";@STOCK BOX X150 Y100 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=1")
    assert stock_bounds(s, (100, 100, -150)) == (100, 100, 250, 200, -179, -149)
    c = parse_stock_line(";@STOCK CYL D60 H40 ORIGIN=BOTTOM_CENTER")
    assert stock_bounds(c, (0, 0, 0)) == (-30, -30, 30, 30, 0, 40)
    s2 = parse_stock_line(";@STOCK BOX X50 Y40 Z10 ORIGIN=TOP_BACK_RIGHT")
    assert stock_bounds(s2, (0, 0, 0)) == (-50, -40, 0, 0, -10, 0)


def test_var_offsets(tmp_path):
    var = tmp_path / "x.var"
    var.write_text("5221\t100.0\n5222\t100.0\n5223\t-150.0\n5241\t1\n")
    off = read_var_offsets(var)
    assert off["G54"] == (100.0, 100.0, -150.0) and off["G55"] == (1.0, 0.0, 0.0)


def test_sim_machine_model():
    m = load_machine(SIM_MACHINE)
    names = {b.name for b in m.bodies}
    assert {"stol", "wrzeciono"} <= names
    assert m.axis_force["Y"] > m.axis_force["X"] > 500  # portal: dwa napędy
    assert 0.5 < m.spindle_torque_limit(12000) < 3.0


def test_tool_seed_db(tmp_path):
    ini = tmp_path / "m.ini"
    seed = ROOT / "config/sim/linumert_xyz/tools_seed.yaml"
    ini.write_text(f"[LINUMERT]\nTOOL_DB = tools.db\nTOOL_SEED = {seed}\n"
                   "[EMCIO]\nTOOL_TABLE = tool.tbl\n")
    db, tbl = open_db(ini)
    tools = {t.number: t for t in db.tools()}
    kinds = {t.type for t in tools.values()}
    assert {"flat", "ball", "bull", "chamfer", "drill_118", "face_mill", "tslot", "lollipop",
            "tap"} <= kinds
    assert tbl.is_file() and "T1 " in tbl.read_text()
    cs = cutters(tools, [(n, t.offsets["Z"], t.diameter or 0) for n, t in tools.items()])
    assert all(c.gauge > c.stickout >= c.cut_top > 0 for c in cs.values())
    assert any(c.hand == -1 for c in cs.values())


def test_sample_programs_stock_lines():
    from linumert_sim.placement import find_stock_line

    for path in sorted((ROOT / "config/sim/nc_files").glob("*.ngc")):
        line = find_stock_line(path)
        assert line, path.name
        parse_stock_line(line)


def test_segment_end_of_feed_is_not_rapid():
    """Koniec G1 w materiale, następna próbka już G0 (odjazd): bez K-302."""
    e = _engine()
    pts = _line((20, 50, 5), (20, 50, -1))
    out = []
    for i, p in enumerate(pts):
        motion = "rapid" if i == len(pts) - 1 else "feed"
        out += e.step(Sample(i * 0.01, (p[0], p[1], p[2] + 80), 1, 10000.0, motion, i))
    assert [x.code for x in out] == []


def test_overload_causes_clear_after_spindle_stops():
    engine = SimEngine()
    engine._active.update({("K-306",), ("K-307", "X")})
    engine.step(Sample(0, (0, 0, 0)))
    assert not engine._active


def test_stock_reset_restores_material_and_discards_previous_swept_move():
    engine = SimEngine()
    engine.set_stock(_stock())
    tool = make_cutter(1, 80, 10, "flat", {"d": 10, "l": 40, "flute_length": 20})
    engine.set_tools({1: tool})
    original = engine.stock.volume()
    engine.step(Sample(0, (30, 50, 85), tool=1, rpm=1000))
    engine.step(Sample(0.1, (50, 50, 75), tool=1, rpm=1000))
    assert engine.stock.volume() < original
    engine.reset_stock()
    assert engine.stock.volume() == original
    assert not engine._active and not engine.path and engine._prev is None
    engine.step(Sample(0.2, (200, 200, 100), tool=1, rpm=0))
    assert engine.stock.volume() == original  # brak starego odcinka do nowego HOME


# ---- eksport STL (sesja 059) --------------------------------------------------------------------

def _signed_volume(tris):
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    return float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c)))) / 6


def test_stl_closed_solid_matches_volume(tmp_path):
    from linumert_sim.stl import mesh, write_stl

    s = StockMap("BOX", 0, 0, 40, 30, -10, 0, cell=1.0)
    flat = make_cutter(1, 80, 8, "flat", {"d": 8, "l": 40, "flute_length": 20})
    s.cut(flat, (10, 15, -3), (30, 15, -3))
    tris = mesh(s)
    assert _signed_volume(tris) == pytest.approx(s.volume(), rel=1e-6)
    # szczelność: każda krawędź skierowana ma parę przeciwną
    edges = {}
    for t in np.round(tris, 6):
        for i in range(3):
            key = (tuple(t[i]), tuple(t[(i + 1) % 3]))
            edges[key] = edges.get(key, 0) + 1
    assert all(edges.get((b, a), 0) == n for (a, b), n in edges.items())
    path = tmp_path / "m.stl"
    n = write_stl(s, path)
    assert path.stat().st_size == 84 + 50 * n
