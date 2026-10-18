"""Wirtualny pulpit: MPG, wybór osi i kroku, Start/Stop posuwu, kluczyk (sesja 022).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 022.

Pulpit to wejścia cyfrowe LinuxCNC przez LRT-NET (bity `digital_in` ramki v1, piny
`lrt_net.0.din-NN`); mapowanie bitów w sekcji `desk:` pliku plant.yaml (docs/PLANT.md §7a).
Stan elektryczny: 1 = styk zamknięty (przycisk wciśnięty, wybrana pozycja przełącznika).

- MPG: kwadratura A/B jak w ręcznym kole (A wyprzedza B przy obrocie dodatnim). Jedna
  ząbkowana pozycja = `edges_per_detent` zboczy (domyślnie 4, cały cykl kwadratury); Plant
  wystawia najwyżej jedno zbocze na ramkę, więc koło nie gubi impulsów przy 1 kHz
  (do 250 pozycji/s). Po stronie LinuxCNC dekoduje je komponent `encoder` (counter-mode 0).
- Oś i krok: przełączniki jedno-z-N (dokładnie jeden bit z grupy = 1).
- Start i Stop posuwu: impulsy o długości `pulse_ms` czasu modelu (przyciski chwilowe).
- Kluczyk: stan stały (0/1).
Czas pochodzi z ramek, więc w trybie lockstep przebieg pulpitu jest deterministyczny.
NIEZWERYFIKOWANE NA SPRZĘCIE (pulpit wirtualny, połączenie HAL w sesji 029).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

QUADRATURE = ((0, 0), (1, 0), (1, 1), (0, 1))  # (A, B) dla fazy 0..3; +1 faza = obrót dodatni
MAX_PENDING_EDGES = 4000  # bufor zboczy MPG (≈ 1000 pozycji koła); nadmiar odrzucany
BUTTONS = ("cycle_start", "feed_hold")


@dataclass
class DeskConfig:
    mpg_a: int | None = None
    mpg_b: int | None = None
    axis: dict[str, int] = field(default_factory=dict)  # litera osi → bit
    step: dict[int, int] = field(default_factory=dict)  # krok ×N → bit
    cycle_start: int | None = None
    feed_hold: int | None = None
    key: int | None = None
    edges_per_detent: int = 4
    pulse_ms: float = 100.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeskConfig:
        def bit(value: Any) -> int | None:
            return None if value is None else int(value)

        axis, step = data.get("axis") or {}, data.get("step") or {}
        if not isinstance(axis, dict) or not isinstance(step, dict):
            raise ValueError("desk.axis i desk.step: oczekiwano mapy pozycja: bit")
        known = {"mpg_a", "mpg_b", "axis", "step", "cycle_start", "feed_hold", "key",
                 "edges_per_detent", "pulse_ms"}
        extra = sorted(set(data) - known)
        if extra:
            raise ValueError(f"desk: nieznane pola {', '.join(extra)}")
        return cls(mpg_a=bit(data.get("mpg_a")), mpg_b=bit(data.get("mpg_b")),
                   axis={str(k).upper(): int(v) for k, v in axis.items()},
                   step={int(k): int(v) for k, v in step.items()},
                   cycle_start=bit(data.get("cycle_start")), feed_hold=bit(data.get("feed_hold")),
                   key=bit(data.get("key")),
                   edges_per_detent=int(data.get("edges_per_detent", 4)),
                   pulse_ms=float(data.get("pulse_ms", 100.0)))

    def bits(self) -> dict[str, int]:
        """Nazwa sygnału → bit (np. mpg_a, axis.X, step.10, key)."""
        out = {n: getattr(self, n) for n in ("mpg_a", "mpg_b", "cycle_start", "feed_hold", "key")
               if getattr(self, n) is not None}
        out.update({f"axis.{k}": v for k, v in self.axis.items()})
        out.update({f"step.{k}": v for k, v in self.step.items()})
        return out

    def problems(self, used: dict[str, int] | None = None) -> list[str]:
        """Błędy mapowania; `used` = wejścia maszyny (io.inputs), bez kolizji bitów."""
        errors = []
        bits = self.bits()
        for name, b in bits.items():
            if not 0 <= b <= 31:
                errors.append(f"desk.{name}: bit {b} poza 0–31")
        seen: dict[int, str] = {}
        for name, b in bits.items():
            if b in seen:
                errors.append(f"desk.{name}: bit {b} zajęty już przez desk.{seen[b]}")
            seen.setdefault(b, name)
        for name, b in (used or {}).items():
            if b in seen:
                errors.append(f"desk.{seen[b]}: bit {b} zajęty przez wejście maszyny {name} "
                              "(machine.yaml io.inputs)")
        if (self.mpg_a is None) != (self.mpg_b is None):
            errors.append("desk: MPG wymaga obu bitów mpg_a i mpg_b")
        if self.edges_per_detent not in (1, 2, 4):
            errors.append(f"desk.edges_per_detent: {self.edges_per_detent} — dozwolone 1, 2, 4")
        if not 1 <= self.pulse_ms <= 5000:
            errors.append(f"desk.pulse_ms: {self.pulse_ms} poza 1–5000")
        if any(k <= 0 for k in self.step):
            errors.append("desk.step: krok musi być dodatni (np. 1, 10, 100)")
        return errors


class Desk:
    """Stan pulpitu; metody operatora wołane z wątku panelu, `step()` z pętli ramek."""

    def __init__(self, cfg: DeskConfig):
        self.cfg = cfg
        self._lock = threading.Lock()
        self.pending = 0  # zbocza MPG do wystawienia (znak = kierunek)
        self.phase = 0
        self.edges = 0  # licznik zboczy wystawionych od startu (znak = kierunek)
        self.dropped = 0
        self.axis = next(iter(cfg.axis), None)
        self.step_size = next(iter(cfg.step), None)
        self.key = False
        self._pulses = {name: 0.0 for name in BUTTONS}

    # ---- operator (panel) ------------------------------------------------------------
    def mpg(self, detents: int) -> int:
        """Obrót koła o `detents` pozycji. Zwraca liczbę przyjętych zboczy."""
        if self.cfg.mpg_a is None:
            raise ValueError("pulpit bez MPG (brak desk.mpg_a/mpg_b w plant.yaml)")
        edges = int(detents) * self.cfg.edges_per_detent
        with self._lock:
            new = max(-MAX_PENDING_EDGES, min(MAX_PENDING_EDGES, self.pending + edges))
            taken = new - self.pending
            self.dropped += abs(edges - taken)
            self.pending = new
        return taken

    def select_axis(self, letter: str) -> None:
        letter = letter.upper()
        if letter not in self.cfg.axis:
            raise ValueError(f"oś {letter} nie jest na pulpicie (desk.axis: "
                             f"{', '.join(self.cfg.axis) or 'brak'})")
        with self._lock:
            self.axis = letter

    def select_step(self, size: int) -> None:
        if size not in self.cfg.step:
            raise ValueError(f"krok ×{size} nie jest na pulpicie (desk.step: "
                             f"{', '.join(map(str, self.cfg.step)) or 'brak'})")
        with self._lock:
            self.step_size = size

    def press(self, button: str) -> None:
        if button not in BUTTONS or getattr(self.cfg, button) is None:
            raise ValueError(f"przycisk {button} nie jest na pulpicie")
        with self._lock:
            self._pulses[button] = self.cfg.pulse_ms / 1000.0

    def set_key(self, on: bool) -> None:
        if self.cfg.key is None:
            raise ValueError("pulpit bez kluczyka (brak desk.key)")
        with self._lock:
            self.key = bool(on)

    # ---- pętla ramek -----------------------------------------------------------------
    def step(self, dt: float) -> None:
        """Jedna ramka: najwyżej jedno zbocze MPG, odliczanie impulsów przycisków."""
        with self._lock:
            if self.pending:
                d = 1 if self.pending > 0 else -1
                self.phase = (self.phase + d) % 4
                self.pending -= d
                self.edges += d
            for name, left in self._pulses.items():
                if left > 0:
                    self._pulses[name] = max(0.0, left - dt)

    def inputs(self) -> tuple[int, int]:
        """(maska, wartość) bitów pulpitu w `digital_in`."""
        c = self.cfg
        mask = value = 0
        with self._lock:
            levels: dict[int, bool] = {}
            if c.mpg_a is not None and c.mpg_b is not None:
                a, b = QUADRATURE[self.phase]
                levels[c.mpg_a], levels[c.mpg_b] = bool(a), bool(b)
            for letter, b in c.axis.items():
                levels[b] = letter == self.axis
            for size, b in c.step.items():
                levels[b] = size == self.step_size
            for name in BUTTONS:
                b = getattr(c, name)
                if b is not None:
                    levels[b] = self._pulses[name] > 0
            if c.key is not None:
                levels[c.key] = self.key
        for b, on in levels.items():
            mask |= 1 << b
            value |= int(on) << b
        return mask, value

    def state(self) -> dict:
        with self._lock:
            return {"axis": self.axis, "step": self.step_size, "key": self.key,
                    "mpg_pending": self.pending, "mpg_edges": self.edges,
                    "mpg_dropped": self.dropped,
                    "buttons": {n: v > 0 for n, v in self._pulses.items()},
                    "bits": self.cfg.bits(), "axes": list(self.cfg.axis),
                    "steps": list(self.cfg.step)}
