"""Magazyn narzędzi, zacisk wrzeciona, pozycje wymiany i czujnik długości (REQ-VM-08, VM-09).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 020.

Zdarzenia dyskretne liczone w serwerze Plant po kroku modelu C (dynamika osi zostaje w C).
Układ odniesienia: współrzędne G53 nosa wrzeciona (jak wyrocznia, sesja 019) — pozycje gniazd,
czujnika i pozycji wymiany z machine.yaml są w tym układzie. Wysokość gniazda = `approach_z`
(nos wrzeciona, gdy oprawka siedzi w gnieździe).

Fizyka wymiany (pkt 3 sesji 020):
  * zwolnienie zacisku z narzędziem nad wolnym gniazdem (XY i Z w tolerancji) → TOOL_PLACED;
    gdzie indziej → TOOL_DROP (narzędzie spada, wrzeciono puste);
  * zaciśnięcie pustego wrzeciona nad gniazdem z narzędziem → TOOL_PICKED;
  * zjazd pustego wrzeciona z zamkniętym zaciskiem na oprawkę w gnieździe → CLAMP_FAULT;
  * zjazd wrzeciona z narzędziem na zajęte gniazdo → POCKET_OCCUPIED;
  * nos poniżej `retract_z` nad magazynem przy niepełnie otwartej osłonie → COVER_CRASH;
  * ręczna wymiana poza `positions.manual_change` (tolerancja) → MANUAL_CHANGE_POSITION.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from linumert.machine.toolchanger_geometry import pocket_positions

MANUAL_TOLERANCE_MM = 2.0
SETTER_RADIUS_MM = 10.0
FOOTPRINT_MARGIN_MM = 40.0


@dataclass
class ToolSpec:
    length: float = 50.0     # wysięg od nosa wrzeciona [mm]
    diameter: float = 6.0


@dataclass
class AtcEvent:
    kind: str
    detail: str
    position: list[float]
    time_s: float
    slot: int | None = None
    tool: int | None = None


@dataclass
class ToolChangerModel:
    type: str
    pockets: list[tuple[float, float, float]]          # pozycje gniazd (dla karuzeli: wymiany)
    io_in: dict[str, int]
    io_out: dict[str, int]
    roles_out: dict[str, str]
    sensor_names: dict[str, str]                       # rola → nazwa wejścia
    tolerance: float = 0.5
    retract_z: float | None = None
    clamp_time: float = 0.2
    cover_time: float = 0.0                            # 0 = brak osłony
    index_time: float = 0.5
    manual_pos: tuple[float, float, float] | None = None
    tools: dict[int, ToolSpec] = field(default_factory=dict)
    slots: list[int | None] = field(default_factory=list)
    spindle_tool: int | None = None
    clamped: bool = True
    cover: float = 0.0                                 # 0 zamknięta … 1 otwarta
    carousel_pos: int = 0
    umbrella: float = 0.0                              # 0 wysunięte … 1 przy wrzecionie
    events: list[AtcEvent] = field(default_factory=list)
    time_s: float = 0.0
    _clamp_timer: float = 0.0
    _index_left: float = 0.0
    _prev_step: bool = False
    _active: set[str] = field(default_factory=set)

    # ---- budowa z machine.yaml --------------------------------------------------------------
    @classmethod
    def from_config(cls, cfg, tools: dict[int, ToolSpec] | None = None) -> ToolChangerModel:
        tc = cfg.toolchanger
        sensors = dict(tc.sensors)
        if tc.clamp is not None and tc.clamp.sensor:
            sensors.setdefault("clamped", tc.clamp.sensor)
        if tc.cover is not None:
            if tc.cover.sensor_open:
                sensors.setdefault("cover_open", tc.cover.sensor_open)
            if tc.cover.sensor_closed:
                sensors.setdefault("cover_closed", tc.cover.sensor_closed)
        pos = cfg.positions
        model = cls(type=tc.type, pockets=pocket_positions(tc), io_in=dict(cfg.io.inputs),
                    io_out=dict(cfg.io.outputs), roles_out=dict(tc.outputs),
                    sensor_names=sensors, tolerance=tc.tolerance_mm, retract_z=tc.retract_z,
                    clamp_time=(tc.clamp.time_ms / 1000.0) if tc.clamp else 0.2,
                    cover_time=(tc.cover.actuation_ms / 1000.0) if tc.cover else 0.0,
                    index_time=tc.index_ms / 1000.0,
                    manual_pos=tuple(pos.manual_change) if pos.manual_change else None,
                    tools=dict(tools or {}))
        model.slots = [i + 1 for i in range(tc.slots)]  # gniazdo i: narzędzie i+1 na starcie
        model.cover = 0.0 if model.cover_time > 0 else 1.0
        return model

    # ---- stan ----------------------------------------------------------------------------
    def tool_spec(self, tool: int | None = None) -> ToolSpec | None:
        tool = self.spindle_tool if tool is None else tool
        return None if tool is None else self.tools.get(tool, ToolSpec())

    def active_pockets(self) -> list[int]:
        if self.type == "rack_linear":
            return list(range(len(self.pockets)))
        if self.type == "carousel":
            return [] if self._index_left > 0 else [self.carousel_pos]
        if self.type == "umbrella":
            ready = self.umbrella >= 1.0 - 1e-9 and self._index_left <= 0
            return [self.carousel_pos] if ready else []
        return []

    def aligned(self, nose, z_tol: float | None = None) -> int | None:
        """Aktywne gniazdo współosiowe z wrzecionem (XY; przy z_tol także wysokość)."""
        for i in self.active_pockets():
            px, py, pz = self.pockets[i]
            if math.hypot(nose[0] - px, nose[1] - py) <= self.tolerance and (
                    z_tol is None or abs(nose[2] - pz) <= z_tol):
                return i
        return None

    def over_magazine(self, nose) -> bool:
        if not self.pockets:
            return False
        xs = [p[0] for p in self.pockets]
        ys = [p[1] for p in self.pockets]
        m = FOOTPRINT_MARGIN_MM
        return min(xs) - m <= nose[0] <= max(xs) + m and min(ys) - m <= nose[1] <= max(ys) + m

    def _out(self, mask: int, role: str) -> bool:
        name = self.roles_out.get(role)
        return name is not None and bool(mask >> self.io_out[name] & 1)

    def _event(self, kind: str, detail: str, nose, slot=None, tool=None) -> AtcEvent:
        ev = AtcEvent(kind, detail, [round(v, 3) for v in nose], round(self.time_s, 4), slot, tool)
        self.events.append(ev)
        return ev

    def _edge(self, key: str, condition: bool) -> bool:
        """True przy wejściu w stan `condition` (zdarzenia bez powtórzeń w kolejnych ramkach)."""
        if condition and key not in self._active:
            self._active.add(key)
            return True
        if not condition:
            self._active.discard(key)
        return False

    # ---- krok ------------------------------------------------------------------------------
    def step(self, dt: float, nose, outputs: int) -> list[AtcEvent]:
        self.time_s += dt
        fresh: list[AtcEvent] = []
        # osłona (siłownik z czasem przejazdu)
        if self.cover_time > 0:
            goal = 1.0 if self._out(outputs, "cover_open") else 0.0
            delta = dt / self.cover_time
            self.cover = min(goal, self.cover + delta) if goal > self.cover else max(
                goal, self.cover - delta)
        # karuzela: zbocze wyjścia = jeden krok w czasie index_time
        step_cmd = self._out(outputs, "carousel_step")
        if self.type in ("carousel", "umbrella") and step_cmd and not self._prev_step \
                and self._index_left <= 0 and self.pockets:
            self._index_left = self.index_time
        self._prev_step = step_cmd
        if self._index_left > 0:
            self._index_left -= dt
            if self._index_left <= 0:
                self.carousel_pos = (self.carousel_pos + 1) % len(self.pockets)
        if self.type == "umbrella":
            goal = 1.0 if self._out(outputs, "umbrella_in") else 0.0
            delta = dt / self.index_time
            self.umbrella = min(goal, self.umbrella + delta) if goal > self.umbrella else max(
                goal, self.umbrella - delta)
        # zacisk wrzeciona: zmiana stanu po clamp_time od polecenia
        want_clamped = not self._out(outputs, "clamp_release")
        if want_clamped != self.clamped:
            self._clamp_timer += dt
            if self._clamp_timer >= self.clamp_time - 1e-9:
                self._clamp_timer = 0.0
                self.clamped = want_clamped
                fresh += self._clamp_changed(nose)
        else:
            self._clamp_timer = 0.0
        # zjazd na gniazdo (oprawka wchodzi w gniazdo, gdy nos schodzi do wysokości gniazda)
        slot = self.aligned(nose)
        engaged = slot is not None and nose[2] <= self.pockets[slot][2] + self.tolerance
        occupied = slot is not None and self.slots[slot] is not None
        if self._edge("clamp_fault", engaged and occupied and self.spindle_tool is None
                      and self.clamped):
            fresh.append(self._event("CLAMP_FAULT", "puste wrzeciono z zamkniętym zaciskiem na "
                                     "oprawce w gnieździe", nose, slot, self.slots[slot]))
        if self._edge("occupied", engaged and occupied and self.spindle_tool is not None):
            fresh.append(self._event("POCKET_OCCUPIED", "narzędzie we wrzecionie nad zajętym "
                                     "gniazdem", nose, slot, self.spindle_tool))
        low = self.retract_z is not None and nose[2] < self.retract_z - self.tolerance
        if self._edge("cover", self.cover_time > 0 and self.cover < 1.0 - 1e-9 and low
                      and self.over_magazine(nose)):
            fresh.append(self._event("COVER_CRASH", "wjazd pod wysokość odjazdu przy "
                                     "niepełnie otwartej osłonie", nose))
        return fresh

    def _clamp_changed(self, nose) -> list[AtcEvent]:
        slot = self.aligned(nose, z_tol=self.tolerance)
        if not self.clamped and self.spindle_tool is not None:   # zwolnienie z narzędziem
            tool = self.spindle_tool
            self.spindle_tool = None
            if slot is not None and self.slots[slot] is None:
                self.slots[slot] = tool
                return [self._event("TOOL_PLACED", f"T{tool} w gnieździe {slot + 1}", nose,
                                    slot, tool)]
            return [self._event("TOOL_DROP", f"T{tool} upadło (zwolnienie poza gniazdem)", nose,
                                slot, tool)]
        if self.clamped and self.spindle_tool is None and slot is not None \
                and self.slots[slot] is not None:                # zaciśnięcie na oprawce
            tool = self.slots[slot]
            self.slots[slot] = None
            self.spindle_tool = tool
            return [self._event("TOOL_PICKED", f"T{tool} z gniazda {slot + 1}", nose, slot, tool)]
        return []

    def manual_change(self, tool: int | None, nose) -> AtcEvent | None:
        """Ręczna wymiana przez operatora (okno ekranu). Poza pozycją wymiany → zdarzenie."""
        ok = self.manual_pos is not None and all(
            abs(a - b) <= MANUAL_TOLERANCE_MM for a, b in zip(nose, self.manual_pos, strict=True))
        self.spindle_tool = tool
        if ok:
            return None
        return self._event("MANUAL_CHANGE_POSITION", "ręczna wymiana poza pozycją "
                           f"{self.manual_pos}", nose, tool=tool)

    def inputs(self) -> tuple[int, int]:
        """(maska, wartości) wejść liczonych tutaj — nadpisują bity z modelu C."""
        mask = value = 0
        eps = 1e-9  # resztki sumowania kroków zmiennoprzecinkowych
        states = {"clamped": self.clamped, "cover_open": self.cover >= 1.0 - eps,
                  "cover_closed": self.cover <= eps, "tool_present": self.spindle_tool is not None,
                  "carousel_in_position": self._index_left <= 0,
                  "umbrella_in": self.umbrella >= 1.0 - eps, "umbrella_out": self.umbrella <= eps}
        for role, state in states.items():
            name = self.sensor_names.get(role)
            if name is None or name not in self.io_in:
                continue
            bit = 1 << self.io_in[name]
            mask |= bit
            if state:
                value |= bit
        return mask, value


@dataclass
class ToolSetterModel:
    """Czujnik długości narzędzia (REQ-VM-09): styk, gdy koniec narzędzia dotknie powierzchni."""

    position: tuple[float, float, float]
    height: float
    bit: int
    radius: float = SETTER_RADIUS_MM

    @classmethod
    def from_config(cls, cfg) -> ToolSetterModel | None:
        ts = cfg.positions.tool_setter
        if ts is None or ts.input not in cfg.io.inputs:
            return None
        return cls(tuple(ts.position), ts.height, cfg.io.inputs[ts.input])

    @property
    def top(self) -> float:
        return self.position[2] + self.height

    def contact(self, tip) -> bool:
        return (math.hypot(tip[0] - self.position[0], tip[1] - self.position[1]) <= self.radius
                and tip[2] <= self.top)

    def inputs(self, tip) -> tuple[int, int]:
        bit = 1 << self.bit
        return bit, bit if self.contact(tip) else 0
