# SPDX-License-Identifier: GPL-2.0-or-later
"""Paused-program Z offsets: leave the interpreter and cutter compensation intact.

Model-Author: Codex. All distances and rates use native machine units.
"""

import math
from dataclasses import dataclass

RETURN_TOLERANCE_MM = 1e-4  # decyzja właściciela 2026-10-26: dokładność powrotu Z


class RetractRefused(ValueError):
    pass


@dataclass(frozen=True)
class PauseSnapshot:
    powered: bool
    ready: bool
    paused: bool
    still: bool
    frame: tuple
    z: float
    offset: float
    requested: float
    lower: float
    upper: float
    limited: bool = False
    settled: bool = True
    offset_enabled: bool = True


class PauseRetract:
    """Own the offset until actual and requested Z both return to zero.

    A changed program/tool/modal frame or lost pause latches a fault. It must
    never silently lower the tool after Abort, a mode change or an I/O failure.
    """

    def __init__(self, tolerance=RETURN_TOLERANCE_MM):
        self.tolerance = tolerance
        self.phase = "idle"
        self.target = 0.0
        self.height = 0.0
        self.speed = 0.0
        self.frame = None
        self.message = "Wstrzymaj program przed wycofaniem."
        self.resume = False

    @property
    def active(self):
        return self.phase != "idle"

    def _check(self, s):
        if not (s.powered and s.ready and s.paused and s.still):
            raise RetractRefused("Wymagana ustalona pauza AUTO, baza osi i gotowe wrzeciono.")
        if not all(math.isfinite(x) for x in (s.z, s.offset, s.requested, s.lower, s.upper)):
            raise RetractRefused("Brak poprawnego odczytu pozycji i limitów.")
        if s.limited:
            raise RetractRefused("Zadziałało ograniczenie external offsets.")
        if self.phase in ("retracting", "retracted", "returning") and not s.offset_enabled:
            raise RetractRefused("Utracono potwierdzenie external offsets z HAL.")
        if self.frame is not None and self.frame != s.frame:
            raise RetractRefused(
                "Zmieniono program, narzędzie, układ lub stan modalny; zatrzymaj maszynę.")

    def start(self, s, height, feed):
        if self.active:
            raise RetractRefused("Najpierw zakończ poprzednie wycofanie.")
        self._check(s)
        if not s.settled:
            raise RetractRefused("Poczekaj na dotrzymanie pozycji przez napędy.")
        if not all(math.isfinite(x) and x > 0 for x in (height, feed)):
            raise RetractRefused("Wysokość i posuw muszą być dodatnie i skończone.")
        # HAL accepts whole counts at 0.001 native units. Validate the height
        # that will actually be sent, especially on an inch machine.
        height = round(height, 3)
        if height <= 0:
            raise RetractRefused("Wysokość jest mniejsza niż rozdzielczość external offsets.")
        if max(abs(s.offset), abs(s.requested)) > self.tolerance:
            raise RetractRefused("Inna funkcja używa już przesunięcia Z.")
        if not s.lower + 0.01 < s.z < s.z + height < s.upper - 0.01:
            raise RetractRefused("Wycofanie przekroczyłoby limit Z; zmniejsz wysokość.")
        self.frame, self.height, self.speed = s.frame, height, feed / 60
        self.target, self.resume, self.phase = 0.0, False, "arming"
        self.message = "Oczekiwanie na potwierdzenie external offsets z HAL."

    def return_to_path(self, s, resume=False):
        if self.phase != "retracted":
            raise RetractRefused("Najpierw poczekaj na zakończenie wycofania.")
        self._check(s)
        if not s.settled:
            raise RetractRefused("Poczekaj na dotrzymanie pozycji przez napędy.")
        self.phase, self.resume = "returning", resume
        self.message = "Powrót w Z do skorygowanego punktu pauzy."

    def fail(self, text):
        if self.active:
            self.phase, self.resume = "fault", False
        self.message = text

    def tick(self, s, dt):
        """Return True once, when a requested resume can be issued after HAL release."""
        if not s.powered:
            self.phase, self.frame = "idle", None
            self.target, self.resume = 0.0, False
            self.message = "Maszyna wyłączona; poprzednie wznowienie anulowane."
            return False
        if not self.active or self.phase == "fault":
            return False
        try:
            self._check(s)
        except RetractRefused as exc:
            self.fail(str(exc))
            return False
        step = self.speed * min(max(dt, 0), 0.1)
        if self.phase == "arming":
            if not s.offset_enabled:
                return False  # Own first; wait for the servo thread before changing counts.
            self.phase = "retracting"
            self.message = "Wycofywanie Z. Program i G41/G42 pozostają w pauzie."
        if self.phase == "retracting":
            self.target = min(self.height, self.target + step)
            if (abs(s.offset - self.height) <= self.tolerance
                    and self.target == self.height and s.settled):
                self.phase = "retracted"
                self.message = "Wycofano. Powrót zachowa G41/G42 i kolejkę programu."
        elif self.phase == "returning":
            self.target = max(0.0, self.target - step)
            if (self.target == 0 and s.settled
                    and max(abs(s.offset), abs(s.requested)) <= self.tolerance):
                resume = self.resume
                self.phase, self.frame, self.resume = "idle", None, False
                self.message = "Powrót zakończony; korekcja narzędzia bez zmian."
                return resume
        return False
