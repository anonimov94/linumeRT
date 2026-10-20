"""Generator otworów: wzory pozycji i cykle wiercenia LinuxCNC (sesja 042).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19

Wzory: pojedynczy, lista („x,y; x,y”), rząd (n otworów co krok pod kątem), siatka (nx × ny),
okrąg (n równo na 360°), łuk (n od kąta początkowego przez zakres). Cykle: G81 (wiercenie),
G82 (z postojem P), G83 (z wycofaniem Q), G73 (łamanie wióra Q), G84 nie istnieje w LinuxCNC 2.9 —
gwintowanie sztywne G33.1 przy `spindle_sync` (wymaga enkodera wrzeciona), bez niego błąd.
Płaszczyzna R, powrót G98/G99, na końcu G80. Pozycje w układzie detalu, G90.
"""

from __future__ import annotations

import math
import re
from typing import Any

from .base import BaseMacroGenerator, Field, Issue, Polyline, fmt

PATTERNS = ("single", "list", "row", "grid", "circle", "arc")
CYCLES = ("G81", "G82", "G83", "G73", "G33.1")
_PAIR = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$")


def parse_points(text: str) -> list[tuple[float, float]]:
    """„x,y; x,y …” → lista punktów (ValueError z numerem pozycji)."""
    out = []
    for i, part in enumerate(p for p in text.split(";") if p.strip()):
        m = _PAIR.match(part)
        if m is None:
            raise ValueError(f"pozycja {i + 1}: oczekiwano „x,y”, jest „{part.strip()}”")
        out.append((float(m.group(1)), float(m.group(2))))
    return out


def pattern_points(v: dict[str, Any]) -> list[tuple[float, float]]:
    """Pozycje otworów dla parametrów generatora (po `normalize`)."""
    kind, x, y = v["pattern"], v["x"], v["y"]
    if kind == "single":
        return [(x, y)]
    if kind == "list":
        return parse_points(v["points"])
    if kind == "row":
        a = math.radians(v["angle"])
        return [(x + i * v["dx"] * math.cos(a), y + i * v["dx"] * math.sin(a))
                for i in range(v["count"])]
    if kind == "grid":
        return [(x + i * v["dx"], y + j * v["dy"]) for j in range(v["rows"])
                for i in range(v["count"])]
    n, r = v["count"], v["radius"]
    if kind == "circle":
        start, step = v["angle"], 360.0 / n
    else:
        start = v["angle"]
        step = v["sweep"] / (n - 1) if n > 1 else 0.0
    return [(x + r * math.cos(math.radians(start + i * step)),
             y + r * math.sin(math.radians(start + i * step))) for i in range(n)]


