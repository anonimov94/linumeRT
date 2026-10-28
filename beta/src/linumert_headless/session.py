"""Sesje klientów, deadman jogu i limiter poleceń.

SPDX-License-Identifier: GPL-2.0-or-later

Trzy zasady przeniesione z bramy web (sprawdzone w praktyce) i obowiązujące dla **każdego**
transportu — REST, WebSocket, CLI i SDK:

1. **Deadman jogu.** Jog ciągły trwa ``jog_hold_s`` od ostatniego odświeżenia i należy do
   jednej sesji. Po wygaśnięciu, rozłączeniu sesji albo E-STOP usługa wysyła stop jogu
   i ponawia go, dopóki się nie powiedzie. To nie jest funkcja bezpieczeństwa: przed
   sprzętem wymagane jest wiązanie ``heartbeat`` z watchdogiem HAL (E-STOP).
2. **Brak zwolnienia E-STOP z GUI.** ``machine.estop_reset`` istnieje w kontrakcie, ale
   domyślnie wymaga roli serwisu i potwierdzenia — reset E-STOP pozostaje w sprzęcie.
3. **Limiter poleceń.** Wiadro tokenów chroni LinuxCNC przed zalaniem przez błąd lub atak
   z GUI. Polecenia zatrzymujące (``safety="stop"``) limitera nie podlegają.
"""

from __future__ import annotations

import itertools
import threading
import time
from collections.abc import Callable

from .errors import RateLimited

JOG_HOLD_S = 0.4          # klient odświeża jog co ~100–150 ms
HEARTBEAT_S = 1.0         # tyle życia klienta uznajemy za „ekran żyje"
COMMAND_RATE = 60.0       # poleceń/s
COMMAND_BURST = 60.0


class RateLimiter:
    """Wiadro tokenów: ``rate`` poleceń/s, seria do ``burst``."""

    def __init__(self, rate: float = COMMAND_RATE, burst: float = COMMAND_BURST,
                 clock: Callable[[], float] = time.monotonic):
        self.rate, self._burst, self._clock = rate, burst, clock
        self._tokens, self._last = burst, clock()

    def allow(self, cost: float = 1.0) -> bool:
        now = self._clock()
        self._tokens = min(self._burst, self._tokens + (now - self._last) * self.rate)
        self._last = now
        if self._tokens < cost:
            return False
        self._tokens -= cost
        return True


class SessionManager:
    """Rejestr sesji klientów i nadzór jogu."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 jog_hold_s: float = JOG_HOLD_S, heartbeat_s: float = HEARTBEAT_S,
                 command_rate: float = COMMAND_RATE):
        self._clock = clock
        self._hold = jog_hold_s
        self._heartbeat = heartbeat_s
        self._lock = threading.RLock()
        self._ids = itertools.count(1)
        self._sessions: dict[str, float] = {}          # sesja → ostatnia aktywność
        self._jog: dict[str, tuple[str, float]] = {}   # oś → (sesja, termin)
        self._increments: set[str] = set()             # osie w jogu przyrostowym
        self._limiter = RateLimiter(command_rate, command_rate, clock)

    # ---- sesje -------------------------------------------------------------
    def open(self) -> str:
        with self._lock:
            session = f"s{next(self._ids)}"
            self._sessions[session] = self._clock()
            return session

    def touch(self, session: str) -> None:
        with self._lock:
            if session in self._sessions:
                self._sessions[session] = self._clock()

    def close(self, session: str) -> list[str]:
        """Kończy sesję i zwraca osie, którym trzeba zatrzymać jog."""
        with self._lock:
            self._sessions.pop(session, None)
            axes = [a for a, (owner, _) in self._jog.items() if owner == session]
            for axis in axes:
                self._jog.pop(axis, None)
            return axes

    def alive(self) -> list[str]:
        now = self._clock()
        with self._lock:
            return [s for s, t in self._sessions.items() if now - t <= self._heartbeat]

    # ---- limiter -----------------------------------------------------------
    def charge(self, *, stopping: bool) -> None:
        """Pobiera token; polecenia zatrzymujące przechodzą zawsze."""
        if stopping or self._limiter.allow():
            return
        raise RateLimited("za dużo poleceń — GUI powinno odświeżać stan, nie wysyłać serię")

    # ---- jog ---------------------------------------------------------------
    def jog_start(self, axis: str, session: str) -> None:
        with self._lock:
            self._jog[axis] = (session, self._clock() + self._hold)
            self._increments.discard(axis)

    def jog_increment(self, axis: str) -> None:
        with self._lock:
            self._increments.add(axis)
            self._jog.pop(axis, None)

    def jog_stop(self, axis: str | None) -> None:
        with self._lock:
            if axis is None:
                self._jog.clear()
                self._increments.clear()
            else:
                self._jog.pop(axis, None)
                self._increments.discard(axis)

    def expired_jog(self) -> list[str]:
        """Osie, którym deadman wygasł — usługa musi wysłać stop (i ponawiać)."""
        now = self._clock()
        with self._lock:
            expired = [a for a, (_, deadline) in self._jog.items() if now >= deadline]
            for axis in expired:
                self._jog.pop(axis, None)
            return expired

    def active_jog(self) -> dict[str, str]:
        with self._lock:
            return {a: owner for a, (owner, _) in self._jog.items()}

    def owned_by_other(self, axis: str, session: str) -> bool:
        """Jog przyrostowy/ciągły należy do jednej sesji — inna go nie odświeży."""
        with self._lock:
            owner = self._jog.get(axis, (None, 0))[0]
            return owner is not None and owner != session


__all__ = ["COMMAND_RATE", "HEARTBEAT_S", "JOG_HOLD_S", "RateLimiter", "SessionManager"]
