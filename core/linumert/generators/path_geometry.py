# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded, reproducible tool-centre paths. Model-Author: Codex."""
from __future__ import annotations

import json
import math

from .base import BaseMacroGenerator, Field, Issue, fmt

MAX_POINTS = 12000
MAX_BLOCKS = 20000
CUT_FIELDS = (
    Field("z_top", "float", "Powierzchnia Z", "mm", default=0.0),
    Field("depth", "float", "Głębokość", "mm", default=0.2, minimum=0.0001, maximum=100),
    Field("step_down", "float", "Krok Z", "mm", default=0.2, minimum=0.0001, maximum=100),
    Field("tool_d", "float", "Średnica robocza narzędzia", "mm", default=1.0,
          minimum=0.0001, maximum=1000),
    Field("feed", "float", "Posuw", "mm/min", default=300.0, minimum=0.001, maximum=100000),
    Field("plunge", "float", "Posuw zagłębiania", "mm/min", default=80.0,
          minimum=0.001, maximum=100000),
    Field("safe_z", "float", "Bezpieczna Z", "mm", default=5.0),
)


def problem(field, detail):
    return Issue("P-5015", {"step": 0, "field": field, "expected": detail}, field)


def decode_paths(text):
    if len(text) > 750000:
        raise ValueError("geometria do 750 kB")
    try:
        paths = json.loads(text)
    except (ValueError, RecursionError):
        raise ValueError("poprawna geometria ścieżek XY") from None
    if not isinstance(paths, list) or not paths or len(paths) > 2000:
        raise ValueError("od 1 do 2000 ścieżek")
    count = 0
    result = []
    for path in paths:
        if not isinstance(path, list) or len(path) < 2:
            raise ValueError("co najmniej dwa punkty każdej ścieżki")
        count += len(path)
        if count > MAX_POINTS:
            raise ValueError(f"najwyżej {MAX_POINTS} punktów")
        points = []
        for point in path:
            if not isinstance(point, list) or len(point) != 2 or any(
                    isinstance(x, bool) or not isinstance(x, (int, float))
                    or not math.isfinite(x) or abs(x) > 1000000 for x in point):
                raise ValueError("skończone współrzędne XY w zakresie ±1000000")
            p = tuple(round(float(x), 4) for x in point)
            if not points or p != points[-1]:
                points.append(p)
        if len(points) < 2:
            raise ValueError("odcinki dłuższe od rozdzielczości 0,0001")
        result.append(points)
    return result


def cut_check(v, paths):
    if round(v["safe_z"], 4) <= round(v["z_top"], 4):
        return [problem("safe_z", "wartość większa od powierzchni Z")]
    layers = math.ceil(v["depth"] / v["step_down"])
    blocks = layers * sum(len(path) + 3 for path in paths) + 1
    if blocks > MAX_BLOCKS:
        return [problem("step_down", f"najwyżej {MAX_BLOCKS} bloków; zwiększ krok Z "
                         "lub uprość geometrię")]
    return []


def emit_paths(v, paths):
    """Every disconnected path starts and ends at safe Z; no rapid plunge."""
    lines = ["G90 G17 G94 G40 G80"]
    for layer in range(1, math.ceil(v["depth"] / v["step_down"]) + 1):
        z = v["z_top"] - min(v["depth"], layer * v["step_down"])
        for path in paths:
            x, y = path[0]
            lines += [f"G0 Z{fmt(v['safe_z'])}", f"G0 X{fmt(x)} Y{fmt(y)}",
                      f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
            lines += [f"G1 X{fmt(x)} Y{fmt(y)} F{fmt(v['feed'])}" for x, y in path[1:]]
            lines.append(f"G0 Z{fmt(v['safe_z'])}")
    return lines


class PathTrace(BaseMacroGenerator):
    name = "path_trace"
    version = 1
    title = "Ścieżki XY — tor środka narzędzia"
    fields = (Field("paths", "text", "Geometria XY", default=""),) + CUT_FIELDS

    def paths(self, v):
        return decode_paths(v["paths"])

    def check(self, v, step):
        try:
            return cut_check(v, self.paths(v))
        except ValueError as exc:
            return [problem("paths", str(exc))]

    def generate(self, v):
        return emit_paths(v, self.paths(v))

    def preview_2d(self, v):
        return self.paths(v)
