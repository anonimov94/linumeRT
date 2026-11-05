"""Conservative three-axis ball-nose finishing of an STL upper envelope.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

This is geometry/G-code generation only, outside RT. Stock must already be roughed.
Undercuts, tool shanks, holders and machine collisions are outside this model.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from linumert.programs.stl_section import Mesh, read_stl

from .base import fmt

MAX_POINTS = 50000
MAX_WORK = 50000000


def ball_tip_height(triangles: np.ndarray, x: float, y: float, radius: float) -> float:
    """Exact static drop-cutter contact: triangle interiors, edges and vertices.

    Return -inf if the ball footprint does not meet the mesh. The cutter reference
    is the bottom tip, not the sphere centre. Vertical facets are handled by edges.
    """
    if not all(math.isfinite(v) for v in (x, y, radius)) or radius <= 0:
        raise ValueError("Frez kulisty: wymagany dodatni promień i skończona pozycja.")
    t = np.asarray(triangles, dtype=float)
    if t.ndim != 3 or t.shape[1:] != (3, 3) or not np.isfinite(t).all():
        raise ValueError("Niepoprawna siatka trójkątów.")
    if not len(t):
        return -math.inf
    xy = np.array([x, y])
    low, high = t[:, :, :2].min(axis=1), t[:, :, :2].max(axis=1)
    t = t[np.all((low <= xy + radius + 1e-9) & (high >= xy - radius - 1e-9), axis=1)]
    best = -math.inf
    # Restriction to each edge is a line plus a circular arc, with an analytic maximum.
    for index in range(3):
        a, b = t[:, index], t[:, (index + 1) % 3]
        d = b - a
        length2 = np.sum(d[:, :2] ** 2, axis=1)
        nonvertical = length2 > 0
        denominator = np.where(nonvertical, length2, 1)
        projection = np.sum((xy - a[:, :2]) * d[:, :2], axis=1) / denominator
        distance2 = np.sum((a[:, :2] + projection[:, None] * d[:, :2] - xy) ** 2,
                           axis=1)
        available = np.maximum(0, radius**2 - distance2)
        offset = d[:, 2] * np.sqrt(available / (denominator + d[:, 2] ** 2))
        parameter = np.clip(projection + offset / np.sqrt(denominator), 0, 1)
        parameter = np.where(nonvertical, parameter, (d[:, 2] > 0).astype(float))
        contact = a + parameter[:, None] * d
        inside = radius**2 - np.sum((contact[:, :2] - xy) ** 2, axis=1)
        heights = contact[:, 2] + np.sqrt(np.maximum(0, inside)) - radius
        touching = inside >= -1e-10 * max(1, radius**2)
        best = max(best, float(np.max(heights[touching], initial=-math.inf)))
    # Interior optimum of z = ax + by + c under the spherical cap.
    normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    t, normal = t[normal[:, 2] != 0], normal[normal[:, 2] != 0]
    if len(t):
        offset = (-radius * normal[:, :2] * np.sign(normal[:, 2, None])
                  / np.linalg.norm(normal, axis=1)[:, None])
        contact = xy + offset
        a, b = t[:, 1, :2] - t[:, 0, :2], t[:, 2, :2] - t[:, 0, :2]
        q = contact - t[:, 0, :2]
        determinant = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        u = (q[:, 0] * b[:, 1] - q[:, 1] * b[:, 0]) / determinant
        v = (a[:, 0] * q[:, 1] - a[:, 1] * q[:, 0]) / determinant
        inside = (u >= -1e-10) & (v >= -1e-10) & (u + v <= 1 + 1e-10)
        surface = (t[:, 0, 2] + u * (t[:, 1, 2] - t[:, 0, 2])
                   + v * (t[:, 2, 2] - t[:, 0, 2]))
        heights = surface + np.sqrt(np.maximum(0, radius**2 - np.sum(offset**2, axis=1)))
        best = max(best, float(np.max(heights[inside], initial=-math.inf)) - radius)
    return best


def ball_tip_heights(triangles: np.ndarray, xy: np.ndarray, radius: float) -> np.ndarray:
    """`ball_tip_height` dla wielu punktów naraz (numpy, te same działania na parach
    punkt × trójkąt). Model-Author: Claude · 2026-11-05.

    Wynik identyczny z wersją punktową; ta zostaje referencją w testach. Punkty liczone
    porcjami po 256 (sąsiednie w wierszu), z kandydatami z obwiedni porcji.
    """
    t = np.asarray(triangles, dtype=float)
    pts = np.asarray(xy, dtype=float).reshape(-1, 2)
    out = np.full(len(pts), -math.inf)
    if not len(t) or not len(pts):
        return out
    r2 = radius**2
    touch = -1e-10 * max(1, radius**2)
    low, high = t[:, :, :2].min(axis=1), t[:, :, :2].max(axis=1)
    order = np.lexsort((pts[:, 0], pts[:, 1]))     # sąsiednie punkty = wspólni kandydaci
    start = 0
    while start < len(order):
        stop = min(start + 256, len(order))
        idx = order[start:stop]
        start = stop
        p = pts[idx]
        win_lo, win_hi = p.min(axis=0) - radius - 1e-9, p.max(axis=0) + radius + 1e-9
        cand = np.flatnonzero(np.all((low <= win_hi) & (high >= win_lo), axis=1))
        if not len(cand):
            continue
        tc, lo, hi = t[cand], low[cand], high[cand]
        x, y = p[:, 0, None], p[:, 1, None]
        mask = ((lo[None, :, 0] <= x + radius + 1e-9) & (lo[None, :, 1] <= y + radius + 1e-9)
                & (hi[None, :, 0] >= x - radius - 1e-9) & (hi[None, :, 1] >= y - radius - 1e-9))
        best = np.full(len(p), -math.inf)
        for index in range(3):
            a, b = tc[:, index], tc[:, (index + 1) % 3]
            d = b - a
            length2 = d[:, 0] ** 2 + d[:, 1] ** 2
            nonvertical = length2 > 0
            denominator = np.where(nonvertical, length2, 1)
            projection = ((x - a[:, 0]) * d[:, 0] + (y - a[:, 1]) * d[:, 1]) / denominator
            distance2 = ((a[:, 0] + projection * d[:, 0] - x) ** 2
                         + (a[:, 1] + projection * d[:, 1] - y) ** 2)
            available = np.maximum(0, r2 - distance2)
            offset = d[:, 2] * np.sqrt(available / (denominator + d[:, 2] ** 2))
            parameter = np.clip(projection + offset / np.sqrt(denominator), 0, 1)
            parameter = np.where(nonvertical, parameter, (d[:, 2] > 0).astype(float))
            c0 = a[:, 0] + parameter * d[:, 0]
            c1 = a[:, 1] + parameter * d[:, 1]
            c2 = a[:, 2] + parameter * d[:, 2]
            inside = r2 - ((c0 - x) ** 2 + (c1 - y) ** 2)
            heights = c2 + np.sqrt(np.maximum(0, inside)) - radius
            ok = mask & (inside >= touch)
            best = np.maximum(best, np.max(np.where(ok, heights, -math.inf), axis=1))
        normal = np.cross(tc[:, 1] - tc[:, 0], tc[:, 2] - tc[:, 0])
        keep = normal[:, 2] != 0
        if np.any(keep):
            tk, nk = tc[keep], normal[keep]
            offset = (-radius * nk[:, :2] * np.sign(nk[:, 2, None])
                      / np.linalg.norm(nk, axis=1)[:, None])
            q0 = x + offset[:, 0] - tk[:, 0, 0]
            q1 = y + offset[:, 1] - tk[:, 0, 1]
            ea, eb = tk[:, 1, :2] - tk[:, 0, :2], tk[:, 2, :2] - tk[:, 0, :2]
            determinant = ea[:, 0] * eb[:, 1] - ea[:, 1] * eb[:, 0]
            u = (q0 * eb[:, 1] - q1 * eb[:, 0]) / determinant
            v = (ea[:, 0] * q1 - ea[:, 1] * q0) / determinant
            inside = mask[:, keep] & (u >= -1e-10) & (v >= -1e-10) & (u + v <= 1 + 1e-10)
            surface = (tk[:, 0, 2] + u * (tk[:, 1, 2] - tk[:, 0, 2])
                       + v * (tk[:, 2, 2] - tk[:, 0, 2]))
            heights = surface + np.sqrt(np.maximum(0, r2 - (offset[:, 0] ** 2
                                                            + offset[:, 1] ** 2)))
            interior = np.max(np.where(inside, heights, -math.inf), axis=1) - radius
            best = np.maximum(best, interior)
        out[idx] = best
    return out


def _grid_heights(t: np.ndarray, xs: np.ndarray, ys: np.ndarray, radius: float) -> np.ndarray:
    """Wysokości (len(ys), len(xs)): biblioteka C, gdy jest, inaczej numpy porcjami."""
    from linumert import native

    xy = np.column_stack((np.tile(xs, len(ys)), np.repeat(ys, len(xs))))
    lib = native.library()
    if lib is not None:
        heights = native.relief_heights(lib, t, xy, radius)
    else:
        heights = ball_tip_heights(t, xy, radius)
    return heights.reshape(len(ys), len(xs))


@dataclass(frozen=True)
class ReliefSettings:
    tool_diameter: float = 3.0
    sample_step: float = 0.1
    stepover: float = 0.5
    safe_z: float = 10.0
    feed: float = 500.0
    plunge: float = 100.0
    tool: int = 1
    rpm: int = 10000
    scale: float = 1.0  # STL has no units: 1 = mm, 25.4 = inches


@dataclass(frozen=True)
class ReliefPath:
    rows: tuple[tuple[tuple[float, float, float], ...], ...]
    settings: ReliefSettings

    def gcode(self) -> str:
        """Standalone mm/G54 program; caller must perform machine/stock preflight."""
        s = self.settings
        lines = ["( linumeRT STL: wykanczanie frezem kulistym, przygotowka po zgrubnej )",
                 "G21 G90 G17 G94 G40 G80 G54 G61", f"T{s.tool} M6", f"G43 H{s.tool}",
                 f"G97 S{s.rpm} M3"]
        for row in self.rows:
            x, y, z = row[0]
            lines += [f"G0 Z{fmt(s.safe_z)}", f"G0 X{fmt(x)} Y{fmt(y)}",
                      f"G1 Z{fmt(z)} F{fmt(s.plunge)}"]
            lines += [f"G1 X{fmt(x)} Y{fmt(y)} Z{fmt(z)} F{fmt(s.feed)}"
                      for x, y, z in row[1:]]
        return "\n".join(lines + [f"G0 Z{fmt(s.safe_z)}", "M5", "M2"]) + "\n"


def plan_relief(mesh: Mesh, settings: ReliefSettings | None = None) -> ReliefPath:
    """Raster the rectangular XY bounds; retain the upper envelope of all shells.

    Inflate the contact sphere by one actual X segment, then reference its centre
    to the real radius. Each endpoint thus bounds the whole connecting segment,
    including narrow features between samples. Z is rounded upwards. This leaves
    conservative stock (on a horizontal plane: one X segment), not a finish tolerance.
    Every row is approached/retracted at safe Z; there are no low diagonal links.
    """
    s = settings or ReliefSettings()
    values = (s.tool_diameter, s.sample_step, s.stepover, s.safe_z, s.feed, s.plunge, s.scale)
    if (not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) and abs(v) <= 1000000 for v in values)
            or min(s.tool_diameter, s.sample_step, s.stepover, s.feed, s.plunge, s.scale) <= 0
            or min(s.tool_diameter, s.sample_step, s.stepover) < 0.0001
            or min(round(s.feed, 4), round(s.plunge, 4)) <= 0
            or s.stepover > s.tool_diameter
            or any(type(v) is not int or not 0 < v <= 1000000 for v in (s.tool, s.rpm))):
        raise ValueError("Niepoprawne parametry płaskorzeźby lub krok poniżej 0,0001 mm.")
    t = np.asarray(mesh.triangles, dtype=float) * s.scale
    if (t.ndim != 3 or t.shape[1:] != (3, 3) or not len(t)
            or not np.isfinite(t).all() or np.abs(t).max() > 1000000):
        raise ValueError("Niepoprawny STL lub zakres po skali przekracza ±1000000 mm.")
    low, high = t.min(axis=(0, 1)), t.max(axis=(0, 1))
    if min(high[:2] - low[:2]) <= 0:
        raise ValueError("STL musi mieć niezerowy obszar XY.")
    nx = math.ceil((high[0] - low[0]) / s.sample_step) + 1
    ny = math.ceil((high[1] - low[1]) / s.stepover) + 1
    if nx * ny > MAX_POINTS or nx * ny * len(t) > MAX_WORK:
        raise ValueError("Przekroczony limit obliczeń STL; uprość siatkę lub zwiększ krok.")
    xs = np.unique(np.round(np.linspace(low[0], high[0], nx), 4))
    ys = np.unique(np.round(np.linspace(low[1], high[1], ny), 4))
    if len(xs) < 2 or len(ys) < 2:
        raise ValueError("Obszar STL znika po zaokrągleniu do 0,0001 mm.")
    margin = float(np.diff(xs).max())
    radius = s.tool_diameter / 2
    if round(s.safe_z, 4) <= math.ceil((high[2] + margin) * 10000) / 10000:
        raise ValueError("Bezpieczna Z musi być ponad STL i naddatkiem próbkowania.")
    # Wysokość kuli w punkcie = ball_tip_height(t, x, y, radius + margin) (biblioteka C albo
    # numpy porcjami; obie z tym samym wynikiem co wersja punktowa).
    grid = _grid_heights(t, xs, ys, radius + margin)
    rows = []
    for index, y in enumerate(ys):
        row = []
        columns = range(len(xs)) if index % 2 == 0 else range(len(xs) - 1, -1, -1)
        for j in columns:
            height = float(grid[index, j]) + margin
            z = math.ceil(max(float(low[2]), height) * 10000) / 10000
            row.append((float(xs[j]), float(y), z))
        rows.append(tuple(row))
    return ReliefPath(tuple(rows), s)


def relief_from_stl(path, settings: ReliefSettings | None = None) -> ReliefPath:
    return plan_relief(read_stl(path), settings)


def main(argv: list[str] | None = None) -> int:
    """CLI writes a file atomically; never connects to or commands a machine."""
    import argparse

    from linumert.programs.lnx import atomic_write

    parser = argparse.ArgumentParser(description="STL → G-code: wykańczanie frezem kulistym")
    parser.add_argument("stl", help="plik STL ASCII lub binary")
    parser.add_argument("-o", "--output", required=True, help="docelowy plik .ngc")
    for field, label in (
        ("tool_diameter", "średnica frezu kulistego [mm]"),
        ("sample_step", "krok wzdłuż wiersza [mm], wpływa na zachowawczy naddatek"),
        ("stepover", "odstęp wierszy [mm]"), ("safe_z", "bezpieczna Z w G54 [mm]"),
        ("feed", "posuw obróbki [mm/min]"), ("plunge", "posuw wejścia [mm/min]"),
        ("scale", "przelicznik STL na mm (25.4 dla cali)"),
        ("tool", "numer narzędzia i H"), ("rpm", "obroty wrzeciona M3"),
    ):
        parser.add_argument("--" + field.replace("_", "-"),
                            type=int if field in ("tool", "rpm") else float,
                            default=getattr(ReliefSettings(), field), help=label)
    args = parser.parse_args(argv)
    settings = ReliefSettings(**{key: getattr(args, key) for key in
                                 ReliefSettings.__dataclass_fields__})
    try:
        path = relief_from_stl(args.stl, settings)
        atomic_write(args.output, path.gcode())
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Zapisano {args.output}: {len(path.rows)} wierszy, "
          f"{sum(map(len, path.rows))} punktów. Przygotówka wymaga obróbki zgrubnej.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
