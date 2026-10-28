"""Walidacja kroków programu dialogowego z bazą narzędzi (sesja 040 p.2).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-20

Krok `tool_change` ustala bieżące narzędzie; kolejne kroki sprawdzane są z jego danymi z bazy
(`linumert.tools.db.ToolDB.get` albo dowolna funkcja numer → Tool | None):

- typ narzędzia pasuje do operacji (P-5207); narzędzie bez typu nie jest odrzucane — symulacja
  zgłasza dla niego K-320, a tu nie ma czego porównać,
- średnica w formularzu = średnica narzędzia (P-5208), skok gwintu = skok gwintownika,
- głębokość przejścia nie przekracza długości ostrza / wysokości głowicy (P-5209),
- obroty ≤ max_rpm i kierunek M3/M4 zgodny z `hand` (P-5210, P-5211),
- narzędzie z `tool_change` istnieje w bazie (P-5206).

Baza trzyma milimetry; program w calach jest przeliczany przed porównaniem.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import Issue, fmt
from .basic import FaceMill
from .drilling import DrillHoles

ToolLookup = Callable[[int], Any]

MILLING = ("flat", "bull", "ball", "face_mill")
DRILLS = ("drill_118", "drill_angle")
TAPS = ("tap",)
DIAMETER_TOL = 0.01  # mm
# Etykiety pól z formularzy generatorów — komunikat mówi językiem ekranu, nie nazwą parametru
LABELS = {f.name: f.label for cls in (FaceMill, DrillHoles) for f in cls.fields}


def _cutting_length(tool) -> float | None:
    p = tool.params
    if tool.type == "face_mill":
        return p.get("h")
    return p.get("flute_length")


def _type_issue(step: int, tool, allowed: tuple[str, ...]) -> list[Issue]:
    if tool.type is None or tool.type in allowed:
        return []
    return [Issue("P-5207", {"step": step, "tool": tool.number, "type": tool.type,
                             "allowed": ", ".join(allowed)})]


def _length_issue(step: int, tool, name: str, value: float) -> list[Issue]:
    limit = _cutting_length(tool)
    if limit is None or value <= limit + 1e-9:
        return []
    return [Issue("P-5209", {"step": step, "tool": tool.number, "field": LABELS.get(name, name),
                             "value": fmt(value), "limit": fmt(limit)}, name)]


def _face_mill(step: int, v: dict[str, Any], tool, k: float) -> list[Issue]:
    issues = _type_issue(step, tool, MILLING)
    d = tool.tool_diameter()
    if d is not None and abs(v["tool_d"] * k - d) > DIAMETER_TOL:
        issues.append(Issue("P-5208", {"step": step, "tool": tool.number, "field": LABELS["tool_d"],
                                       "value": fmt(v["tool_d"]), "expected": f"D = {fmt(d)} mm"},
                            "tool_d"))
    return issues + _length_issue(step, tool, "step_down", v["step_down"] * k)


def _drill_holes(step: int, v: dict[str, Any], tool, k: float) -> list[Issue]:
    tapping = v["cycle"] == "G33.1"
    issues = _type_issue(step, tool, TAPS if tapping else DRILLS)
    if tapping and tool.type == "tap" and "pitch" in tool.params:
        if abs(v["pitch"] * k - tool.params["pitch"]) > 1e-6:
            issues.append(Issue("P-5208", {"step": step, "tool": tool.number,
                                           "field": LABELS["pitch"],
                                           "value": fmt(v["pitch"]),
                                           "expected": f"skok {fmt(tool.params['pitch'])} mm"},
                                "pitch"))
    return issues + _length_issue(step, tool, "depth", v["depth"] * k)


def _spindle(step: int, v: dict[str, Any], tool) -> list[Issue]:
    issues = []
    limit = tool.params.get("max_rpm")
    if limit and v["rpm"] > limit:
        issues.append(Issue("P-5210", {"step": step, "tool": tool.number,
                                       "rpm": str(round(v["rpm"])), "limit": fmt(limit, 0)},
                            "rpm"))
    hand = tool.params.get("hand")
    if v["rpm"] > 0 and hand in (1, -1):
        expected = "M3" if hand == 1 else "M4"
        if v["direction"] != expected:
            issues.append(Issue("P-5211", {"step": step, "tool": tool.number,
                                           "direction": v["direction"], "expected": expected},
                                "direction"))
    return issues


CHECKS = {"face_mill": _face_mill, "drill_holes": _drill_holes,
          "pocket_rect": _face_mill, "pocket_circle": _face_mill}


def _engraving(step, v, tool, k):
    if tool.type == "chamfer":
        return _length_issue(step, tool, "step_down", v["step_down"] * k)
    return _face_mill(step, v, tool, k)


CHECKS.update(dict.fromkeys(("shape_engrave", "engrave_text", "path_trace", "stl_section"),
                           _engraving))


def check_steps(steps: list[tuple[int, str, dict[str, Any]]], lookup: ToolLookup,
                units: str = "mm") -> list[Issue]:
    """Kroki (numer, nazwa generatora, znormalizowane parametry) → błędy względem bazy."""
    k = 25.4 if units == "inch" else 1.0
    issues: list[Issue] = []
    current = None
    for number, name, values in steps:
        if name == "tool_change":
            current = lookup(values["tool"])
            if current is None:
                issues.append(Issue("P-5206", {"tool": values["tool"]}, "tool"))
                continue
            issues += _spindle(number, values, current)
        elif current is not None and name in CHECKS:
            issues += CHECKS[name](number, values, current, k)
    return issues
