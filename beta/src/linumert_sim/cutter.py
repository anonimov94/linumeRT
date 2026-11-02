"""Bryła narzędzia w symulacji: profil części tnącej, szyjka, oprawka (NARZEDZIA_I_KOLIZJE.md §1).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

Układ narzędzia: oś Z w górę, 0 = wierzchołek narzędzia (punkt prowadzony). Od dołu:
część tnąca 0…`cut_top` (profil `lower(r)` = wysokość najniższej powierzchni tnącej nad
wierzchołkiem w odległości r od osi), szyjka/chwyt `cut_top`…`stickout` (promień `neck_r`,
nie tnie), oprawka `stickout`…`gauge` (promień `holder_r`, nie tnie). `gauge` = długość z tool.tbl
(Z) = odległość wierzchołka od nosa wrzeciona. Powyżej nosa leżą bryły wrzeciona z machine.yaml.

Model 2.5D (mapa wysokości) nie przechowuje podcięć: frez teowy i lizakowy usuwają w nim cały
słup materiału nad tarczą/kulą; `undercut = True` daje ostrzeżenie w zdarzeniach.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULT_HOLDER_D = 32.0   # [mm] typowa nakrętka tulejki ER20/ER25
DEFAULT_HOLDER_L = 30.0   # [mm]


@dataclass(frozen=True)
class Cutter:
    number: int
    kind: str                 # id typu z linumert.tools.types albo "cylinder" (brak geometrii)
    radius: float             # promień tnący z korekcją średnicy [mm]
    cut_top: float            # wysokość części tnącej [mm]
    neck_r: float             # promień części nietnącej nad ostrzem [mm]
    stickout: float           # wysięg z oprawki [mm]
    gauge: float              # wierzchołek → nos wrzeciona (tool.tbl Z) [mm]
    holder_r: float
    flutes: int = 2
    max_rpm: float | None = None
    hand: int = 1             # 1 = prawe (M3), -1 = lewe (M4)
    corner: float = 0.0       # promień naroża (bull)
    cone_tan: float = 0.0     # tan(połowy kąta wierzchołkowego) dla stożka (0 = brak)
    undercut: bool = False
    substitute: bool = False  # walec zastępczy (K-320)

    @property
    def diameter(self) -> float:
        return 2 * self.radius

    def lower(self, r: np.ndarray) -> np.ndarray:
        """Wysokość powierzchni tnącej nad wierzchołkiem; +inf poza promieniem tnącym."""
        r = np.asarray(r, dtype=float)
        R = self.radius
        out = np.full(r.shape, np.inf)
        inside = r <= R
        ri = r[inside]
        if self.kind in ("ball", "lollipop"):
            h = R - np.sqrt(np.maximum(R * R - ri * ri, 0.0))
        elif self.kind == "bull" and self.corner > 0:
            flat = R - self.corner
            d = np.maximum(ri - flat, 0.0)
            h = self.corner - np.sqrt(np.maximum(self.corner ** 2 - d * d, 0.0))
        elif self.cone_tan > 0:
            h = ri / self.cone_tan
        else:
            h = np.zeros_like(ri)
        out[inside] = h
        return out

    def parts(self) -> list[tuple[str, float, float, float]]:
        """Walce nietnące (nazwa, promień, z od, z do) względem wierzchołka."""
        out = []
        if self.stickout > self.cut_top:
            out.append(("szyjka", self.neck_r, self.cut_top, self.stickout))
        if self.gauge > self.stickout:
            out.append(("oprawka", self.holder_r, self.stickout, self.gauge))
        return out


def _f(params: dict, name: str, default: float | None = None) -> float | None:
    value = params.get(name, default)
    return None if value is None else float(value)


def make_cutter(number: int, gauge: float, diameter: float, kind: str | None = None,
                params: dict | None = None) -> Cutter:
    """Narzędzie z tool.tbl (Z = `gauge`, D) i opcjonalnie z bazy narzędzi (typ, parametry)."""
    p = dict(params or {})
    d = _f(p, "d", diameter) or diameter
    wear = max(-1.0, min(1.0, _f(p, "d_wear", 0.0) or 0.0))
    radius = max((d + wear) / 2, 0.05)
    holder_r = (_f(p, "holder_d", None) or max(DEFAULT_HOLDER_D, 2 * radius + 12)) / 2
    holder_l = _f(p, "holder_l", DEFAULT_HOLDER_L) or DEFAULT_HOLDER_L
    gauge = gauge if gauge > 0 else (_f(p, "l", 4 * d) or 4 * d) + holder_l
    stickout = _f(p, "l", None) or max(gauge - holder_l, 1.0)
    stickout = min(stickout, gauge)
    common = dict(number=number, gauge=gauge, holder_r=holder_r,
                  flutes=int(_f(p, "flutes", 2) or 2), max_rpm=_f(p, "max_rpm", None),
                  hand=-1 if (_f(p, "hand", 1) or 1) < 0 else 1)
    if kind is None or kind == "special_stl":
        # Brak geometrii (albo STL): walec zastępczy D × wysięg, cały tnący (K-320)
        return Cutter(kind="cylinder", radius=radius, cut_top=stickout, neck_r=radius,
                      stickout=stickout, substitute=True, **common)
    flute = _f(p, "flute_length", None)
    if kind == "flat":
        return Cutter(kind=kind, radius=radius, cut_top=min(flute or stickout, stickout),
                      neck_r=radius, stickout=stickout, **common)
    if kind == "ball":
        return Cutter(kind=kind, radius=radius, cut_top=min(flute or 2 * d, stickout),
                      neck_r=radius, stickout=stickout, **common)
    if kind == "bull":
        return Cutter(kind=kind, radius=radius, cut_top=min(flute or 2 * d, stickout),
                      neck_r=radius, stickout=stickout,
                      corner=min(_f(p, "corner_radius", 0.0) or 0.0, radius), **common)
    if kind in ("chamfer", "drill_118", "drill_angle"):
        angle = 118.0 if kind == "drill_118" else (_f(p, "angle", 90.0) or 90.0)
        if angle >= 180:  # wiertło płaskie
            tan = 0.0
            tip_h = 0.0
        else:
            tan = math.tan(math.radians(angle / 2))
            tip_h = radius / tan
        top = tip_h if kind == "chamfer" else (flute or max(stickout * 0.8, tip_h))
        return Cutter(kind=kind, radius=radius, cut_top=min(max(top, tip_h), stickout),
                      neck_r=radius, stickout=stickout, cone_tan=tan, **common)
    if kind == "face_mill":
        h = _f(p, "h", 10.0) or 10.0
        return Cutter(kind=kind, radius=radius, cut_top=min(h, stickout),
                      neck_r=min(radius, 20.0), stickout=stickout, **common)
    if kind == "tslot":
        width = _f(p, "width", 3.0) or 3.0
        neck_r = (_f(p, "neck_d", d / 2) or d / 2) / 2
        return Cutter(kind=kind, radius=radius, cut_top=min(width, stickout), neck_r=neck_r,
                      stickout=stickout, undercut=True, **common)
    if kind == "lollipop":
        neck_r = (_f(p, "neck_d", d / 2) or d / 2) / 2
        return Cutter(kind=kind, radius=radius, cut_top=min(2 * radius, stickout), neck_r=neck_r,
                      stickout=stickout, undercut=True, **common)
    if kind == "tap":
        return Cutter(kind=kind, radius=radius, cut_top=min(flute or 2.5 * d, stickout),
                      neck_r=radius * 0.8, stickout=stickout, **common)
    return Cutter(kind="cylinder", radius=radius, cut_top=stickout, neck_r=radius,
                  stickout=stickout, substitute=True, **common)
