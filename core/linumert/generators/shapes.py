# SPDX-License-Identifier: GPL-2.0-or-later
"""Parametric engraving outlines and hatch strokes. Model-Author: Codex."""
from __future__ import annotations

import math

from .base import Field
from .path_geometry import CUT_FIELDS, PathTrace, cut_check, problem


class ShapeEngrave(PathTrace):
    name = "shape_engrave"
    version = 1
    title = "Kształty — kontur i kreskowanie"
    fields = (
        Field("shape", "choice", "Kształt", default="rectangle",
              choices=("rectangle", "ellipse", "polygon", "star")),
        Field("width", "float", "Szerokość", "mm", default=40.0, minimum=0.001, maximum=10000),
        Field("height", "float", "Wysokość", "mm", default=25.0, minimum=0.001, maximum=10000),
        Field("sides", "int", "Boki / ramiona", default=6, minimum=3, maximum=64),
        Field("inner", "float", "Promień wewnętrzny gwiazdy", "%", default=45.0,
              minimum=5, maximum=95),
        Field("strategy", "choice", "Strategia", default="outline",
              choices=("outline", "hatch", "crosshatch", "outline_hatch")),
        Field("spacing", "float", "Odstęp kreskowania", "mm", default=1.0,
              minimum=0.001, maximum=10000),
        Field("cx", "float", "Środek X", "mm", default=0.0, minimum=-100000, maximum=100000),
        Field("cy", "float", "Środek Y", "mm", default=0.0, minimum=-100000, maximum=100000),
        Field("angle", "float", "Obrót", "°", default=0.0, minimum=-360, maximum=360),
    ) + CUT_FIELDS

    def paths(self, v):
        w, h = v["width"] / 2, v["height"] / 2
        if v["shape"] == "rectangle":
            polygon = [(-w, -h), (w, -h), (w, h), (-w, h)]
        else:
            n = 128 if v["shape"] == "ellipse" else v["sides"]
            if v["shape"] == "star":
                n *= 2
            polygon = []
            for i in range(n):
                r = v["inner"] / 100 if v["shape"] == "star" and i % 2 else 1
                a = math.tau * i / n
                polygon.append((r * w * math.cos(a), r * h * math.sin(a)))
        paths = [polygon + [polygon[0]]] if v["strategy"] in ("outline", "outline_hatch") else []
        if v["strategy"] != "outline":
            paths += hatch(polygon, v["spacing"])
        if v["strategy"] == "crosshatch":
            paths += [[(y, x) for x, y in path] for path in
                      hatch([(y, x) for x, y in polygon], v["spacing"])]
        c, s = math.cos(math.radians(v["angle"])), math.sin(math.radians(v["angle"]))
        return [[(v["cx"] + c * x - s * y, v["cy"] + s * x + c * y) for x, y in path]
                for path in paths]

    def check(self, v, step):
        if v["strategy"] != "outline" and max(v["width"], v["height"]) / v["spacing"] > 500:
            return [problem("spacing", "najwyżej 500 linii kreskowania na kierunek")]
        return cut_check(v, self.paths(v))


def hatch(polygon, spacing):
    low, high = min(y for _, y in polygon), max(y for _, y in polygon)
    n = max(1, math.ceil((high - low) / spacing))
    paths = []
    for row in range(n):
        y = low + (row + 0.5) * (high - low) / n
        xs = []
        for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1], strict=True):
            if (ay <= y < by) or (by <= y < ay):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        xs.sort()
        for a, b in zip(xs[::2], xs[1::2], strict=True):
            if b - a > 0.0001:
                paths.append([(a, y), (b, y)] if row % 2 == 0 else [(b, y), (a, y)])
    return paths


def register(registry=None):
    from .registry import DEFAULT_REGISTRY

    registry = registry or DEFAULT_REGISTRY
    registry.register(ShapeEngrave)
    registry.register(PathTrace)
