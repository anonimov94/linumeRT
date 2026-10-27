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
    rows = []
    for index, y in enumerate(ys):
        row = []
        for x in xs if index % 2 == 0 else xs[::-1]:
            height = ball_tip_height(t, float(x), float(y), radius + margin) + margin
            z = math.ceil(max(float(low[2]), height) * 10000) / 10000
            row.append((float(x), float(y), z))
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
