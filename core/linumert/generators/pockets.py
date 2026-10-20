"""Kieszenie prostokątne i okrągłe — wersja 2 (sesja 041, plan 21–22.10).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-21

UWAGA: wejście pionowe wymaga narzędzia skrawającego w osi; przed obróbką
wymagane sprawdzenie w symulacji LinuxCNC/Plant. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
from typing import Any

from .base import BaseMacroGenerator, Field, Issue, Polyline, fmt
from .pockets_v1 import PocketCircle as PocketCircleV1
from .pockets_v1 import PocketRect as PocketRectV1

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
    Field("entry", "choice", "Wejście", default="plunge",
          choices=("plunge", "ramp", "helix")),
    Field("entry_angle", "float", "Kąt rampy / helisy", "°", default=3.0,
          minimum=0.1, maximum=15.0),
    Field("direction", "choice", "Kierunek XY (M3)", default="ccw", choices=("ccw", "cw")),
    Field("wall_allowance", "float", "Naddatek ścian", "mm", default=0.0, minimum=0),
    Field("floor_allowance", "float", "Naddatek dna", "mm", default=0.0, minimum=0),
    Field("finish", "bool", "Wykonaj wykańczanie naddatków", default=False),
    Field("finish_feed", "float", "Posuw wykańczania", "mm/min", default=250.0,
          minimum=0, exclusive_minimum=True),
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
    layers = math.ceil(v["depth"] / v["step_down"]) + int(v["finish"])
    blocks = layers * (9 * rings + 15)
    if v["entry"] != "plunge" and clearance > 0:
        radius = _entry_radius(v)
        length = (math.pi if v["entry"] == "helix" else 2) * radius
        if round(radius, 4) <= 0:
            issues.append(Issue("P-5007", {"tool": 0, "what":
                                          "brak miejsca na rampę / helisę"}, "entry"))
        else:
            drop = length * math.tan(math.radians(v["entry_angle"]))
            blocks += layers * (
                math.ceil(min(v["depth"], v["step_down"]) / drop) + 5)
    if round(v["floor_allowance"], 4) >= round(v["depth"], 4):
        issues.append(Issue("P-5003", {"name": "floor_allowance",
                                      "value": fmt(v["floor_allowance"]),
                                      "limit": f"< {fmt(v['depth'])}"}, "floor_allowance"))
    if v["finish"] and v["floor_allowance"] > v["step_down"]:
        issues.append(Issue("P-5003", {"name": "floor_allowance",
                                      "value": fmt(v["floor_allowance"]),
                                      "limit": f"<= {fmt(v['step_down'])}"}, "floor_allowance"))
    if blocks > 20000:
        issues.append(Issue("P-5003", {"name": "liczba bloków", "value": str(blocks),
                                      "limit": "<= 20000"}, "step_down"))
    if round(clearance / 2, 4) <= 0:
        issues.append(Issue("P-5007", {"tool": 0, "what":
                                      "średnica frezu nie mieści się w kieszeni"}, "tool_d"))
    return issues


def _layer_pairs(v: dict[str, Any]):
    top = v["z_top"]
    for z in _levels(v):
        yield top, z
        top = z


def _entry_radius(v: dict[str, Any]) -> float:
    span = min(v["width"], v["height"]) if "width" in v else v["diameter"]
    # Średnica helisy <= D frezu: nie zostaje centralny rdzeń. Zaokrąglenie
    # w dół zachowuje obrys kieszeni także po zapisie G-code do 4 miejsc.
    return math.floor(min(v["tool_d"], span - v["tool_d"] -
                          2 * v["wall_allowance"]) * 5000) / 10000


def _point(v, x, y, *, vector=False):
    angle = math.radians(v.get("rotation", 0))
    c, s = math.cos(angle), math.sin(angle)
    return (c * x - s * y + (0 if vector else v["cx"]),
            s * x + c * y + (0 if vector else v["cy"]))


def _xy(v, x, y):
    x, y = _point(v, x, y)
    return f"X{fmt(x)} Y{fmt(y)}"


def _ij(v, x, y):
    x, y = _point(v, x, y, vector=True)
    return f"I{fmt(x)} J{fmt(y)}"


def _entry(v: dict[str, Any], top: float, z: float) -> list[str]:
    radius = _entry_radius(v)
    lines = [f"G0 Z{fmt(v['safe_z'])}"]
    if v["entry"] == "plunge":
        return lines + [f"G0 {_xy(v, 0, 0)}", f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
    sign = 1 if v["entry"] == "helix" else -1
    lines += [f"G0 {_xy(v, sign * radius, 0)}",
              f"G1 Z{fmt(top)} F{fmt(v['plunge'])}"]
    length = (math.pi if v["entry"] == "helix" else 2) * radius
    count = math.ceil((top - z) / (length * math.tan(math.radians(v["entry_angle"]))))
    for k in range(1, count + 1):
        target = top + (z - top) * k / count
        if v["entry"] == "helix":
            arc = "G3" if v["direction"] == "ccw" else "G2"
            lines.append(f"{arc} {_xy(v, -sign * radius, 0)} Z{fmt(target)} "
                         f"{_ij(v, -sign * radius, 0)} F{fmt(v['plunge'])}")
        else:
            lines.append(f"G1 {_xy(v, -sign * radius, 0)} Z{fmt(target)} "
                         f"F{fmt(v['plunge'])}")
        sign = -sign
    # Zakończenie na środku w poziomie; brak pionowego zagłębienia w materiał.
    return lines + [f"G1 {_xy(v, 0, 0)} F{fmt(v['feed'])}"]


def _entry_preview(v: dict[str, Any]) -> list[Polyline]:
    r = _entry_radius(v)
    if v["entry"] == "helix":
        return [[_point(v, r * math.cos(math.tau * k / 64),
                        r * math.sin(math.tau * k / 64)) for k in range(65)]]
    if v["entry"] == "ramp":
        return [[_point(v, -r, 0), _point(v, r, 0)]]
    return []


# Kontur: punkt końcowy i opcjonalny środek łuku, we współrzędnych lokalnych.
def _rect_path(hx, hy, radius, direction):
    r = min(radius, hx, hy)
    if r <= 0:
        points = [(-hx, -hy, None), (hx, -hy, None), (hx, hy, None),
                  (-hx, hy, None), (-hx, -hy, None)]
    else:
        points = [(-hx + r, -hy, None), (hx - r, -hy, None),
                  (hx, -hy + r, (hx - r, -hy + r)), (hx, hy - r, None),
                  (hx - r, hy, (hx - r, hy - r)), (-hx + r, hy, None),
                  (-hx, hy - r, (-hx + r, hy - r)), (-hx, -hy + r, None),
                  (-hx + r, -hy, (-hx + r, -hy + r))]
    if direction == "cw":
        points = [points[0]] + [(points[i - 1][0], points[i - 1][1], points[i][2])
                                for i in range(len(points) - 1, 0, -1)]
    # Przy R równym połowie wymiaru odcinki proste mogą mieć długość zero.
    return [point for i, point in enumerate(points)
            if i == 0 or point[:2] != points[i - 1][:2] or point[2] is not None]


def _emit_path(v, path, feed):
    lines = []
    previous = path[0][:2]
    for x, y, center in path:
        if center is None:
            lines.append(f"G1 {_xy(v, x, y)} F{fmt(feed)}")
        else:
            arc = "G3" if v["direction"] == "ccw" else "G2"
            lines.append(f"{arc} {_xy(v, x, y)} "
                         f"{_ij(v, center[0] - previous[0], center[1] - previous[1])} "
                         f"F{fmt(feed)}")
        previous = (x, y)
    return lines


def _preview_path(v, path):
    points = [path[0][:2]]
    for x, y, center in path[1:]:
        if center is None:
            points.append((x, y))
        else:
            start = points[-1]
            radius = math.hypot(start[0] - center[0], start[1] - center[1])
            a = math.atan2(start[1] - center[1], start[0] - center[0])
            b = math.atan2(y - center[1], x - center[0])
            sign = 1 if v["direction"] == "ccw" else -1
            sweep = ((sign * (b - a)) % math.tau or math.tau) * sign
            points.extend((center[0] + radius * math.cos(a + sweep * k / 64),
                           center[1] + radius * math.sin(a + sweep * k / 64))
                          for k in range(1, 65))
    return [_point(v, x, y) for x, y in points]


class _Pocket(BaseMacroGenerator):
    def _paths(self, v):
        raise NotImplementedError

    def generate(self, v):
        title = "Kieszen prostokatna" if self.name == "pocket_rect" else "Kieszen okragla"
        lines = [f"( {title}: wejscie {v['entry']}, symulacja wymagana )",
                 "G17 G90 G91.1 G94 G40 G80"]
        rough = {**v, "depth": v["depth"] - v["floor_allowance"]}
        final = {**v, "wall_allowance": 0.0}
        for top, z in _layer_pairs(rough):
            lines += _entry(rough, top, z)
            for path in self._paths(rough):
                lines += _emit_path(rough, path, v["feed"])
            if v["finish"]:
                lines += ["( wykanczanie scian )"]
                lines += _emit_path(final, self._paths(final)[-1], v["finish_feed"])
        if v["finish"] and v["floor_allowance"] > 0:
            lines += ["( wykanczanie dna )"]
            lines += _entry(final, v["z_top"] - rough["depth"], v["z_top"] - v["depth"])
            for path in self._paths(final):
                lines += _emit_path(final, path, v["finish_feed"])
        return lines + [f"G0 Z{fmt(v['safe_z'])}"]

    def preview_2d(self, v):
        paths = self._paths(v)
        if v["finish"]:
            paths += self._paths({**v, "wall_allowance": 0.0})
        return _entry_preview(v) + [_preview_path(v, path) for path in paths]


class PocketRect(_Pocket):
    name = "pocket_rect"
    version = 2
    title = "Kieszeń prostokątna"
    fields = COMMON + (
        Field("width", "float", "Szerokość X", "mm", minimum=0.001, maximum=10000),
        Field("height", "float", "Długość Y", "mm", minimum=0.001, maximum=10000),
        Field("rotation", "float", "Obrót XY", "°", default=0.0, minimum=-360, maximum=360),
        Field("corner_radius", "float", "Promień naroża (0 = D/2)", "mm", default=0.0, minimum=0),
    )

    def check(self, v, step):
        clearance = min(v["width"], v["height"]) - v["tool_d"] - 2 * v["wall_allowance"]
        issues = _check(v, step, clearance)
        r = v["corner_radius"] or v["tool_d"] / 2
        if r < v["tool_d"] / 2 or r > min(v["width"], v["height"]) / 2:
            issues.append(Issue("P-5003", {"name": "corner_radius", "value": fmt(r),
                                          "limit": "D/2 <= R <= min(X,Y)/2"}, "corner_radius"))
        elif 0 < r - v["tool_d"] / 2 < 0.0001:
            issues.append(Issue("P-5003", {"name": "corner_radius", "value": fmt(r),
                                          "limit": "R = D/2 lub R >= D/2 + 0.0001"},
                                "corner_radius"))
        return issues

    def _paths(self, v):
        hx = (v["width"] - v["tool_d"]) / 2 - v["wall_allowance"]
        hy = (v["height"] - v["tool_d"]) / 2 - v["wall_allowance"]
        r = max(0, (v["corner_radius"] or v["tool_d"] / 2) -
                v["tool_d"] / 2 - v["wall_allowance"])
        # Oba wymiary rosną jednocześnie: odstęp po przekątnej też musi
        # pozostać mniejszy od średnicy frezu, również przy 90% stepover.
        stride = v["tool_d"] * v["stepover"] / (100 * math.sqrt(2))
        count = max(1, math.ceil(max(hx, hy) / stride))
        return [_rect_path(min(hx, k * stride), min(hy, k * stride), r, v["direction"])
                for k in range(1, count + 1)]


class PocketCircle(_Pocket):
    name = "pocket_circle"
    version = 2
    title = "Kieszeń okrągła"
    fields = COMMON + (
        Field("diameter", "float", "Średnica kieszeni", "mm", minimum=0.001, maximum=10000),
    )

    def check(self, v, step):
        return _check(v, step, v["diameter"] - v["tool_d"] - 2 * v["wall_allowance"])

    def _paths(self, v):
        maximum = (v["diameter"] - v["tool_d"]) / 2 - v["wall_allowance"]
        stride = v["tool_d"] * v["stepover"] / 100
        radii = [min(maximum, i * stride)
                 for i in range(1, max(1, math.ceil(maximum / stride)) + 1)]
        return [[(r, 0, None), (r, 0, (0, 0))] for r in radii]


def register(registry=None) -> None:
    from .registry import DEFAULT_REGISTRY

    registry = registry or DEFAULT_REGISTRY
    for cls in (PocketRectV1, PocketCircleV1, PocketRect, PocketCircle):
        if registry.get(cls.name, cls.version) is None:
            registry.register(cls)
