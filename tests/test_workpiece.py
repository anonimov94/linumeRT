"""Geometria zamkniętych przygotówek. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from collections import Counter
from math import pi

import numpy as np
import pytest
from linumert.programs.workpiece import (
    ANCHOR_NAMES,
    Workpiece,
    anchor_name,
    offset_command,
)


@pytest.mark.parametrize(("shape", "volume"), [
    ("box", 100 * 80 * 30), ("cylinder", pi * 40**2 * 30),
    ("tube", pi * (40**2 - 20**2) * 30),
    ("casting", pi * 15 / 3 * (25**2 + 25 * 40 + 40**2)
     + pi * 25 / 3 * (40**2 + 40 * 30 + 30**2)),
])
def test_mesh_closed_volume_and_anchor(shape, volume):
    spec = Workpiece(shape=shape, position=(0, 0, 0))
    vertices, faces = spec.mesh()
    edges = Counter(tuple(sorted((int(a), int(b)))) for face in faces
                    for a, b in zip(face, np.roll(face, -1), strict=True))
    assert set(edges.values()) == {2}
    measured = abs(sum(np.dot(vertices[a], np.cross(vertices[b], vertices[c]))
                       for a, b, c in faces)) / 6
    assert measured == pytest.approx(volume, rel=0.004)
    assert vertices[:, 2].max() == pytest.approx(0)


@pytest.mark.parametrize("values", [dict(shape="tube", bore=90), dict(x=float("nan")),
    dict(shape="casting", profile=((0, 10), (0, 20))),
    dict(shape="casting", profile=((0, -10), (10, 20)))])
def test_invalid_geometry(values):
    with pytest.raises(ValueError):
        Workpiece(**values)


def test_units_and_persisted_definition():
    spec = Workpiece(shape="tube", position=(25.4, 50.8, -25.4), offset="G59")
    assert offset_command(spec, False) == "G10 L2 P6 X1.000000 Y2.000000 Z-1.000000"
    assert Workpiece(**spec.to_dict()).to_dict() == spec.to_dict()


@pytest.mark.parametrize("anchor", ANCHOR_NAMES)
def test_every_anchor_puts_the_chosen_point_at_the_position(anchor):
    spec = Workpiece(x=100, y=60, height=30, anchor=anchor, position=(200, 150, -50))
    low, high = spec.bounds()
    face, _, rest = anchor.partition("-")
    x = {"left": low[0], "right": high[0]}.get(rest.split("-")[-1], (low[0] + high[0]) / 2)
    y = {"front": low[1], "back": high[1]}.get(rest.split("-")[0], (low[1] + high[1]) / 2)
    z = high[2] if face == "top" else low[2]
    assert (x, y, z) == pytest.approx((200, 150, -50))


def test_anchor_name_from_clicked_point():
    assert anchor_name("top", -1, -1) == "top-front-left"
    assert anchor_name("bottom", 1, 1) == "bottom-back-right"
    assert anchor_name("top", 0, 0) == "top-center"
    with pytest.raises(ValueError):
        anchor_name("top", 0, 1)


def test_fit_issues_for_stock_and_zero():
    limits = {"X": (0.0, 600.0), "Y": (0.0, 400.0), "Z": (-120.0, 0.0)}
    ok = Workpiece(x=100, y=100, height=30, anchor="top-front-left", position=(100, 100, -50))
    assert ok.fit_issues(limits) == []
    out = Workpiece(x=100, y=100, height=30, anchor="top-front-left", position=(560, 100, -50))
    assert "osi X" in out.fit_issues(limits)[0]
    deep = Workpiece(x=100, y=100, height=30, anchor="top-front-left", position=(100, 100, -150))
    assert any("osi Z" in m for m in deep.fit_issues(limits))
