"""Wyrocznia testowa Plant: soft limits i strefy zakazane (REQ-VM-06, sesja 019).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 019.

W każdej ramce (po kroku modelu) sprawdza:
  * pozycję zadaną każdego napędu w CSP, przeliczoną na fizyczne położenie osi:
    `położenie rzeczywiste + (607Ah − 6064h) / impulsy_na_jednostkę` — niezależnie od bazowania
    i przesunięć mastera; poza `soft_limits` osi z machine.yaml = naruszenie `soft_limit`;
  * koniec narzędzia z kinematyki prostej wewnątrz `forbidden_zones` = `zone`. Punkt liczony
    względem stołu (`tool_tip(workpiece=True)`), czyli tak jak współrzędne maszynowe G53 LinuxCNC:
    w frezarce ze stołem ruchomym koniec narzędzia w ramie maszyny stoi w XY, a strefa magazynu
    w G53 dotyczy położenia narzędzia względem stołu. Przy osiach obrotowych w zerze oba układy
    są równe; strefy ruchome razem ze stołem obrotowym = PROPOZYCJA (DECYZJE, sesja 019).
Naruszenie jest zdarzeniem ORACLE_VIOLATION (rodzaj, oś/strefa, pozycja, numer ramki), zapisanym
przy wejściu w stan naruszenia; czas trwania liczony w cyklach. Wynik scenariusza = FAIL przy
każdym naruszeniu, niezależnie od tego, czy LinuxCNC je zablokował.

Uzbrojenie: bazowanie LinuxCNC celowo wyjeżdża za soft limits (krańcówka za soft limit), więc
wyrocznia działa dopiero, gdy master ustawi bit wyjścia `arm_bit` (HAL: `motion.is-all-homed` →
`lrt-net.0.dout-31`). `arm_bit = None` = zawsze uzbrojona (testy jednostkowe).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

MODE_CSP = 8
MAX_RECORDS = 200


@dataclass
class Violation:
    kind: str                # "soft_limit" | "zone"
    name: str                # litera osi (z napędem) albo nazwa strefy
    position: list[float]    # [jedn. osi] albo [x, y, z] mm
    seq: int
    time_ns: int
    detail: str = ""
    cycles: int = 1          # liczba kolejnych ramek w naruszeniu


@dataclass
class Box:
    name: str
    lo: tuple[float, float, float]
    hi: tuple[float, float, float]

    def contains(self, p: tuple[float, float, float]) -> bool:
        """Punkt wewnątrz (krawędź = poza: dotknięcie granicy strefy nie jest wjazdem)."""
        return all(lo < v < hi for v, lo, hi in zip(p, self.lo, self.hi, strict=True))


@dataclass
class Oracle:
    soft_limits: dict[str, tuple[float, float]]       # litera osi → (min, max)
    zones: list[Box]
    drive_axis: dict[str, str]                         # napęd → litera osi
    counts_per_unit: dict[str, float]
    arm_bit: int | None = 31
    tolerance: float = 1e-3
    violations: list[Violation] = field(default_factory=list)
    total: int = 0
    checked: int = 0
    _active: dict[tuple[str, str], Violation] = field(default_factory=dict)

    @classmethod
    def for_machine(cls, machine, drives: list[str], arm_bit: int | None = 31) -> Oracle:
        cfg = machine.model.config
        limits = {a.letter: (float(a.soft_limits[0]), float(a.soft_limits[1])) for a in cfg.axes}
        owner = {d: a.letter for a in cfg.axes for d in a.drives}
        zones = [Box(z.name, tuple(z.min), tuple(z.max)) for z in cfg.forbidden_zones]
        return cls(soft_limits=limits, zones=zones,
                   drive_axis={d: owner[d] for d in drives if d in owner},
                   counts_per_unit={d: machine.model.counts_per_unit[d] for d in drives},
                   arm_bit=arm_bit)

    def target_position(self, machine, drive: str, target_counts: int) -> float:
        """Pozycja zadana napędu (607Ah) jako fizyczne położenie osi [jedn. machine.yaml]."""
        return machine.drive_position(drive) + (
            target_counts - machine.position_actual(drive)) / self.counts_per_unit[drive]

    def armed(self, digital_out: int) -> bool:
        return self.arm_bit is None or bool(digital_out >> self.arm_bit & 1)

    def check(self, machine, cmd, drives: list[str]) -> list[Violation]:
        """Jedna ramka (po kroku modelu). Zwraca nowe naruszenia (wejścia w stan naruszenia)."""
        if not self.armed(cmd.digital_out):
            self._active.clear()
            return []
        self.checked += 1
        now: dict[tuple[str, str], tuple[list[float], str]] = {}
        for drive, axis in zip(drives, cmd.axes, strict=True):
            letter = self.drive_axis.get(drive)
            if letter is None or axis.mode != MODE_CSP or letter not in self.soft_limits:
                continue
            lo, hi = self.soft_limits[letter]
            target = self.target_position(machine, drive, axis.target_pos)
            if target < lo - self.tolerance or target > hi + self.tolerance:
                now[("soft_limit", f"{letter}:{drive}")] = (
                    [round(target, 4)], f"zadane {target:.3f} poza [{lo:g}, {hi:g}]")
        if self.zones:
            tip = machine.tool_tip(workpiece=True)  # względem stołu = współrzędne G53
            for box in self.zones:
                if box.contains(tip):
                    now[("zone", box.name)] = (
                        [round(v, 3) for v in tip], f"narzędzie w strefie {box.name}")
        fresh = []
        for key, (pos, detail) in now.items():
            if key in self._active:
                self._active[key].cycles += 1
                continue
            v = Violation(kind=key[0], name=key[1], position=pos, seq=cmd.seq,
                          time_ns=cmd.time_ns, detail=detail)
            self._active[key] = v
            self.total += 1
            if len(self.violations) < MAX_RECORDS:
                self.violations.append(v)
            fresh.append(v)
        for key in list(self._active):
            if key not in now:
                del self._active[key]
        return fresh

    @property
    def passed(self) -> bool:
        return self.total == 0

    def report(self) -> dict:
        return {"result": "PASS" if self.passed else "FAIL", "violations_total": self.total,
                "frames_checked": self.checked, "arm_bit": self.arm_bit,
                "violations": [asdict(v) for v in self.violations]}
