"""Brama: wątek odpytujący maszynę, nadzór jogu, wykonywanie poleceń.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Brama działa poza RT (zwykły wątek Pythona), jak panel Plant. Trzy zasady bezpieczeństwa:
- **Deadman jogu:** ciągły jog trwa tylko ``jog_hold_s`` od ostatniego odświeżenia z przeglądarki
  i należy do jednej sesji (inna sesja go nie odświeży). Po wygaśnięciu, po rozłączeniu sesji
  właściciela albo po ``estop`` brama wysyła stop jogu i ponawia go, dopóki się nie powiedzie.
  To nie jest funkcja bezpieczeństwa: ciągły jog w LinuxCNC trwa dalej, gdy proces bramy padnie;
  z ``hal_pins`` (``--hal``) brak sygnału życia otwiera łańcuch E-STOP przez ``watchdog`` HAL
  (``hal_link.py``).
- **E-STOP tylko przez zatrzask HAL:** ``reset`` to pojedynczy Reset z D37: kasuje alarmy, których
  przyczyna ustała; alarm E-STOP (E-1100) i krańcówki (E-1200) wracają, dopóki przyczyna trwa.
  Podwójny Reset (``double``) potwierdza E-STOP w zatrzasku HAL (impuls ``hmi-ack``) i żąda
  ``ESTOP_RESET`` — wyłącznie z ``hal_pins``; bez nich brama E-STOP nie zwalnia (CLAUDE.md §6).
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
from typing import TYPE_CHECKING

from linumert.alarms.manager import AlarmManager
from linumert.cnc import MachineSnapshot, Mode

from .backend import CommandError, MachineBackend
from .hal_link import HalPins
from .schema import Command, snapshot_to_dict

if TYPE_CHECKING:
    from .job_instance import Instance

STOP_COMMANDS = frozenset({"estop", "stop", "pause", "jog_stop", "power_off"})
LOCAL_SESSION = "local"  # polecenia z REST (bez sesji WebSocket)
POLL_HZ = 50.0
JOG_HOLD_S = 0.4  # klient odświeża jog co ~100-150 ms
HEARTBEAT_S = 1.0  # tyle życia przeglądarki uznajemy za "ekran żyje"
ESTOP_RESET_DELAY_S = 0.3  # po impulsie ack, jak ekran Qt (zatrzask zdąży się ustawić)
ALARM_RESET_DELAY_S = 0.7  # po ESTOP_RESET: pojedynczy Reset alarmów (ekran Qt: 700 ms)
PROGRAMS_S = 2.0  # odświeżanie listy programów
MAX_ALARMS = 20  # tyle aktywnych alarmów idzie do przeglądarki (najnowsze)


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
                 jog_hold_s: float = JOG_HOLD_S, command_rate: float = 60.0,
                 hal_pins: HalPins | None = None, instance: Instance | None = None):
        self.backend = backend
        self._instance = instance
        self._hal = hal_pins
        self._estop_reset_at: float | None = None
        self._alarm_reset_at: float | None = None
        self._clock = clock
        self._hold = jog_hold_s
        self._lock = threading.RLock()
        self._jog: dict[str, tuple[str, float]] = {}  # os -> (sesja, termin)
        self._increment_axes: set[str] = set()
        self._jog_retry: set[str] = set()  # osie, dla których stop jogu się nie udał
        self._limiter = RateLimiter(command_rate, command_rate, clock)
        self._sessions: dict[str, float] = {}  # sesja -> ostatnia aktywność
        self._alarms = AlarmManager(clock=clock)
        self._programs: tuple[str, ...] = ()
        self._programs_at = -PROGRAMS_S
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
            self._pending_estop_reset(now)
            self.backend.tick()
            snap = self.backend.snapshot()
            if self._alarm_reset_at is not None and now >= self._alarm_reset_at:
                self._alarm_reset_at = None
                self._alarms.reset()  # przed zgłoszeniem: trwający E-STOP wraca w tym obiegu
            self._raise_alarms(snap)
            if now - self._programs_at >= PROGRAMS_S:
                self._programs, self._programs_at = self.backend.programs(), now
            state = snapshot_to_dict(snap)
            if self._instance is not None:
                state["execution"] = self._instance.status()
            state["alarms"] = self._alarm_rows()
            state["programs"] = list(self._programs)
            state["heartbeat"] = any(now - seen <= HEARTBEAT_S
                                     for seen in self._sessions.values())
            state["hmi_hal"] = self._hal is not None
            if self._hal is not None:
                # Po odczycie stanu: zawieszony odczyt maszyny też gasi sygnał życia.
                self._hal.tick(now, state["heartbeat"])
            state["jog_active"] = sorted(self._jog)
            state["jog_stop_pending"] = sorted(self._jog_retry)
            state.pop("gateway_error", None)
            if state != self._state:
                self._version += 1
                self._state = state

    # ---- alarmy (katalog core/linumert/alarms/catalog.yaml) --------------------
    def _raise_alarms(self, snap: MachineSnapshot) -> None:
        """Komunikaty LinuxCNC i trwające przyczyny (E-STOP, krańcówka) jako alarmy z katalogu."""
        for message in snap.errors:
            self._alarms.raise_alarm("E-1000", message=message)
        causes = [("E-1100", {})] if snap.task_state.value == "estop" else []
        # Czujnik bazy bywa krańcówką (``home_sensor: shared_with``): bazowanie najeżdża na nią
        # celowo, więc alarm krańcówki liczymy dopiero po bazowaniu wszystkich osi.
        causes += [("E-1200", {"axis": a.name})
                   for a in (snap.axes if snap.all_homed else ()) if a.limit_hit]
        # Trwająca przyczyna to jedno zgłoszenie, nie jedno na obieg (licznik = wystąpienia).
        active = [(a.code, a.params) for a in self._alarms.active()]
        for code, params in causes:
            if (code, params) not in active:
                self._alarms.raise_alarm(code, **params)

    def _alarm_rows(self) -> list[dict]:
        rows = sorted(self._alarms.active(), key=lambda a: a.id, reverse=True)[:MAX_ALARMS]
        return [{"id": a.id, "code": a.code, "text": self._alarms.message(a),
                 "count": a.count} for a in rows]

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
            if session in self._sessions:  # REST nie tworzy trwałej sesji
                self._sessions[session] = self._clock()

    def snapshot(self) -> tuple[int, dict]:
        with self._lock:
            return self._version, dict(self._state)

    # ---- potwierdzenie E-STOP (podwójny Reset, D37) ------------------------------
    def _acknowledge_estop(self) -> None:
        if self._hal is None:
            raise CommandError("podwójny Reset: brama bez pinów HAL (--hal) nie potwierdza "
                               "E-STOP; reset zatrzasku poza bramą")
        if self._state.get("task_state") != "estop":
            return  # nie ma czego potwierdzać; pojedynczy Reset alarmów niżej
        now = self._clock()
        self._hal.acknowledge(now)
        self._estop_reset_at = now + ESTOP_RESET_DELAY_S

    def _pending_estop_reset(self, now: float) -> None:
        if self._estop_reset_at is None or now < self._estop_reset_at:
            return
        self._estop_reset_at = None
        try:
            self.backend.estop_reset()
        except Exception as error:  # noqa: BLE001 - odmowa resetu to komunikat, nie awaria wątku
            self._alarms.raise_alarm("E-1000", message=f"potwierdzenie E-STOP: {error}")
            return
        self._alarm_reset_at = now + ALARM_RESET_DELAY_S

    def _cancel_estop_reset(self) -> None:
        pending = self._estop_reset_at is not None
        self._estop_reset_at = self._alarm_reset_at = None
        if pending and self._hal is not None:
            self._hal.cancel_acknowledge()

    # ---- polecenia ------------------------------------------------------------
    def _stop_axis(self, axis: str) -> None:
        """Zdejmuje jog osi; przy błędzie backendu zostaje do ponowienia w kolejnym obiegu."""
        self._jog.pop(axis, None)
        self._increment_axes.discard(axis)
        try:
            self.backend.jog_stop(axis)
            self._jog_retry.discard(axis)
        except Exception:  # noqa: BLE001 - stop musi być ponawiany, nie gubiony
            self._jog_retry.add(axis)

    def _stop_all_jog(self) -> None:
        self._jog.clear()
        self._increment_axes.clear()
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
            if stop and self._jog_retry:
                raise CommandError("zatrzymanie jogu niepotwierdzone przez LinuxCNC; "
                                   "brama ponawia je automatycznie")

    def _dispatch(self, c: Command, session: str) -> None:
        b = self.backend
        name = c.cmd
        if self._instance is not None and name in ("run", "resume"):
            raise CommandError(self._instance.status()["reason"])
        if name == "estop":
            self._stop_all_jog()
            try:
                b.estop()
            finally:  # błąd zapisu pinów HAL nie może zablokować wysłania zatrzymania
                self._cancel_estop_reset()
        elif name == "power_on":
            b.power_on()
        elif name == "power_off":
            self._stop_all_jog()
            try:
                b.power_off()
            finally:
                self._cancel_estop_reset()
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
            try:
                b.stop()
            finally:
                self._cancel_estop_reset()
        elif name == "override":
            if c.feed is None and c.rapid is None and c.spindle is None:
                raise CommandError("override: podaj feed, rapid lub spindle")
            b.set_override(c.feed, c.rapid, c.spindle)
        elif name == "jog":
            if c.axis is None or c.speed is None:
                raise CommandError("jog: wymagane axis i speed")
            if c.speed != 0.0 and self._jog_retry:
                self._retry_stops()
                if self._jog_retry:  # stary stop niepotwierdzony: nie startujemy nowego ruchu
                    raise CommandError("jog zablokowany: poprzednie zatrzymanie niepotwierdzone")
            owner = self._jog.get(c.axis, (session, 0.0))[0]
            if c.speed == 0.0:
                self._stop_axis(c.axis)
            elif c.axis in self._increment_axes:
                raise CommandError("jog: najpierw zatrzymaj poprzedni ruch przyrostowy")
            elif owner != session:
                raise CommandError(f"jog osi {c.axis} trwa w innej sesji")
            else:
                b.jog(c.axis, c.speed)
                self._jog[c.axis] = (session, self._clock() + self._hold)
        elif name == "jog_increment":
            if c.axis is None or c.speed is None or c.speed == 0 or c.distance is None:
                raise CommandError("jog przyrostowy: wymagane axis, niezerowa speed i distance")
            if self._jog_retry:
                self._retry_stops()
                if self._jog_retry:
                    raise CommandError("jog zablokowany: poprzednie zatrzymanie niepotwierdzone")
            if c.axis in self._jog:
                raise CommandError("jog: najpierw zatrzymaj poprzedni ruch osi")
            if self._state.get("gateway_error"):
                raise CommandError("jog: brak wiarygodnego stanu maszyny")
            b.jog_increment(c.axis, c.speed, c.distance)
            self._increment_axes.add(c.axis)
            self._jog[c.axis] = (session, self._clock() + self._hold)
        elif name == "jog_keepalive":
            if c.axis not in self._increment_axes:
                raise CommandError("jog: brak aktywnego ruchu przyrostowego")
            if self._jog[c.axis][0] != session:
                raise CommandError("jog osi trwa w innej sesji")
            self._jog[c.axis] = (session, self._clock() + self._hold)
        elif name == "jog_stop":
            if c.axis is None:
                self._stop_all_jog()
            else:
                self._stop_axis(c.axis)
        elif name == "work_zero":
            if self._jog_retry:
                raise CommandError("zero detalu: niepotwierdzone zatrzymanie JOG")
            if self._jog:
                raise CommandError("zero detalu: najpierw zatrzymaj JOG")
            b.work_zero(c.axis)
        elif name == "open":
            if c.name is None:
                raise CommandError("program: brak nazwy pliku")
            self._stop_all_jog()
            if self._jog_retry:
                raise CommandError("program: niepotwierdzone zatrzymanie JOG")
            b.open_program(c.name)
        elif name == "reset":
            if c.double:
                self._acknowledge_estop()
            self._alarms.reset()
            self.step()  # trwające przyczyny wracają od razu, nie po kolejnym obiegu
