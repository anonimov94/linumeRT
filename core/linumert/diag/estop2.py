"""Dwukanałowy E-STOP NC z kontrolą rozbieżności — model logiki `hal/lrt_estop2.comp`.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19

Ta sama logika co komponent HAL (testy bez LinuxCNC, panel Plant, opis w dokumentacji):
`ok` = oba kanały zamknięte i brak błędu; różnica kanałów dłuższa niż `discrepancy_time` = błąd
zatrzaśnięty; skasowanie wymaga testu obwodu (oba otwarte → oba zamknięte) i zbocza `reset`.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Estop2:
    discrepancy_time: float = 0.1
    ok: bool = False
    fault: bool = False
    test_done: bool = False
    timer: float = 0.0
    _last_reset: bool = False
    _both_opened: bool = False

    def step(self, ch_a: bool, ch_b: bool, reset: bool, period: float) -> bool:
        rise = reset and not self._last_reset
        self._last_reset = reset
        if ch_a != ch_b:
            self.timer += period
            if self.timer > self.discrepancy_time:
                if not self.fault:
                    self._both_opened = False
                    self.test_done = False
                self.fault = True
        else:
            self.timer = 0.0
        if self.fault:
            if not ch_a and not ch_b:
                self._both_opened = True
            if self._both_opened and ch_a and ch_b:
                self.test_done = True
            if self.test_done and rise and ch_a and ch_b:
                self.fault = self.test_done = self._both_opened = False
        self.ok = ch_a and ch_b and not self.fault
        return self.ok
