# SPDX-License-Identifier: GPL-2.0-or-later
"""Versioned facing strategies; version 1 remains unchanged. Model-Author: Codex."""
from __future__ import annotations

import math
from dataclasses import replace

from .base import Field
from .basic import FaceMill
from .path_geometry import MAX_BLOCKS, cut_check, emit_paths, problem


class FaceMillStrategies(FaceMill):
    version = 2
    choice_labels = {
        "mode": {"zigzag": "Zygzak", "one_way": "Jednokierunkowo",
                 "crosshatch": "Przejścia krzyżowe", "concentric": "Kontury współśrodkowe"},
        "direction": {"ccw": "Przeciwnie do wskazówek zegara", "cw": "Zgodnie z zegarem"},
    }
    fields = tuple(
        replace(f, choices=("zigzag", "one_way", "crosshatch", "concentric"))
        if f.name == "mode" else
        replace(f, minimum=0.0001, exclusive_minimum=False)
        if f.name in ("depth", "tool_d", "step_down") else f for f in FaceMill.fields
    ) + (
        Field("axis", "choice", "Kierunek przejść", default="X", choices=("X", "Y")),
        Field("direction", "choice", "Kierunek konturów", default="ccw", choices=("ccw", "cw")),
    )

    def check(self, v, step):
        issues = super().check(v, step)
        if issues:
            return issues
        for key in ("x0", "x1", "y0", "y1", "z_top", "safe_z", "overrun", "tool_d"):
            if abs(v[key]) > 1000000:
                return [problem(key, "wartość w zakresie ±1000000", step)]
        stride = v["tool_d"] * v["stepover"] / 100
        width, height = v["x1"] - v["x0"], v["y1"] - v["y0"]
        nx, ny = math.ceil(width / stride) + 1, math.ceil(height / stride) + 1
        if v["mode"] == "concentric":
            n = math.floor((min(width, height) / 2 + v["overrun"] + v["tool_d"] / 2)
                           / stride) + 1
            count = 8 * n + 5
        elif v["mode"] == "crosshatch":
            count = 2 * (nx + ny) + 6
        else:
            n = ny if v["axis"] == "X" else nx
            count = 5 * n if v["mode"] == "one_way" else 2 * n + 3
        if count * math.ceil(v["depth"] / v["step_down"]) + 1 > MAX_BLOCKS:
            return [problem("stepover", "najwyżej 20000 bloków; zwiększ krok lub średnicę "
                             "narzędzia, zmniejsz wybieg lub głębokość", step)]
        return cut_check(v, self.paths(v), step)

    def paths(self, v):
        stride = v["tool_d"] * v["stepover"] / 100
        over = v["tool_d"] / 2 + v["overrun"]
        if v["mode"] == "concentric":
            cx, cy = (v["x0"] + v["x1"]) / 2, (v["y0"] + v["y1"]) / 2
            hx, hy = (v["x1"] - v["x0"]) / 2 + over, (v["y1"] - v["y0"]) / 2 + over
            paths = []
            n = math.floor(min(hx, hy) / stride) + 1
            for i in range(n):
                a, b = hx - i * stride, hy - i * stride
                if min(a, b) <= 0.00005:
                    break
                path = [(cx - a, cy - b), (cx + a, cy - b), (cx + a, cy + b),
                        (cx - a, cy + b), (cx - a, cy - b)]
                paths.append(path[::-1] if v["direction"] == "cw" else path)
            # Finish the centre strip even when the last mathematical ring collapses to a point.
            a, b = (abs(paths[-1][0][0] - cx), abs(paths[-1][0][1] - cy)) if paths else (hx, hy)
            paths.append([(cx - a, cy), (cx + a, cy)] if hx >= hy else
                         [(cx, cy - b), (cx, cy + b)])
            return [p for p in paths if p[0] != p[1]]
        paths = self._raster(v, v["axis"] == "Y", stride, over)
        if v["mode"] == "crosshatch":
            paths += self._raster(v, v["axis"] != "Y", stride, over)
        return paths

    @staticmethod
    def _raster(v, vertical, stride, over):
        a, b = (("y", "x") if vertical else ("x", "y"))
        n = math.ceil((v[b + "1"] - v[b + "0"]) / stride)
        paths, connected = [], []
        for i in range(n + 1):
            cross = v[b + "0"] + (v[b + "1"] - v[b + "0"]) * i / n
            pair = [(v[a + "0"] - over, cross), (v[a + "1"] + over, cross)]
            if v["mode"] != "one_way" and i % 2:
                pair.reverse()
            if vertical:
                pair = [(y, x) for x, y in pair]
            if v["mode"] == "one_way":
                paths.append(pair)
            else:
                connected += pair
        return paths or [connected]

    def generate(self, v):
        return emit_paths(v, self.paths(v))

    def preview_2d(self, v):
        return self.paths(v)


def register(registry=None):
    from .registry import DEFAULT_REGISTRY

    (registry or DEFAULT_REGISTRY).register(FaceMillStrategies)
