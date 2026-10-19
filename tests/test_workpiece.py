"""Geometria zamkniętych przygotówek. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from collections import Counter
from math import pi

import numpy as np
import pytest
from linumert.programs.workpiece import Workpiece, offset_command


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
