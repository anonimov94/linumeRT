"""Biblioteka natywna (core/native) kontra ścieżka referencyjna w Pythonie, te same dane.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-05

Tolerancje (jawne):
- wysokości frezu kulistego i program płaskorzeźby: identyczne (porównanie `==`);
- mapa przygotówki po przejazdach: identyczna bitowo, części w materiale i pierwszy kontakt
  identyczne; objętość usunięta: błąd względny ≤ 1e-6 (numpy sumuje float32, C w double);
- symulacja offline: zdarzenia i czasy identyczne, objętość jak wyżej (± 0,1 mm³ zaokrąglenia).
Biblioteka budowana do katalogu tymczasowego; bez kompilatora test jest pomijany, w CI
(zmienna CI) brak biblioteki to błąd.
"""

from __future__ import annotations

import math
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from linumert import native
from linumert.generators.relief import (
    ReliefSettings,
    ball_tip_height,
    ball_tip_heights,
    plan_relief,
)
from linumert.programs.stl_section import Mesh
from linumert_sim.cutter import make_cutter
from linumert_sim.offline import OfflineJob, simulate
from linumert_sim.zmap import StockMap

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    try:
        path = native.build_library(tmp_path_factory.mktemp("native"))
        return native.load_library(path)
    except native.NativeUnavailable as error:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"biblioteka natywna niedostępna: {error}")


def wave(n=12, size=10.0, seed=0):
    rng = np.random.default_rng(seed)
    g = np.linspace(0.0, size, n + 1)
    xx, yy = np.meshgrid(g, g)
    zz = np.sin(xx / 2) * np.cos(yy / 3) + rng.normal(0, 0.05, xx.shape)
    p = np.stack([xx, yy, zz], axis=-1)
    a, b, c, d = p[:-1, :-1], p[:-1, 1:], p[1:, 1:], p[1:, :-1]
    return np.concatenate([np.stack([a, b, c], axis=2).reshape(-1, 3, 3),
                           np.stack([a, c, d], axis=2).reshape(-1, 3, 3)])


def odd_shapes():
    """Pionowa ściana, pochyła krawędź, trójkąt zdegenerowany w XY, osobna powłoka."""
    return np.array([[(0, -2, 0), (0, 2, 0), (0, 0, 3)],
                     [(0, -2, -2), (0, 2, 2), (0, -2, -3)],
                     [(1, 1, 0), (1, 1, 2), (1, 1, 1)],
                     [(-3, -3, 1), (3, -3, 1), (0, 3, 1.5)]], dtype=float)


@pytest.mark.parametrize("radius", [0.05, 0.5, 1.6, 4.0])
def test_relief_heights_identical_to_reference(lib, radius):
    tris = np.concatenate([wave(), odd_shapes()])
    rng = np.random.default_rng(int(radius * 100))
    xy = np.column_stack((rng.uniform(-4, 14, 400), rng.uniform(-4, 14, 400)))
    reference = np.array([ball_tip_height(tris, x, y, radius) for x, y in xy])
    assert np.isinf(reference).any() and np.isfinite(reference).any()
    np.testing.assert_array_equal(native.relief_heights(lib, tris, xy, radius), reference)
    np.testing.assert_array_equal(ball_tip_heights(tris, xy, radius), reference)


def test_plan_relief_same_with_library_numpy_and_point_reference(lib):
    mesh = Mesh(wave(n=8, size=6.0, seed=3))
    settings = ReliefSettings(tool_diameter=1.0, sample_step=0.2, stepover=0.4, safe_z=5.0)
    with native.override(lib):
        fast = plan_relief(mesh, settings)
    with native.override(None):
        slow = plan_relief(mesh, settings)
    assert fast == slow
    # program z punktu: każdy z ball_tip_height jak przed przyspieszeniem
    margin = float(np.diff(np.unique(np.round(np.linspace(0, 6, 31), 4))).max())
    for row in slow.rows[::4]:
        for x, y, z in row[::7]:
            h = ball_tip_height(mesh.triangles, x, y, 0.5 + margin) + margin
            assert z == math.ceil(max(float(mesh.triangles[:, :, 2].min()), h) * 10000) / 10000


CUTTERS = [
    make_cutter(1, 40.0, 6.0, "flat"),
    make_cutter(2, 45.0, 6.0, "ball"),
    make_cutter(3, 50.0, 8.0, "bull", {"corner_radius": 1.0}),
    make_cutter(4, 55.0, 6.0, "chamfer", {"angle": 90}),
    make_cutter(5, 60.0, 10.0, "tslot", {"width": 3, "neck_d": 4}),
    make_cutter(6, 48.0, 5.0, None),            # walec zastępczy (K-320)
]


