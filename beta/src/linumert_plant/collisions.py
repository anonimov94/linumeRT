"""Bryły kolizyjne i detekcja CRASH (REQ-VM-10, sesja 020).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 020.

Bryły z `collision_bodies` w machine.yaml: `box` (size = x, y, z) albo `cylinder` o osi Z
(size = średnica, wysokość); `position` = środek bryły. Bryły `head` i `spindle` jadą z nosem
wrzeciona (position względem nosa), pozostałe (`table`, `magazine`, `toolsetter`, `vise`) stoją
w układzie G53 (jak wyrocznia i magazyn). Narzędzie we wrzecionie = walec (średnica, wysięg) pod
nosem. Kolizja = przecięcie brył ruchomych z nieruchomymi; zdarzenie CRASH z parą nazw i pozycją
nosa przy wejściu w kolizję.
Wyjątki: narzędzie–magazyn przy wrzecionie współosiowym z aktywnym gniazdem (wymiana);
narzędzie–czujnik długości do 1 mm zagłębienia (pomiar = dotknięcie).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

MOVING = ("head", "spindle")
TOOL_NAME = "narzedzie"
SETTER_ALLOWANCE_MM = 1.0


@dataclass
class Solid:
    name: str
    shape: str                    # "box" | "cylinder"
    attached: str
    size: tuple[float, ...]
    offset: tuple[float, float, float]

    def at(self, nose) -> Solid:
        if self.attached not in MOVING and self.attached != "tool":
            return self
        c = tuple(n + o for n, o in zip(nose, self.offset, strict=True))
        return Solid(self.name, self.shape, self.attached, self.size, c)

    def z_range(self) -> tuple[float, float]:
        h = self.size[2] if self.shape == "box" else self.size[1]
        return self.offset[2] - h / 2, self.offset[2] + h / 2


def _z_overlap(a: Solid, b: Solid) -> float:
    a0, a1 = a.z_range()
    b0, b1 = b.z_range()
    return min(a1, b1) - max(a0, b0)


def _xy_overlap(a: Solid, b: Solid) -> bool:
    if a.shape == "box" and b.shape == "box":
        return all(abs(a.offset[i] - b.offset[i]) < (a.size[i] + b.size[i]) / 2 for i in (0, 1))
    if a.shape == "cylinder" and b.shape == "cylinder":
        d = math.hypot(a.offset[0] - b.offset[0], a.offset[1] - b.offset[1])
        return d < (a.size[0] + b.size[0]) / 2
    cyl, box = (a, b) if a.shape == "cylinder" else (b, a)
    # najbliższy punkt prostokąta do osi walca
    nx = min(max(cyl.offset[0], box.offset[0] - box.size[0] / 2), box.offset[0] + box.size[0] / 2)
    ny = min(max(cyl.offset[1], box.offset[1] - box.size[1] / 2), box.offset[1] + box.size[1] / 2)
    return math.hypot(cyl.offset[0] - nx, cyl.offset[1] - ny) < cyl.size[0] / 2


def penetration(a: Solid, b: Solid) -> float:
    """Zagłębienie w osi Z (> 0 przy przecięciu, ≤ 0 bez kolizji)."""
    if not _xy_overlap(a, b):
        return 0.0
    return max(0.0, _z_overlap(a, b))


@dataclass
class CrashEvent:
    kind: str
    pair: tuple[str, str]
    position: list[float]
    time_s: float
    depth_mm: float


@dataclass
class CollisionModel:
    solids: list[Solid]
    events: list[CrashEvent] = field(default_factory=list)
    time_s: float = 0.0
    _active: set[tuple[str, str]] = field(default_factory=set)

    @classmethod
    def from_config(cls, cfg) -> CollisionModel:
        return cls([Solid(b.name, b.shape, b.attached_to, tuple(float(v) for v in b.size),
                          tuple(float(v) for v in b.position)) for b in cfg.collision_bodies])

    def check(self, dt: float, nose, tool=None, exchange_aligned: bool = False
              ) -> list[CrashEvent]:
        """Jedna ramka. `tool` = ToolSpec narzędzia we wrzecionie (None = puste)."""
        self.time_s += dt
        moving = [s.at(nose) for s in self.solids if s.attached in MOVING]
        if tool is not None:
            moving.append(Solid(TOOL_NAME, "cylinder", "tool", (tool.diameter, tool.length),
                                (nose[0], nose[1], nose[2] - tool.length / 2)))
        fixed = [s for s in self.solids if s.attached not in MOVING]
        now: dict[tuple[str, str], float] = {}
        for m in moving:
            for f in fixed:
                if m.name == TOOL_NAME and f.attached == "magazine" and exchange_aligned:
                    continue
                depth = penetration(m, f)
                if m.name == TOOL_NAME and f.attached == "toolsetter":
                    depth -= SETTER_ALLOWANCE_MM
                if depth > 0:
                    now[(m.name, f.name)] = depth
        fresh = []
        for pair, depth in now.items():
            if pair not in self._active:
                ev = CrashEvent("CRASH", pair, [round(v, 3) for v in nose], round(self.time_s, 4),
                                round(depth, 3))
                self.events.append(ev)
                fresh.append(ev)
        self._active = set(now)
        return fresh
