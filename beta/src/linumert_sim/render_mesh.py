"""Validated triangle input for the offline SKIN-01 renderer, in machine mm.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex. No Qt, LinuxCNC, HAL or implicit winding repair.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray
    removed_degenerate: int


def prepare_mesh(vertices, faces):
    """Copy and validate input; omit zero-area faces with an explicit count.

    CCW faces point outwards. Open meshes are allowed; their winding is retained.
    Topology and self-intersections remain the caller's responsibility.
    """
    v = np.array(vertices, dtype=np.float64, copy=True)
    f = np.asarray(faces)
    if v.ndim != 2 or v.shape[1] != 3 or not len(v) or not np.isfinite(v).all():
        raise ValueError("vertices must be finite XYZ coordinates in mm")
    if f.ndim != 2 or f.shape[1] != 3 or not len(f) or f.dtype.kind not in "iu":
        raise ValueError("faces must be nonempty integer triples")
    if f.min() < 0 or f.max() >= len(v):
        raise ValueError("face index outside vertices")
    f = np.array(f, dtype=np.int64, copy=True)
    triangles = v[f]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    length = np.linalg.norm(normals, axis=1)
    if not np.isfinite(length).all():
        raise ValueError("mesh exceeds numeric range")
    keep = length > 1e-12  # twice area, in mm²; do not hide thin valid triangles
    if not keep.any():
        raise ValueError("mesh has no nondegenerate faces")
    removed = int((~keep).sum())
    f, normals = f[keep], normals[keep] / length[keep, None]
    for array in (v, f, normals):
        array.flags.writeable = False
    return Mesh(v, f, normals, removed)


def crossing_triangles():
    """Two intersecting open surfaces: no whole-triangle sort can render these.

    Viewed from +Z, the teal surface is in front at x>0, amber at x<0.
    Equal mean depth deliberately exposes order-dependent painter rendering.
    """
    xy = np.array([[-80., -60.], [80., -60.], [0., 80.]])
    return tuple(prepare_mesh(np.column_stack((xy, sign * xy[:, 0] / 2)), [[0, 1, 2]])
                 for sign in (1, -1))
