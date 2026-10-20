"""Generatory podstawowe: nagłówek, koniec programu, wymiana narzędzia, planowanie (sesja 040).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19

Zasady jak w `base.py`: wyłącznie tekst G-code LinuxCNC, bez M2/M30 (koniec programu dopisuje
kompilator — `program_end` daje tylko zatrzymanie wrzeciona, chłodziwa i wycofanie), wynik zależy
tylko od parametrów i wersji. Przygotówka w nagłówku: linia `;@STOCK` (CLAUDE.md §8).
"""

from __future__ import annotations

import math
from typing import Any

from .base import BaseMacroGenerator, Field, Issue, Polyline, fmt

OFFSETS = ("G54", "G55", "G56", "G57", "G58", "G59")


class Header(BaseMacroGenerator):
    name = "header"
    version = 1
    title = "Nagłówek programu"
    fields = (
        Field("title", "text", "Opis programu", default=""),
        Field("units", "choice", "Jednostki", default="G21", choices=("G21", "G20")),
        Field("offset", "choice", "Układ detalu", default="G54", choices=OFFSETS),
        Field("stock", "text", "Przygotówka (linia ;@STOCK, opcjonalnie)", default=""),
    )

    def check(self, v: dict[str, Any], step: int) -> list[Issue]:
        if v["stock"] and not v["stock"].upper().startswith(";@STOCK"):
            return [Issue("P-5015", {"step": step, "field": "stock",
                                     "expected": "linia zaczynająca się od ;@STOCK"}, "stock")]
        return []

    def generate(self, v: dict[str, Any]) -> list[str]:
        lines = [f"( {v['title']} )"] if v["title"] else []
        if v["stock"]:
            lines.append(v["stock"])
        lines += [f"{v['units']} G90 G17 G40 G49 G80 G94 {v['offset']}", "G53 G0 Z0"]
        return lines


class ProgramEnd(BaseMacroGenerator):
    name = "program_end"
    version = 1
    title = "Koniec programu"
    fields = (
        Field("retract", "choice", "Wycofanie", default="z_home",
              choices=("z_home", "z_home_xy", "none")),
        Field("park_x", "float", "Parkowanie X (G53)", "mm", default=0.0),
        Field("park_y", "float", "Parkowanie Y (G53)", "mm", default=0.0),
    )

    def generate(self, v: dict[str, Any]) -> list[str]:
        lines = ["M5", "M9"]
        if v["retract"] != "none":
            lines.append("G53 G0 Z0")
        if v["retract"] == "z_home_xy":
            lines.append(f"G53 G0 X{fmt(v['park_x'])} Y{fmt(v['park_y'])}")
        return lines


class ToolChange(BaseMacroGenerator):
    name = "tool_change"
    version = 1
    title = "Wymiana narzędzia"
    fields = (
        Field("tool", "int", "Narzędzie T", minimum=1, maximum=99999),
        Field("rpm", "float", "Obroty S", "obr/min", default=0.0, minimum=0, maximum=100000),
        Field("direction", "choice", "Kierunek", default="M3", choices=("M3", "M4")),
        Field("coolant", "choice", "Chłodziwo", default="off", choices=("off", "M7", "M8")),
        Field("safe_z", "float", "Z po wymianie", "mm", default=10.0),
    )

    def generate(self, v: dict[str, Any]) -> list[str]:
        t = v["tool"]
        lines = ["M5", "G53 G0 Z0", f"T{t} M6", f"G43 H{t}"]
        if v["rpm"] > 0:
            lines.append(f"S{round(v['rpm'])} {v['direction']}")
        if v["coolant"] != "off":
            lines.append(v["coolant"])
        lines.append(f"G0 Z{fmt(v['safe_z'])}")
        return lines


