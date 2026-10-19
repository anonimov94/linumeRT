"""Eksport materiału przygotówki (mapa wysokości) do STL binarnego (sesja 059, punkt 2).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19.

Bryła zamknięta: wierzch z mapy wysokości (dwa trójkąty na komórkę), dno płaskie na `z_bottom`,
ściany boczne na obrysie siatki. Komórki puste (poza walcem albo przecięte do dna) mają wysokość
dna — powstaje płaska powierzchnia na dnie, bryła pozostaje szczelna. Normalne liczone z trójkątów.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from .zmap import StockMap


def _quads_to_tris(a, b, c, d) -> np.ndarray:
    """Czworokąty (a, b, c, d przeciwnie do zegara) → trójkąty [n, 3, 3]."""
    return np.concatenate([np.stack([a, b, c], axis=1), np.stack([a, c, d], axis=1)])


def mesh(smap: StockMap) -> np.ndarray:
    """Trójkąty bryły materiału: tablica [n, 3, 3] (wierzchołki x, y, z w mm)."""
    h = smap.display().astype(np.float64)
    ny, nx = h.shape
    xs = smap.x0 + np.arange(nx + 1) * smap.cell
    ys = smap.y0 + np.arange(ny + 1) * smap.cell
    z0 = smap.z_bottom
    gx, gy = np.meshgrid(xs[:-1], ys[:-1])
    g1x, g1y = np.meshgrid(xs[1:], ys[1:])
    top = h.ravel()
    x0, y0, x1, y1 = gx.ravel(), gy.ravel(), g1x.ravel(), g1y.ravel()
    p = lambda x, y, z: np.stack([x, y, z], axis=1)  # noqa: E731
    tris = [_quads_to_tris(p(x0, y0, top), p(x1, y0, top), p(x1, y1, top), p(x0, y1, top)),
            _quads_to_tris(p(x0, y0, np.full_like(top, z0)), p(x0, y1, np.full_like(top, z0)),
                           p(x1, y1, np.full_like(top, z0)), p(x1, y0, np.full_like(top, z0)))]
    # ściany między sąsiednimi komórkami o różnej wysokości (schodki) i na obrysie
    pad = np.pad(h, 1, constant_values=z0)
    for axis, sign in ((1, 1), (1, -1), (0, 1), (0, -1)):
        nb = np.roll(pad, -sign, axis=axis)[1:-1, 1:-1]
        iy, ix = np.nonzero(h > nb + 1e-9)
        if iy.size == 0:
            continue
        hi, lo = h[iy, ix], nb[iy, ix]
        if axis == 1:   # ściana w X
            x = xs[ix + 1] if sign > 0 else xs[ix]
            ya, yb = (ys[iy], ys[iy + 1]) if sign > 0 else (ys[iy + 1], ys[iy])
            tris.append(_quads_to_tris(p(x, ya, lo), p(x, yb, lo), p(x, yb, hi), p(x, ya, hi)))
        else:           # ściana w Y
            y = ys[iy + 1] if sign > 0 else ys[iy]
            xa, xb = (xs[ix + 1], xs[ix]) if sign > 0 else (xs[ix], xs[ix + 1])
            tris.append(_quads_to_tris(p(xa, y, lo), p(xb, y, lo), p(xb, y, hi), p(xa, y, hi)))
    return np.concatenate(tris)


def write_stl(smap: StockMap, path: str | Path, name: str = "linumeRT material") -> int:
    """Zapis STL binarnego; zwraca liczbę trójkątów."""
    tris = mesh(smap).astype(np.float32)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(length > 0, normals / np.maximum(length, 1e-12), 0).astype(np.float32)
    record = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    record["n"], record["v"] = normals, tris
    with open(path, "wb") as fh:
        fh.write(name.encode("ascii", "replace")[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        fh.write(record.tobytes())
    return len(tris)
