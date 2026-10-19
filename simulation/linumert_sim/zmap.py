"""Materiał przygotówki 2.5D: mapa wysokości (Z-map) i usuwanie materiału przejazdem narzędzia.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

Siatka w układzie maszyny (wierzchołek narzędzia, mm), komórka `cell` × `cell`. `h[iy, ix]` =
górna powierzchnia materiału w komórce; komórka pusta = -inf (poza walcem przygotówki albo
przecięta do dna). Dno przygotówki `z_bottom`: materiał poniżej dna nie istnieje (tam jest stół
albo mocowanie — kolizje z nimi liczy `machine.py`). Przejazd p0 → p1 próbkowany co ≤ pół komórki;
na każdej próbce część tnąca obniża mapę do profilu `Cutter.lower(r)`, a części nietnące
(szyjka, oprawka, wrzeciono) zgłaszają kontakt, gdy materiał sięga ponad ich dolną krawędź.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .cutter import Cutter

EPS = 1e-3          # [mm] zagłębienie uznawane za kontakt
MAX_CELLS = 1_200_000


@dataclass
class CutResult:
    removed: float = 0.0                       # [mm³]
    parts: set[str] = field(default_factory=set)  # części nietnące w materiale
    contact_at: tuple[float, float, float] | None = None  # pierwsza próbka z kontaktem

    def merge(self, other: CutResult) -> None:
        self.removed += other.removed
        self.parts |= other.parts
        if self.contact_at is None:
            self.contact_at = other.contact_at


class StockMap:
    """Przygotówka BOX albo CYL (oś Z) w układzie maszyny."""

    def __init__(self, shape: str, x0: float, y0: float, x1: float, y1: float,
                 z_bottom: float, z_top: float, cell: float = 0.5):
        if x1 <= x0 or y1 <= y0 or z_top <= z_bottom:
            raise ValueError("przygotówka: wymiary muszą być dodatnie")
        area = (x1 - x0) * (y1 - y0)
        cell = max(cell, math.sqrt(area / MAX_CELLS))
        self.shape, self.cell = shape, cell
        self.x0, self.y0 = x0, y0
        self.nx = max(int(math.ceil((x1 - x0) / cell)), 1)
        self.ny = max(int(math.ceil((y1 - y0) / cell)), 1)
        self.x1, self.y1 = x0 + self.nx * cell, y0 + self.ny * cell
        self.z_bottom, self.z_top = z_bottom, z_top
        self.xs = x0 + (np.arange(self.nx) + 0.5) * cell
        self.ys = y0 + (np.arange(self.ny) + 0.5) * cell
        self.h = np.empty((self.ny, self.nx), dtype=np.float32)
        self.version = 0
        self.reset()

    def reset(self) -> None:
        self.h.fill(self.z_top)
        if self.shape == "CYL":
            cx, cy = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2
            r = min(self.x1 - self.x0, self.y1 - self.y0) / 2
            xx, yy = np.meshgrid(self.xs - cx, self.ys - cy)
            self.h[xx * xx + yy * yy > r * r] = -np.inf
        self.version += 1

    @property
    def top(self) -> float:
        """Najwyższy punkt materiału (szybkie odrzucenie przejazdów nad przygotówką)."""
        m = float(np.max(self.h))
        return m if math.isfinite(m) else -math.inf

    def volume(self) -> float:
        h = np.clip(self.h, self.z_bottom, None)
        return float(np.sum(h - self.z_bottom)) * self.cell * self.cell

    def display(self) -> np.ndarray:
        """Wysokości do widoku: puste komórki = dno."""
        return np.where(np.isfinite(self.h), np.maximum(self.h, self.z_bottom),
                        self.z_bottom).astype(np.float32)

    def cut(self, cutter: Cutter, p0, p1, extra_parts=()) -> CutResult:
        """Przejazd wierzchołka p0 → p1; `extra_parts` = dodatkowe walce nietnące (wrzeciono)."""
        res = CutResult()
        parts = list(cutter.parts()) + list(extra_parts)
        reach = max([cutter.radius] + [p[1] for p in parts])
        lo_x, hi_x = min(p0[0], p1[0]) - reach, max(p0[0], p1[0]) + reach
        lo_y, hi_y = min(p0[1], p1[1]) - reach, max(p0[1], p1[1]) + reach
        if hi_x < self.x0 or lo_x > self.x1 or hi_y < self.y0 or lo_y > self.y1:
            return res
        if min(p0[2], p1[2]) > self.top + EPS:
            return res
        dist = math.dist(p0, p1)
        step = max(min(self.cell * 0.5, cutter.radius * 0.5), 0.02)
        n = max(int(math.ceil(dist / step)), 1)
        for i in range(0 if dist == 0 else 1, n + 1):
            t = i / n
            p = tuple(a + (b - a) * t for a, b in zip(p0, p1, strict=True))
            res.merge(self._stamp(cutter, p, parts, reach))
        if res.removed > 0:
            self.version += 1
        return res

    def _stamp(self, cutter: Cutter, p, parts, reach) -> CutResult:
        res = CutResult()
        x, y, z = p
        ix0 = max(int((x - reach - self.x0) / self.cell), 0)
        ix1 = min(int((x + reach - self.x0) / self.cell) + 1, self.nx)
        iy0 = max(int((y - reach - self.y0) / self.cell), 0)
        iy1 = min(int((y + reach - self.y0) / self.cell) + 1, self.ny)
        if ix0 >= ix1 or iy0 >= iy1:
            return res
        win = self.h[iy0:iy1, ix0:ix1]
        if float(np.max(win)) <= z + EPS:
            return res
        dx = self.xs[ix0:ix1] - x
        dy = self.ys[iy0:iy1] - y
        r = np.sqrt(dx[None, :] ** 2 + dy[:, None] ** 2)
        # części nietnące najpierw: materiał nad ostrzem w ich promieniu = kontakt (zanim ostrze
        # obniży słup w modelu 2.5D)
        for name, radius, z_from, _z_to in parts:
            if np.any((r <= radius) & (win > z + z_from + EPS)):
                res.parts.add(name)
                res.contact_at = (x, y, z)
        surface = z + cutter.lower(r)
        hit = win > surface + EPS
        if np.any(hit):
            old = np.clip(win[hit], self.z_bottom, None)
            new_h = surface[hit].astype(np.float32)
            win[hit] = new_h
            res.removed = float(np.sum(old - np.clip(new_h, self.z_bottom, None))) \
                * self.cell * self.cell
            res.contact_at = res.contact_at or (x, y, z)
        return res