class FaceMill(BaseMacroGenerator):
    name = "face_mill"
    version = 1
    title = "Planowanie"
    fields = (
        Field("x0", "float", "X min", "mm", default=0.0),
        Field("y0", "float", "Y min", "mm", default=0.0),
        Field("x1", "float", "X max", "mm"),
        Field("y1", "float", "Y max", "mm"),
        Field("z_top", "float", "Z powierzchni", "mm", default=0.0),
        Field("depth", "float", "Głębokość całkowita", "mm", minimum=0, exclusive_minimum=True,
              maximum=50),
        Field("step_down", "float", "Głębokość przejścia", "mm", default=1.0, minimum=0,
              exclusive_minimum=True),
        Field("tool_d", "float", "Średnica narzędzia", "mm", minimum=0, exclusive_minimum=True),
        Field("stepover", "float", "Krok boczny", "% D", default=70.0, minimum=5, maximum=95),
        Field("overrun", "float", "Wybieg poza krawędź", "mm", default=2.0, minimum=0),
        Field("mode", "choice", "Kierunek", default="zigzag", choices=("zigzag", "one_way")),
        Field("feed", "float", "Posuw F", "mm/min", default=800.0, minimum=0,
              exclusive_minimum=True),
        Field("plunge", "float", "Posuw wgłębny", "mm/min", default=200.0, minimum=0,
              exclusive_minimum=True),
        Field("safe_z", "float", "Bezpieczna Z", "mm", default=5.0),
    )

    def check(self, v: dict[str, Any], step: int) -> list[Issue]:
        issues = []
        for a, b in (("x0", "x1"), ("y0", "y1")):
            if v[b] <= v[a]:
                issues.append(Issue("P-5003", {"name": b, "value": fmt(v[b]),
                                               "limit": f"> {a} = {fmt(v[a])}"}, b))
        if v["safe_z"] <= v["z_top"]:
            issues.append(Issue("P-5003", {"name": "safe_z", "value": fmt(v["safe_z"]),
                                           "limit": f"> Z powierzchni {fmt(v['z_top'])}"},
                                "safe_z"))
        return issues

    def _passes(self, v) -> list[tuple[float, float, float]]:
        """Przejścia (y, x_od, x_do) jednej warstwy."""
        r = v["tool_d"] / 2
        step = v["tool_d"] * v["stepover"] / 100
        xa, xb = v["x0"] - r - v["overrun"], v["x1"] + r + v["overrun"]
        n = max(1, math.ceil((v["y1"] - v["y0"]) / step) + 1)
        ys = [min(v["y0"] + i * step, v["y1"]) for i in range(n)]
        out = []
        for i, y in enumerate(ys):
            forward = v["mode"] == "one_way" or i % 2 == 0
            out.append((y, xa, xb) if forward else (y, xb, xa))
        return out

    def generate(self, v: dict[str, Any]) -> list[str]:
        layers = max(1, math.ceil(v["depth"] / v["step_down"] - 1e-9))
        passes = self._passes(v)
        lines = [f"( Planowanie {fmt(v['depth'])} mm, {layers} warstw, {len(passes)} przejść )"]
        for k in range(1, layers + 1):
            z = v["z_top"] - min(k * v["step_down"], v["depth"])
            y, xs, _xe = passes[0]
            lines += [f"G0 Z{fmt(v['safe_z'])}", f"G0 X{fmt(xs)} Y{fmt(y)}",
                      f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
            for i, (y, xs, xe) in enumerate(passes):
                if i:
                    if v["mode"] == "one_way":
                        lines += [f"G0 Z{fmt(v['safe_z'])}", f"G0 X{fmt(xs)} Y{fmt(y)}",
                                  f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
                    else:
                        lines.append(f"G1 Y{fmt(y)} F{fmt(v['feed'])}")
                lines.append(f"G1 X{fmt(xe)} F{fmt(v['feed'])}")
        lines.append(f"G0 Z{fmt(v['safe_z'])}")
        return lines

    def preview_2d(self, v: dict[str, Any]) -> list[Polyline]:
        pts = []
        for y, xs, xe in self._passes(v):
            pts += [(xs, y), (xe, y)]
        return [pts]


GENERATORS = (Header, ProgramEnd, ToolChange, FaceMill)


def register(registry=None) -> None:
    from .registry import DEFAULT_REGISTRY

    registry = registry or DEFAULT_REGISTRY
    for cls in GENERATORS:
        if registry.get(cls.name, cls.version) is None:
            registry.register(cls)
