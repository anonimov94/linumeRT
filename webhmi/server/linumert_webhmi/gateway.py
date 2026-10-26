"""Brama: wątek odpytujący maszynę, nadzór jogu, wykonywanie poleceń.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Brama działa poza RT (zwykły wątek Pythona), jak panel Plant. Trzy zasady bezpieczeństwa:
- **Deadman jogu:** ciągły jog trwa tylko ``jog_hold_s`` od ostatniego odświeżenia z przeglądarki
  i należy do jednej sesji (inna sesja go nie odświeży). Po wygaśnięciu, po rozłączeniu sesji
  właściciela albo po ``estop`` brama wysyła stop jogu i ponawia go, dopóki się nie powiedzie.
  To nie jest funkcja bezpieczeństwa: ciągły jog w LinuxCNC trwa dalej, gdy proces bramy padnie;
  dlatego przed sprzętem wymagane jest wiązanie ``heartbeat`` z ``watchdog`` HAL (E-STOP).
- **Brak zwolnienia E-STOP:** brama nie ma polecenia resetu (CLAUDE.md §6, D35/D37).
- **Limit poleceń:** wiadra tokenów, żeby błąd lub atak z przeglądarki nie zalał LinuxCNC; polecenia
  zatrzymujące (``estop``, ``stop``, ``pause``, ``jog_stop``, ``power_off``, ``jog`` z prędkością 0)
  limitera nie podlegają.
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

STOP_COMMANDS = frozenset({"estop", "stop", "pause", "jog_stop", "power_off"})
LOCAL_SESSION = "local"  # polecenia z REST (bez sesji WebSocket)
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
        self._jog: dict[str, tuple[str, float]] = {}  # os -> (sesja, termin)
        self._jog_retry: set[str] = set()  # osie, dla których stop jogu się nie udał
        self._limiter = RateLimiter(command_rate, command_rate, clock)
        self._sessions: dict[str, float] = {}  # sesja -> ostatnia aktywność
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
                    self._stop_all_jog()  # bez wiarygodnego stanu nie ma ciągłego jogu
                    self._version += 1
                    self._state = {**self._state, "gateway_error": str(error)}

    def step(self) -> None:
        """Jeden obieg: czas atrapy, wygaśnięcie jogu, nowa migawka."""
        with self._lock:
            now = self._clock()
            # najpierw wygaszanie jogu: błąd odczytu nie może go odsunąć
            for axis in [a for a, (_, until) in self._jog.items() if now >= until]:
                self._stop_axis(axis)
            self._retry_stops()
            self.backend.tick()
            state = snapshot_to_dict(self.backend.snapshot())
            state["heartbeat"] = any(now - seen <= HEARTBEAT_S
                                     for seen in self._sessions.values())
            state["jog_active"] = sorted(self._jog)
            state.pop("gateway_error", None)
            if state != self._state:
                self._version += 1
                self._state = state

    # ---- klienci ------------------------------------------------------------
    def client_connected(self, session: str = LOCAL_SESSION) -> None:
        with self._lock:
            self._sessions[session] = self._clock()

    def client_disconnected(self, session: str = LOCAL_SESSION) -> None:
        """Rozłączenie zdejmuje jogi tej sesji; ostatnia sesja zdejmuje wszystkie."""
        with self._lock:
            self._sessions.pop(session, None)
            for axis in [a for a, (owner, _) in self._jog.items() if owner == session]:
                self._stop_axis(axis)
            if not self._sessions:
                self._stop_all_jog()

    def touch(self, session: str = LOCAL_SESSION) -> None:
        """Przeglądarka żyje (wiadomość z klienta); zasila ``heartbeat`` w stanie."""
        with self._lock:
            if session in self._sessions or session == LOCAL_SESSION:
                self._sessions[session] = self._clock()

    def snapshot(self) -> tuple[int, dict]:
        with self._lock:
            return self._version, dict(self._state)

    # ---- polecenia ------------------------------------------------------------
    def _stop_axis(self, axis: str) -> None:
        """Zdejmuje jog osi; przy błędzie backendu zostaje do ponowienia w kolejnym obiegu."""
        self._jog.pop(axis, None)
        try:
            self.backend.jog_stop(axis)
            self._jog_retry.discard(axis)
        except Exception:  # noqa: BLE001 - stop musi być ponawiany, nie gubiony
            self._jog_retry.add(axis)

    def _stop_all_jog(self) -> None:
        self._jog.clear()
        try:
            self.backend.jog_stop(None)
            self._jog_retry.clear()
        except Exception:  # noqa: BLE001
            self._jog_retry.add("*")

    def _retry_stops(self) -> None:
        for axis in sorted(self._jog_retry):
            if axis == "*":
                self._stop_all_jog()
            else:
                self._stop_axis(axis)

    def execute(self, command: Command, session: str = LOCAL_SESSION) -> None:
        """Wykonuje polecenie; ``CommandError`` z komunikatem dla operatora przy odmowie."""
        with self._lock:
            stop = command.cmd in STOP_COMMANDS or (command.cmd == "jog" and command.speed == 0.0)
            if not stop and not self._limiter.allow():
                raise CommandError("zbyt wiele poleceń na sekundę")
            self.touch(session)
            self._dispatch(command, session)

    def _dispatch(self, c: Command, session: str) -> None:
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
            owner = self._jog.get(c.axis, (session, 0.0))[0]
            if c.speed == 0.0:
                self._stop_axis(c.axis)
            elif owner != session:
                raise CommandError(f"jog osi {c.axis} trwa w innej sesji")
            else:
                b.jog(c.axis, c.speed)
                self._jog[c.axis] = (session, self._clock() + self._hold)
        elif name == "jog_stop":
            if c.axis is None:
                self._stop_all_jog()
            else:
                self._stop_axis(c.axis)
