"""Brama: wątek odpytujący maszynę, nadzór jogu, wykonywanie poleceń.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Brama działa poza RT (zwykły wątek Pythona), jak panel Plant. Trzy zasady bezpieczeństwa:
- **Deadman jogu:** ciągły jog trwa tylko ``jog_hold_s`` od ostatniego odświeżenia z przeglądarki;
  po tym czasie, po utracie ostatniego klienta albo po ``estop`` brama sama wysyła stop jogu.
- **Brak zwolnienia E-STOP:** brama nie ma polecenia resetu (CLAUDE.md §6, D35/D37).
- **Limit poleceń:** wiadra tokenów, żeby błąd lub atak z przeglądarki nie zalał LinuxCNC.
Stan dla klientów to ostatnia migawka z wątku; klienci nie odpytują maszyny sami.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from linumert.cnc import Mode

from .backend import CommandError, MachineBackend
from .schema import Command, snapshot_to_dict

POLL_HZ = 50.0
JOG_HOLD_S = 0.4  # klient odświeża jog co ~100-150 ms
HEARTBEAT_S = 1.0  # tyle życia przeglądarki uznajemy za "ekran żyje"


class RateLimiter:
    """Wiadro tokenów: ``rate`` poleceń/s, seria do ``burst``."""

    def __init__(self, rate: float, burst: float, clock: Callable[[], float] = time.monotonic):
        self.rate, self.burst, self._clock = rate, burst, clock
        self._tokens, self._last = burst, clock()

    def allow(self) -> bool:
        now = self._clock()
        self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
        self._last = now
        if self._tokens < 1.0:
            return False
        self._tokens -= 1.0
        return True


class Gateway:
    def __init__(self, backend: MachineBackend, clock: Callable[[], float] = time.monotonic,
                 jog_hold_s: float = JOG_HOLD_S, command_rate: float = 60.0):
        self.backend = backend
        self._clock = clock
        self._hold = jog_hold_s
        self._lock = threading.RLock()
        self._jog_until: dict[str, float] = {}
        self._limiter = RateLimiter(command_rate, command_rate, clock)
        self._clients = 0
        self._last_seen = float("-inf")
        self._version = 0
        self._state: dict = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.step()

    # ---- wątek odpytujący ---------------------------------------------------
    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="webhmi-poll", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        with self._lock:
            self._stop_all_jog()

    def _loop(self) -> None:
        period = 1.0 / POLL_HZ
        while not self._stop.wait(period):
            try:
                self.step()
            except Exception as error:  # noqa: BLE001 - wątek nie może zginąć po błędzie odczytu
                with self._lock:
                    self._version += 1
                    self._state = {**self._state, "gateway_error": str(error)}

    def step(self) -> None:
        """Jeden obieg: czas atrapy, wygaśnięcie jogu, nowa migawka."""
        with self._lock:
            self.backend.tick()
            now = self._clock()
            for axis in [a for a, until in self._jog_until.items() if now >= until]:
                self._jog_until.pop(axis)
                self.backend.jog_stop(axis)
            state = snapshot_to_dict(self.backend.snapshot())
            state["heartbeat"] = self._clients > 0 and now - self._last_seen <= HEARTBEAT_S
            state["jog_active"] = sorted(self._jog_until)
            state.pop("gateway_error", None)
            if state != self._state:
                self._version += 1
                self._state = state

    # ---- klienci ------------------------------------------------------------
    def client_connected(self) -> None:
        with self._lock:
            self._clients += 1
            self._last_seen = self._clock()

    def client_disconnected(self) -> None:
        with self._lock:
            self._clients = max(self._clients - 1, 0)
            if self._clients == 0:
                self._stop_all_jog()

    def touch(self) -> None:
        """Przeglądarka żyje (wiadomość z klienta); zasila ``heartbeat`` w stanie."""
        with self._lock:
            self._last_seen = self._clock()

    def snapshot(self) -> tuple[int, dict]:
        with self._lock:
            return self._version, dict(self._state)

    # ---- polecenia ------------------------------------------------------------
    def _stop_all_jog(self) -> None:
        self._jog_until.clear()
        self.backend.jog_stop(None)

    def execute(self, command: Command) -> None:
        """Wykonuje polecenie; ``CommandError`` z komunikatem dla operatora przy odmowie."""
        with self._lock:
            if not self._limiter.allow():
                raise CommandError("zbyt wiele poleceń na sekundę")
            self.touch()
            self._dispatch(command)

    def _dispatch(self, c: Command) -> None:
        b = self.backend
        name = c.cmd
        if name == "estop":
            self._stop_all_jog()
            b.estop()
        elif name == "power_on":
            b.power_on()
        elif name == "power_off":
            self._stop_all_jog()
            b.power_off()
        elif name == "mode":
            if c.mode is None:
                raise CommandError("tryb: brak parametru mode")
            self._stop_all_jog()
            b.set_mode(Mode(c.mode))
        elif name == "home":
            b.home(c.axis)
        elif name == "mdi":
            if c.text is None:
                raise CommandError("MDI: brak tekstu")
            b.mdi(c.text)
        elif name == "run":
            b.run(c.from_line)
        elif name == "pause":
            b.pause()
        elif name == "resume":
            b.resume()
        elif name == "stop":
            self._stop_all_jog()
            b.stop()
        elif name == "override":
            if c.feed is None and c.rapid is None and c.spindle is None:
                raise CommandError("override: podaj feed, rapid lub spindle")
            b.set_override(c.feed, c.rapid, c.spindle)
        elif name == "jog":
            if c.axis is None or c.speed is None:
                raise CommandError("jog: wymagane axis i speed")
            if c.speed == 0.0:
                self._jog_until.pop(c.axis, None)
                b.jog_stop(c.axis)
            else:
                b.jog(c.axis, c.speed)
                self._jog_until[c.axis] = self._clock() + self._hold
        elif name == "jog_stop":
            if c.axis is None:
                self._stop_all_jog()
            else:
                self._jog_until.pop(c.axis, None)
                b.jog_stop(c.axis)
