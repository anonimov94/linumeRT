# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded STL reader and closed XY sections, without Qt. Model-Author: Codex."""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MAX_BYTES = 8 * 1024 * 1024
MAX_TRIANGLES = 100000
MAX_SEGMENTS = 10000


@dataclass(frozen=True)
class Mesh:
    triangles: np.ndarray

    @property
    def bounds(self):
        return self.triangles.min(axis=(0, 1)), self.triangles.max(axis=(0, 1))


def read_stl(path):
    with Path(path).open("rb") as file:
        data = file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("STL: limit 8 MiB; uprość siatkę przed importem.")
    count = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0
    if count and len(data) == 84 + count * 50:
        if count > MAX_TRIANGLES:
            raise ValueError("STL: najwyżej 100000 trójkątów.")
        dtype = np.dtype([("normal", "<f4", 3), ("points", "<f4", (3, 3)), ("attr", "<u2")])
        triangles = np.frombuffer(data, dtype=dtype, count=count, offset=84)["points"].astype(float)
    else:
        try:
            lines = [line.strip().split() for line in data.decode("ascii").splitlines()
                     if line.strip()]
            if (len(lines) < 9 or lines[0][0].lower() != "solid"
                    or lines[-1][0].lower() != "endsolid" or (len(lines) - 2) % 7):
                raise ValueError
            if (len(lines) - 2) // 7 > MAX_TRIANGLES:
                raise ValueError
            facets = []
            for i in range(1, len(lines) - 1, 7):
                part = lines[i:i + 7]
                if ([x.lower() for x in part[0][:2]] != ["facet", "normal"]
                        or len(part[0]) != 5 or [x.lower() for x in part[1]] != ["outer", "loop"]
                        or part[5] != ["endloop"] or part[6] != ["endfacet"]):
                    raise ValueError
                for vertex in part[2:5]:
                    if len(vertex) != 4 or vertex[0].lower() != "vertex":
                        raise ValueError
                facets.append([[float(x) for x in vertex[1:]] for vertex in part[2:5]])
            triangles = np.asarray(facets, dtype=float)
        except (UnicodeError, ValueError, IndexError):
            raise ValueError("Niepoprawny STL ASCII/binary lub przekroczony limit siatki."
                             ) from None
    if (not triangles.size or not np.isfinite(triangles).all()
            or np.abs(triangles).max() > 1000000):
        raise ValueError("STL: wymagane skończone współrzędne w zakresie ±1000000.")
    nonzero = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                     triangles[:, 2] - triangles[:, 0]), axis=1) > 1e-16
    triangles = triangles[nonzero]
    if not len(triangles):
        raise ValueError("STL nie zawiera niezerowych trójkątów.")
    triangles.setflags(write=False)
    return Mesh(triangles)


def section_xy(mesh, z, factor=1.0, centered=False):
    if (not math.isfinite(z) or not math.isfinite(factor) or factor <= 0
            or factor > 25400 or abs(z) > 1000000):
        raise ValueError("Niepoprawna płaszczyzna lub skala STL.")
    points = mesh.triangles * factor
    low, high = points.min(axis=(0, 1)), points.max(axis=(0, 1))
    if not low[2] + 1e-7 < z < high[2] - 1e-7:
        raise ValueError(f"Wybierz przekrój wewnątrz zakresu Z: {low[2]:g} … {high[2]:g}.")
    if np.abs(points).max() > 1000000:
        raise ValueError("STL po przeskalowaniu przekracza zakres ±1000000.")
    if centered:
        points[:, :, :2] -= (low[:2] + high[:2]) / 2
    candidates = points[(points[:, :, 2].min(axis=1) <= z)
                        & (points[:, :, 2].max(axis=1) >= z)]
    segments = set()
    for triangle in candidates:
        if np.abs(triangle[:, 2] - z).max() <= 1e-9:
            continue
        hits = set()
        for a, b in zip(triangle, np.roll(triangle, -1, axis=0), strict=True):
            da, db = a[2] - z, b[2] - z
            if abs(da) <= 1e-9:
                hits.add(tuple(round(float(x), 6) for x in a[:2]))
            if da * db < 0:
                hit = a + (b - a) * (-da / (db - da))
                hits.add(tuple(round(float(x), 6) for x in hit[:2]))
        if len(hits) == 2:
            segments.add(tuple(sorted(hits)))
        if len(segments) > MAX_SEGMENTS:
            raise ValueError("Przekrój ma zbyt wiele odcinków; uprość STL.")
    return join_closed(segments)


def join_closed(segments):
    if not segments:
        raise ValueError("Brak konturu w wybranej płaszczyźnie.")
    neighbours = {}
    for a, b in segments:
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    if any(len(edges) != 2 for edges in neighbours.values()):
        raise ValueError("Przekrój jest otwarty lub rozgałęziony. Napraw siatkę albo zmień Z.")
    unused = set(neighbours)
    paths = []
    while unused:
        start = min(unused)
        previous, current = None, start
        path = []
        while True:
            path.append(current)
            unused.discard(current)
            following = min(p for p in neighbours[current] if p != previous)
            previous, current = current, following
            if current == start:
                break
        paths.append(path + [start])
    return paths