def _maps():
    a = StockMap("CYL", 0, 0, 40, 30, -10, 0, cell=0.5)
    b = StockMap("CYL", 0, 0, 40, 30, -10, 0, cell=0.5)
    return a, b


@pytest.mark.parametrize("below", [False, True], ids=["czesci-nad", "czesc-pod-ostrzem"])
@pytest.mark.parametrize("cutter", CUTTERS, ids=lambda c: c.kind)
def test_zmap_cut_identical_to_python(lib, cutter, below):
    ref, fast = _maps()
    rng = np.random.default_rng(cutter.number)
    spindle = [("wrzeciono", 30.0, cutter.gauge, cutter.gauge + 80)]
    if below:   # część od z < 0: C przegląda całe okno jak Python (wczesne wyjście)
        spindle.append(("kolnierz", 2.0, -1.0, 5.0))
    points = [(rng.uniform(-5, 45), rng.uniform(-5, 35), rng.uniform(-12, 3)) for _ in range(30)]
    points[10] = points[9]                                    # przejazd zerowy
    points[20] = (points[19][0], points[19][1], -cutter.stickout - 2)  # oprawka w materiale
    for p0, p1 in zip(points[:-1], points[1:], strict=True):
        with native.override(None):
            a = ref.cut(cutter, p0, p1, spindle)
        with native.override(lib):
            b = fast.cut(cutter, p0, p1, spindle)
        assert b.parts == a.parts
        assert b.contact_at == a.contact_at
        assert b.removed == pytest.approx(a.removed, rel=1e-6, abs=1e-9)
        assert fast.version == ref.version
    np.testing.assert_array_equal(fast.h, ref.h)
    assert ref.volume() < StockMap("CYL", 0, 0, 40, 30, -10, 0, cell=0.5).volume()


def _program():
    from linumert.generators.pockets import PocketRect
    from linumert.generators.registry import GeneratorRegistry

    reg = GeneratorRegistry()
    reg.register(PocketRect)
    gen = reg.latest("pocket_rect")
    values, issues = gen.normalize({"cx": 20, "cy": 15, "width": 24, "height": 16, "depth": 3,
                                    "step_down": 1.5, "tool_d": 6})
    assert not issues
    return "\n".join([';@STOCK BOX X40 Y30 Z10 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 MAT="aluminium"',
                      "G21 G90 G17 G54", "T1 M6", "S8000 M3", *gen.generate(values),
                      "G0 Z5", "M5", "G1 X10 Y10 Z-1 F300", "G0 X30 Y20 Z-2", "M2"]) + "\n"


@pytest.mark.parametrize("program", ["pocket", "linumert_kolizja"])
def test_simulate_identical_with_library(lib, program):
    if program == "pocket":
        text = _program()
    else:
        text = (ROOT / "config" / "sim" / "nc_files" / f"{program}.ngc").read_text("utf-8")
    job = OfflineJob(program=text, tools=((1, 40.0, 6.0), (2, 45.0, 10.0)), source="subset")
    with native.override(None):
        a = simulate(job)
    with native.override(lib):
        b = simulate(job)
    assert a["removed_mm3"] > 0
    assert b["events"] == a["events"]
    assert b["removed_mm3"] == pytest.approx(a["removed_mm3"], rel=1e-6, abs=0.1)
    del a["removed_mm3"], b["removed_mm3"]
    assert b == a


def test_switch_and_missing_library(monkeypatch, tmp_path):
    monkeypatch.setattr(native, "_state", native._UNSET)
    monkeypatch.setenv("LINUMERT_NATIVE", "0")
    assert native.library() is None and "LINUMERT_NATIVE=0" in native.reason()
    monkeypatch.setattr(native, "_state", native._UNSET)
    monkeypatch.setenv("LINUMERT_NATIVE", "1")
    monkeypatch.setenv("LINUMERT_NATIVE_LIB", str(tmp_path / "brak.so"))
    assert native.library() is None and "make -C core/native" in native.reason()
    # bez biblioteki: płaskorzeźba i materiał liczą się w Pythonie
    path = plan_relief(Mesh(wave(n=3, size=2.0)), replace(ReliefSettings(), sample_step=0.5,
                                                          stepover=0.5, safe_z=5.0))
    assert path.rows
