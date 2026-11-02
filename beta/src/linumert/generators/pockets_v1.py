"""Kieszenie prostokątne i okrągłe — niezmienna wersja 1 (sesja 041).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-20

UWAGA: wejście pionowe wymaga narzędzia skrawającego w osi; przed obróbką
wymagane sprawdzenie w symulacji LinuxCNC/Plant. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
from typing import Any

from .base import BaseMacroGenerator, Field, Issue, Polyline, fmt

COMMON = (
    Field("cx", "float", "Środek X", "mm", default=0.0),
    Field("cy", "float", "Środek Y", "mm", default=0.0),
    Field("z_top", "float", "Powierzchnia Z", "mm", default=0.0),
    Field("depth", "float", "Głębokość", "mm", minimum=0.0001, maximum=100),
    Field("step_down", "float", "Krok Z", "mm", default=1.0, minimum=0.0001),
    Field("tool_d", "float", "Średnica frezu", "mm", minimum=0.001),
    Field("stepover", "float", "Krok boczny", "% D", default=50.0, minimum=5, maximum=90),
    Field("feed", "float", "Posuw", "mm/min", default=400.0, minimum=0,
          exclusive_minimum=True),
    Field("plunge", "float", "Posuw zagłębiania", "mm/min", default=100.0, minimum=0,
          exclusive_minimum=True),
    Field("safe_z", "float", "Bezpieczna Z", "mm", default=5.0),
)


def _levels(v: dict[str, Any]):
    count = math.ceil(v["depth"] / v["step_down"])
    for k in range(1, count + 1):
        yield v["z_top"] - min(v["depth"], k * v["step_down"])


def _check(v: dict[str, Any], step: int, clearance: float) -> list[Issue]:
    issues = []
    if round(v["safe_z"], 4) <= round(v["z_top"], 4):
        issues.append(Issue("P-5003", {"name": "safe_z", "value": fmt(v["safe_z"]),
                                      "limit": f"> {fmt(v['z_top'])}"}, "safe_z"))
    extent = max(v.get("width", 0), v.get("height", 0), v.get("diameter", 0))
    rings = math.ceil(extent / (v["tool_d"] * v["stepover"] / 100))
    blocks = math.ceil(v["depth"] / v["step_down"]) * (5 * rings + 4)
    if blocks > 20000:
        issues.append(Issue("P-5003", {"name": "liczba bloków", "value": str(blocks),
                                      "limit": "<= 20000"}, "step_down"))
    if round(clearance / 2, 4) <= 0:
        issues.append(Issue("P-5007", {"tool": 0, "what":
                                      "średnica frezu nie mieści się w kieszeni"}, "tool_d"))
    return issues


class PocketRect(BaseMacroGenerator):
    name = "pocket_rect"
    version = 1
    title = "Kieszeń prostokątna (prototyp)"
    fields = COMMON + (
        Field("width", "float", "Szerokość X", "mm", minimum=0.001, maximum=10000),
        Field("height", "float", "Długość Y", "mm", minimum=0.001, maximum=10000),
    )

    def check(self, v: dict[str, Any], step: int) -> list[Issue]:
        return _check(v, step, min(v["width"], v["height"]) - v["tool_d"])

    def _rings(self, v: dict[str, Any]) -> list[Polyline]:
        hx = (v["width"] - v["tool_d"]) / 2
        hy = (v["height"] - v["tool_d"]) / 2
        stride = v["tool_d"] * v["stepover"] / 100
        count = max(1, math.ceil(max(hx, hy) / stride))
        rings = []
        for k in range(1, count + 1):
            x, y = min(hx, k * stride), min(hy, k * stride)
            cx, cy = v["cx"], v["cy"]
            rings.append([(cx - x, cy - y), (cx + x, cy - y),
                          (cx + x, cy + y), (cx - x, cy + y), (cx - x, cy - y)])
        return rings

    def generate(self, v: dict[str, Any]) -> list[str]:
        lines = ["( Kieszen prostokatna: wejscie pionowe, symulacja wymagana )",
                 "G17 G90 G91.1 G94 G40 G80"]
        rings = self._rings(v)
        for z in _levels(v):
            lines += [f"G0 Z{fmt(v['safe_z'])}", f"G0 X{fmt(v['cx'])} Y{fmt(v['cy'])}",
                      f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
            for ring in rings:
                for x, y in ring:
                    lines.append(f"G1 X{fmt(x)} Y{fmt(y)} F{fmt(v['feed'])}")
        return lines + [f"G0 Z{fmt(v['safe_z'])}"]

    def preview_2d(self, v: dict[str, Any]) -> list[Polyline]:
        return self._rings(v)


class PocketCircle(BaseMacroGenerator):
    name = "pocket_circle"
    version = 1
    title = "Kieszeń okrągła (prototyp)"
    fields = COMMON + (
        Field("diameter", "float", "Średnica kieszeni", "mm", minimum=0.001, maximum=10000),
    )

    def check(self, v: dict[str, Any], step: int) -> list[Issue]:
        return _check(v, step, v["diameter"] - v["tool_d"])

    def _radii(self, v: dict[str, Any]) -> list[float]:
        maximum = (v["diameter"] - v["tool_d"]) / 2
        stride = v["tool_d"] * v["stepover"] / 100
        return [min(maximum, i * stride)
                for i in range(1, max(1, math.ceil(maximum / stride)) + 1)]

    def generate(self, v: dict[str, Any]) -> list[str]:
        cx, cy = v["cx"], v["cy"]
        lines = ["( Kieszen okragla: wejscie pionowe, symulacja wymagana )",
                 "G17 G90 G91.1 G94 G40 G80"]
        for z in _levels(v):
            lines += [f"G0 Z{fmt(v['safe_z'])}", f"G0 X{fmt(cx)} Y{fmt(cy)}",
                      f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
            for radius in self._radii(v):
                lines.append(f"G1 X{fmt(cx + radius)} Y{fmt(cy)} F{fmt(v['feed'])}")
                lines.append(f"G3 X{fmt(cx + radius)} Y{fmt(cy)} "
                             f"I{fmt(-radius)} J0 F{fmt(v['feed'])}")
        return lines + [f"G0 Z{fmt(v['safe_z'])}"]

    def preview_2d(self, v: dict[str, Any]) -> list[Polyline]:
        return [[(v["cx"] + r * math.cos(2 * math.pi * k / 64),
                  v["cy"] + r * math.sin(2 * math.pi * k / 64)) for k in range(65)]
                for r in self._radii(v)]


def register(registry=None) -> None:
    from .registry import DEFAULT_REGISTRY

    registry = registry or DEFAULT_REGISTRY
    for cls in (PocketRect, PocketCircle):
        if registry.get(cls.name, cls.version) is None:
            registry.register(cls)
