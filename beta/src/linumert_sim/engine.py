"""Silnik symulacji na żywo: materiał, reguły kolizji i przeciążenia (NARZEDZIA_I_KOLIZJE.md §3).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

Wejście: kolejne próbki stanu maszyny (`Sample`: pozycja nosa wrzeciona w G53, narzędzie,
obroty ze znakiem, rodzaj ruchu, linia programu). Wyjście: zdarzenia (`Event`) z kodem K-3xx.
Reguły (kolizja i przeciążenie = wskazanie modelu `stop`, bez komend do LinuxCNC):
- kontakt z materiałem bez obrotów (K-301), w złym kierunku obrotów (K-308),
  ruchem szybkim G0 (K-302);
- część nietnąca (szyjka, oprawka, wrzeciono) w materiale (K-303);
- narzędzie, oprawka albo wrzeciono z bryłą maszyny (K-305) lub z mocowaniem (K-304) — zawsze,
  z obrotami i bez;
- przeciążenie wrzeciona (K-306) i napędu osi (K-307): moc skrawania z objętości usuniętej
  w oknie 0,2 s (P = kc · MRR), moment = P/ω, siła skrawania = moment / promień narzędzia,
  siła posuwu ≈ 0,5 siły skrawania (gwintownik 0,1) rozłożona na osie wg kierunku ruchu;
- obroty powyżej maksimum narzędzia (K-309); ostrzeżenia: brak geometrii (K-320), podcięcie (K-322).
Kolizje symulacji nie są funkcją bezpieczeństwa (CLAUDE.md §6). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field

from .cutter import Cutter
from .machine import FIXTURE, Machine, collisions
from .zmap import StockMap

MIN_RPM = 10.0          # próg „wrzeciono stoi” (NARZEDZIA_I_KOLIZJE.md §3)
MIN_REMOVED = 0.01      # [mm³] kontakt z materiałem w jednym kroku
LOAD_WINDOW = 0.2       # [s] okno mocy skrawania
# Opór właściwy skrawania kc [N/mm²] (wartości orientacyjne)
KC = {"aluminium": 700.0, "aluminium 6061": 700.0, "aluminium 7075": 850.0, "stal": 2000.0,
      "stal nierdzewna": 2500.0, "mosiądz": 800.0, "miedź": 1100.0, "żeliwo": 1200.0,
      "tworzywo": 150.0, "pom": 150.0, "drewno": 60.0, "mdf": 50.0}
DEFAULT_KC = 700.0


def kc_for(material: str | None) -> float:
    return KC.get((material or "").strip().lower(), DEFAULT_KC)


@dataclass
class Sample:
    t: float                                   # [s]
    nose: tuple[float, float, float]           # nos wrzeciona, układ maszyny G53 [mm]
    tool: int = 0
    rpm: float = 0.0                           # > 0 M3, < 0 M4
    motion: str = "feed"                       # rapid | feed | none
    line: int = 0


@dataclass
class Event:
    code: str
    kind: str                                  # collision | overload | warning
    line: int
    tool: int
    pos: tuple[float, float, float]
    params: dict = field(default_factory=dict)
    pair: tuple[str, str] | None = None

    @property
    def stop(self) -> bool:
        return self.kind != "warning"

    def text(self) -> str:
        try:
            from linumert.alarms.catalog import load_catalog

            return load_catalog().format(self.code, "pl", **self.params)
        except Exception:  # noqa: BLE001 - katalog niedostępny: sam kod i parametry
            return f"{self.code} {self.params}"

    def to_dict(self) -> dict:
        return {"code": self.code, "kind": self.kind, "line": self.line, "tool": self.tool,
                "pos": [round(v, 3) for v in self.pos], "pair": list(self.pair or ()),
                "text": self.text(), "stop": self.stop}


@dataclass
class Load:
    mrr: float = 0.0          # [mm³/s]
    power: float = 0.0        # [W]
    torque: float = 0.0       # [N·m]
    torque_limit: float = 0.0
    force: float = 0.0        # [N] siła skrawania
    axis: dict = field(default_factory=dict)   # oś → (siła, granica)


class SimEngine:
    def __init__(self, machine: Machine | None = None):
        self.machine = machine or Machine()
        self.stock: StockMap | None = None
        self.material: str | None = None
        self.tools: dict[int, Cutter] = {}
        self.load = Load()
        self._prev: Sample | None = None
        self._window: collections.deque[tuple[float, float, float]] = collections.deque()
        self._active: set[tuple] = set()       # bieżące pary kolizji (zdarzenie na wejściu)
        self._warned: set[tuple] = set()
        self._idle = 0                         # próbki bez kontaktu z materiałem (histereza)
        self.path: list[tuple[float, float, float, str]] = []

    # ---- konfiguracja ------------------------------------------------------------------
    def set_stock(self, stock: StockMap | None, material: str | None = None) -> None:
        self.stock, self.material = stock, material
        self._prev = None
        self.path.clear()

    def reset_stock(self) -> None:
        if self.stock is not None:
            self.stock.reset()
        self.path.clear()
        self._active.clear()
        self._window.clear()
        self._prev = None
        self._idle = 0
        self.load = Load()

    def set_tools(self, tools: dict[int, Cutter]) -> None:
        self.tools = dict(tools)
        self._warned = {w for w in self._warned if w[0] != "K-320"}

    def set_machine(self, machine: Machine) -> None:
        self.machine = machine
        self._active.clear()

    # ---- krok ----------------------------------------------------------------------------
    def step(self, s: Sample) -> list[Event]:
        events: list[Event] = []
        self._active -= {key for key in self._active
                         if key[0] == "K-309" and key[1] != s.tool}
        cutter = self.tools.get(s.tool) if s.tool else None
        gauge = cutter.gauge if cutter else 0.0
        tip = (s.nose[0], s.nose[1], s.nose[2] - gauge)
        prev = self._prev
        self._prev = s
        if cutter is not None:
            self._warnings(cutter, s, tip, events)
        if prev is not None and (prev.tool != s.tool or s.t - prev.t > 1.0):
            prev = None  # zmiana narzędzia albo przerwa w próbkach: bez przejazdu
        if not self.path or math.dist(self.path[-1][:3], tip) > 0.2:
            self.path.append((*tip, s.motion))
            if len(self.path) > 200_000:
                del self.path[:50_000]
        removed = 0.0
        if self.stock is not None and prev is not None and cutter is not None:
            p0 = (prev.nose[0], prev.nose[1], prev.nose[2] - gauge)
            res = self.stock.cut(cutter, p0, tip, self._spindle_parts(gauge))
            removed = res.removed
            pos = res.contact_at or tip
            for part in sorted(res.parts):
                self._once(events, ("K-303", part), Event(
                    "K-303", "collision", s.line, s.tool, pos, {"line": s.line, "part": part},
                    (part, "przygotówka")))
            if removed > MIN_REMOVED:
                self._idle = 0
                self._material_rules(cutter, s, prev, pos, events)
            else:
                self._idle += 1
                if self._idle > 20:  # ok. 0,2 s bez kontaktu: następny kontakt = nowe zdarzenie
                    self._active -= {k for k in self._active
                                     if k[0] in ("K-301", "K-302", "K-308")}
            if not res.parts:
                self._active -= {k for k in self._active if k[0] == "K-303"}
        self._machine_rules(cutter, s, tip, events)
        self._loads(cutter, s, prev, tip, removed, events)
        return events

    def _spindle_parts(self, gauge: float):
        """Bryły wrzeciona z modelu jako walce nietnące względem wierzchołka."""
        out = []
        for b in self.machine.bodies:
            if b.moving and b.shape == "cylinder":
                z0, z1 = b.z_range(0.0)
                out.append((b.name, b.size[0] / 2, gauge + z0, gauge + z1))
        return out

    def _once(self, events: list[Event], key: tuple, event: Event) -> None:
        if key not in self._active:
            self._active.add(key)
            events.append(event)

    def _warnings(self, cutter: Cutter, s: Sample, tip, events: list[Event]) -> None:
        if cutter.substitute and ("K-320", s.tool) not in self._warned:
            self._warned.add(("K-320", s.tool))
            events.append(Event("K-320", "warning", s.line, s.tool, tip, {"tool": s.tool}))
        if cutter.undercut and ("K-322", s.tool) not in self._warned:
            self._warned.add(("K-322", s.tool))
            events.append(Event("K-322", "warning", s.line, s.tool, tip, {"tool": s.tool}))
        if cutter.max_rpm and abs(s.rpm) > cutter.max_rpm * 1.001:
            self._once(events, ("K-309", s.tool), Event(
                "K-309", "overload", s.line, s.tool, tip,
                {"tool": s.tool, "rpm": round(abs(s.rpm)), "limit": round(cutter.max_rpm)}))
        else:
            self._active.discard(("K-309", s.tool))

    def _material_rules(self, cutter: Cutter, s: Sample, prev: Sample, pos,
                        events: list[Event]) -> None:
        # Odcinek między próbkami: G0 tylko gdy obie próbki to G0 (koniec G1 → początek G0),
        # obroty z próbki, w której wrzeciono wirowało (zatrzymanie wrzeciona w trakcie odcinka)
        rpm = s.rpm if abs(s.rpm) >= abs(prev.rpm) else prev.rpm
        if s.motion == "rapid" and prev.motion == "rapid":
            self._once(events, ("K-302",), Event("K-302", "collision", s.line, s.tool, pos,
                                                 {"line": s.line, "tool": s.tool},
                                                 ("narzedzie", "przygotówka")))
        elif abs(rpm) < MIN_RPM:
            self._once(events, ("K-301",), Event("K-301", "collision", s.line, s.tool, pos,
                                                 {"line": s.line, "tool": s.tool},
                                                 ("narzedzie", "przygotówka")))
        elif cutter.kind != "tap" and (1 if rpm > 0 else -1) != cutter.hand:
            direction = "M4, lewe" if rpm < 0 else "M3, prawe"
            self._once(events, ("K-308",), Event("K-308", "collision", s.line, s.tool, pos,
                                                 {"line": s.line, "tool": s.tool,
                                                  "direction": direction},
                                                 ("narzedzie", "przygotówka")))

    def _machine_rules(self, cutter: Cutter | None, s: Sample, tip, events: list[Event]) -> None:
        cyl = []
        if cutter is not None:
            cyl.append(("narzedzie", cutter.radius, tip[2], tip[2] + cutter.cut_top))
            for name, r, z0, z1 in cutter.parts():
                cyl.append((name, r, tip[2] + z0, tip[2] + z1))
        hits = set()
        for moving, fixed in collisions(self.machine, s.nose, cyl):
            body = next(b for b in self.machine.bodies if b.name == fixed)
            if body.attached == "toolsetter" and moving == "narzedzie":
                continue  # pomiar długości = dotknięcie czujnika
            if body.attached == "magazine" and moving == "narzedzie":
                continue  # odkładanie narzędzia w gnieździe (pozycje wymiany sprawdza Plant)
            code = "K-304" if body.attached in FIXTURE else "K-305"
            key = (code, moving, fixed)
            hits.add(key)
            params = ({"line": s.line, "tool": s.tool} if code == "K-304"
                      else {"line": s.line, "element": f"{moving} – {fixed}"})
            self._once(events, key, Event(code, "collision", s.line, s.tool, tip, params,
                                          (moving, fixed)))
        self._active -= {k for k in self._active if k[0] in ("K-304", "K-305") and k not in hits}

    def _loads(self, cutter: Cutter | None, s: Sample, prev: Sample | None, tip, removed: float,
               events: list[Event]) -> None:
        dt = min(max(s.t - prev.t, 0.0), 1.0) if prev is not None else 0.0
        self._window.append((s.t, removed, dt))
        while self._window and s.t - self._window[0][0] > LOAD_WINDOW:
            self._window.popleft()
        span = sum(d for _t, _v, d in self._window)
        mrr = sum(v for _t, v, _d in self._window) / span if span > 1e-3 else 0.0
        load = Load(mrr=mrr)
        if cutter is not None and abs(s.rpm) >= MIN_RPM and mrr > 0:
            omega = abs(s.rpm) * 2 * math.pi / 60
            load.power = kc_for(self.material) * mrr * 1e-3
            load.torque = load.power / omega
            load.force = load.torque / max(cutter.radius * 1e-3, 1e-4)
        load.torque_limit = self.machine.spindle_torque_limit(s.rpm) if abs(s.rpm) else 0.0
        if prev is not None and load.force > 0:
            # siła posuwu ≈ 0,5 siły skrawania (frez, wiertło); gwintownik prowadzi się sam
            feed = load.force * (0.1 if cutter is not None and cutter.kind == "tap" else 0.5)
            d = [b - a for a, b in zip(prev.nose, s.nose, strict=True)]
            n = math.sqrt(sum(v * v for v in d)) or 1.0
            for axis, comp in zip("XYZ", d, strict=True):
                load.axis[axis] = (feed * abs(comp) / n, self.machine.force_limit(axis))
        self.load = load
        if load.torque > 0 and load.torque > load.torque_limit > 0:
            self._once(events, ("K-306",), Event(
                "K-306", "overload", s.line, s.tool, tip,
                {"line": s.line, "torque": f"{load.torque:.2f}",
                 "limit": f"{load.torque_limit:.2f}"}, ("wrzeciono", "")))
        elif load.torque == 0 or load.torque < 0.8 * load.torque_limit:
            self._active.discard(("K-306",))
        if not load.axis:
            self._active -= {key for key in self._active if key[0] == "K-307"}
        for axis, (force, limit) in load.axis.items():
            if force > limit:
                self._once(events, ("K-307", axis), Event(
                    "K-307", "overload", s.line, s.tool, tip,
                    {"line": s.line, "axis": axis, "force": round(force),
                     "limit": round(limit)}, (f"oś {axis}", "")))
            elif force < 0.8 * limit:
                self._active.discard(("K-307", axis))