class DrillHoles(BaseMacroGenerator):
    name = "drill_holes"
    version = 1
    title = "Otwory: wiercenie i gwintowanie"
    fields = (
        Field("pattern", "choice", "Wzór", default="single", choices=PATTERNS),
        Field("x", "float", "X (start / środek)", "mm", default=0.0),
        Field("y", "float", "Y (start / środek)", "mm", default=0.0),
        Field("points", "text", "Lista pozycji „x,y; x,y”", default=""),
        Field("count", "int", "Liczba otworów (w rzędzie)", default=1, minimum=1, maximum=1000),
        Field("rows", "int", "Liczba rzędów (siatka)", default=1, minimum=1, maximum=1000),
        Field("dx", "float", "Krok X / w rzędzie", "mm", default=10.0),
        Field("dy", "float", "Krok Y", "mm", default=10.0),
        Field("radius", "float", "Promień (okrąg, łuk)", "mm", default=10.0, minimum=0,
              exclusive_minimum=True),
        Field("angle", "float", "Kąt początkowy / kierunek rzędu", "°", default=0.0),
        Field("sweep", "float", "Zakres łuku", "°", default=90.0, minimum=-360, maximum=360),
        Field("cycle", "choice", "Cykl", default="G81", choices=CYCLES),
        Field("z_top", "float", "Z powierzchni", "mm", default=0.0),
        Field("depth", "float", "Głębokość", "mm", minimum=0, exclusive_minimum=True,
              maximum=500),
        Field("r_plane", "float", "Płaszczyzna R nad powierzchnią", "mm", default=2.0,
              minimum=0, exclusive_minimum=True, maximum=100),
        Field("peck", "float", "Krok wiercenia Q (G83, G73)", "mm", default=2.0, minimum=0,
              exclusive_minimum=True),
        Field("dwell", "float", "Postój P (G82)", "s", default=0.5, minimum=0),
        Field("feed", "float", "Posuw F", "mm/min", default=100.0, minimum=0,
              exclusive_minimum=True),
        Field("pitch", "float", "Skok gwintu (G33.1)", "mm", default=1.0, minimum=0,
              exclusive_minimum=True, maximum=10),
        Field("retract", "choice", "Powrót", default="G98", choices=("G98", "G99")),
        Field("spindle_sync", "bool", "Wrzeciono z enkoderem (gwintowanie sztywne)",
              default=False),
    )

    def check(self, v: dict[str, Any], step: int) -> list[Issue]:
        issues = []
        if v["pattern"] == "list":
            try:
                if not parse_points(v["points"]):
                    issues.append(Issue("P-5014", {"step": step, "field": "points"}, "points"))
            except ValueError as exc:
                issues.append(Issue("P-5015", {"step": step, "field": "points",
                                               "expected": str(exc)}, "points"))
        if v["pattern"] in ("circle", "arc") and v["count"] < 2:
            issues.append(Issue("P-5003", {"name": "count", "value": str(v["count"]),
                                           "limit": ">= 2 dla okręgu i łuku"}, "count"))
        if v["cycle"] == "G33.1" and not v["spindle_sync"]:
            issues.append(Issue("P-5007", {"tool": 0, "what": "gwintowanie sztywne G33.1 "
                                           "wymaga wrzeciona z enkoderem (spindle_sync)"},
                                "spindle_sync"))
        if v["cycle"] in ("G83", "G73") and v["peck"] > v["depth"]:
            issues.append(Issue("P-5003", {"name": "peck", "value": fmt(v["peck"]),
                                           "limit": f"<= głębokość {fmt(v['depth'])} mm"},
                                "peck"))
        return issues

    def generate(self, v: dict[str, Any]) -> list[str]:
        pts = pattern_points(v)
        z = v["z_top"] - v["depth"]
        r = v["z_top"] + v["r_plane"]
        lines = [f"( Otwory: {v['pattern']} x{len(pts)}, {v['cycle']}, Z{fmt(z)} )", "G90"]
        if v["cycle"] == "G33.1":
            for px, py in pts:
                lines += [f"G0 X{fmt(px)} Y{fmt(py)}", f"G0 Z{fmt(r)}",
                          f"G33.1 Z{fmt(z)} K{fmt(v['pitch'])}", f"G0 Z{fmt(r)}"]
            return lines
        words = {"G81": "", "G82": f" P{fmt(v['dwell'])}", "G83": f" Q{fmt(v['peck'])}",
                 "G73": f" Q{fmt(v['peck'])}"}[v["cycle"]]
        (fx, fy), rest = pts[0], pts[1:]
        lines.append(f"G0 Z{fmt(r)}")
        lines.append(f"{v['retract']} {v['cycle']} X{fmt(fx)} Y{fmt(fy)} Z{fmt(z)} "
                     f"R{fmt(r)}{words} F{fmt(v['feed'])}")
        lines += [f"X{fmt(px)} Y{fmt(py)}" for px, py in rest]
        lines.append("G80")
        return lines

    def preview_2d(self, v: dict[str, Any]) -> list[Polyline]:
        """Krzyżyk na każdym otworze (±2 mm)."""
        out: list[Polyline] = []
        for px, py in pattern_points(v):
            out += [[(px - 2, py), (px + 2, py)], [(px, py - 2), (px, py + 2)]]
        return out


def register(registry=None) -> None:
    """Rejestracja w rejestrze (domyślnie DEFAULT_REGISTRY), bez dublowania."""
    from .registry import DEFAULT_REGISTRY

    registry = registry or DEFAULT_REGISTRY
    if registry.get(DrillHoles.name, DrillHoles.version) is None:
        registry.register(DrillHoles)
