"""Backend maszyny: atrapa z zegarem rzeczywistym (`FakeBackend`).

SPDX-License-Identifier: GPL-2.0-or-later

Backend domyślny aplikacji headless — pozwala uruchomić **całą** funkcjonalność (sterowanie,
programy, symulacja, Plant, diagnostyka) bez LinuxCNC i bez sprzętu. Oś ruchu liczy
``linumert.cnc.fake.FakeMachine``; backend dokłada to, czego wymaga port ``MachinePort``:

- wątek czasu: ``advance(dt)`` z zegara hosta, więc maszyna „żyje" bez GUI,
- jog przyrostowy: ruch ciągły zatrzymany po przejechaniu zadanego dystansu,
- wrzeciono przez MDI (``S… M3/M4/M5``) — tak samo robi LinuxCNC,
- ``load_program`` z tekstu (LinuxCNC czyta plik, atrapa dostaje linie).

Atrapa nie jest wzorcem zachowania LinuxCNC: pozycja rzeczywista równa się zadanej, dynamikę
dopiero Plant. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from linumert.cnc.fake import FakeMachine
from linumert.cnc.model import MachineSnapshot, Mode

from ..errors import BackendUnavailable, Conflict, SafetyRefused

STEP_S = 0.02  # 50 Hz — tyle samo co pętla odpytująca bramy


class FakeBackend:
    """``MachinePort`` na atrapie; czas płynie w wątku tła."""

    name = "fake"
    # Atrapa nie ma interpretera podprogramów ani G38.x — sondowanie wymaga LinuxCNC.
    capabilities: frozenset[str] = frozenset()

    def __init__(self, machine: FakeMachine | None = None, *,
                 axes: tuple[str, ...] = ("X", "Y", "Z"),
                 limits: dict[str, tuple[float, float]] | None = None,
                 clock: Callable[[], float] = time.monotonic, autostart: bool = True,
                 step_s: float = STEP_S):
        self.machine = machine or FakeMachine(axes=axes, limits=limits)
        self._clock = clock
        self._step = step_s
        self._lock = threading.RLock()
        self._increments: dict[str, tuple[float, float]] = {}  # oś → (start, dystans)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if autostart:
            self.start()

    # ---- cykl życia --------------------------------------------------------
    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="fake-machine", daemon=True)
            self._thread.start()

    def shutdown(self) -> None:
        """Zatrzymuje wątek czasu (cykl życia backendu — nie mylić ze ``stop()`` ruchu)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _loop(self) -> None:
        last = self._clock()
        while not self._stop.is_set():
            time.sleep(self._step)
            now = self._clock()
            dt, last = now - last, now
            self.advance(min(dt, 0.5))

    def advance(self, dt: float) -> None:
        """Przesuwa zegar wirtualny (API backendu; testy wołają to zamiast ``machine.advance``).

        Czas jest cięty na plasterki cyklu serwo, bo nadzór jogu przyrostowego działa tylko
        między plasterkami: bez tego jeden duży krok przejechałby cały dystans i zatrzymał
        się dopiero po nim. Nadzór jest tu, a nie tylko w wątku, żeby działał także gdy
        wątek czasu nie biegnie (``autostart=False``).
        """
        remaining = max(dt, 0.0)
        with self._lock:
            while remaining > 1e-9:
                step = min(self._step, remaining, self._increment_cap())
                if step <= 1e-12:
                    # Dystans już przejechany — domykamy nadzór i idziemy dalej.
                    self._stop_finished_increments()
                    step = min(self._step, remaining)
                    if not self._increments:
                        self.machine.advance(step)
                        remaining -= step
                        continue
                self.machine.advance(step)
                remaining -= step
                self._stop_finished_increments()

    def _increment_cap(self) -> float:
        """Najdłuższy krok, który nie przejedzie zadanego dystansu jogu przyrostowego.

        Bez tego krok zatrzymywałby się dopiero po całym plasterku cyklu serwo, czyli
        z przelotem rzędu ``predkosc * krok`` (np. 0,2 mm przy 10 mm/s i 20 ms).
        """
        snapshot = self.machine.snapshot()
        cap = self._step
        for axis, (start, distance) in self._increments.items():
            speed = abs(self.machine._jog.get(axis, 0.0))
            if speed <= 0.0:
                continue
            left = distance - abs(snapshot.axis(axis).position - start)
            cap = min(cap, max(left / speed, 0.0))
        return cap

    def _stop_finished_increments(self) -> None:
        """Zatrzymuje jog przyrostowy, który dojechał do swojego dystansu."""
        snapshot = self.machine.snapshot()
        for axis, (start, distance) in list(self._increments.items()):
            if abs(snapshot.axis(axis).position - start) >= distance - 1e-9:
                self.machine.jog_stop(axis)
                self._increments.pop(axis, None)

    def tick(self) -> None:
        """Odświeżenie z pętli aplikacji: pilnuje jogu przyrostowego.

        Przy ``autostart=True`` czas płynie w wątku, więc ``tick`` tylko domyka nadzór;
        przy ``autostart=False`` (testy) zegar przesuwa wywołujący przez ``advance``.
        """
        with self._lock:
            self._stop_finished_increments()

    # ---- stan --------------------------------------------------------------
    def now(self) -> float:
        """Zegar symulowany — tym samym czasem stemplowana jest migawka."""
        return self.machine.time

    def snapshot(self) -> MachineSnapshot:
        with self._lock:
            return self.machine.snapshot()

    # ---- polecenia ---------------------------------------------------------
    def estop(self) -> None:
        with self._lock:
            self._increments.clear()
            self.machine.estop()

    def estop_reset(self) -> None:
        with self._lock:
            if not self.machine.estop_reset():
                raise Conflict("reset E-STOP odrzucony przez maszynę")

    def power_on(self) -> None:
        with self._lock:
            if not self.machine.power_on():
                raise Conflict("włączenie zasilania odrzucone (sprawdź E-STOP)")

    def power_off(self) -> None:
        with self._lock:
            self._increments.clear()
            self.machine.power_off()

    def set_mode(self, mode: Mode) -> None:
        with self._lock:
            if not self.machine.set_mode(mode):
                raise Conflict(f"zmiana trybu na {mode.value} odrzucona")

    def home(self, axis: str | None) -> None:
        axes = None if axis is None else (axis.upper(),)
        with self._lock:
            if not self.machine.home(axes):
                raise SafetyRefused("bazowanie odrzucone (maszyna wyłączona albo ruch w toku)")

    def mdi(self, text: str) -> None:
        with self._lock:
            if not self.machine.mdi(text):
                raise Conflict(f"MDI odrzucone: {text!r}")

    def load_program(self, name: str, text: str) -> None:
        lines = [line for line in text.splitlines() if line.strip()]
        with self._lock:
            if not self.machine.load_program(lines, name):
                raise Conflict(f"wczytanie programu {name} odrzucone")

    def run(self, from_line: int = 1) -> None:
        with self._lock:
            if not self.machine.run(from_line):
                raise Conflict("start programu odrzucony (tryb AUTO albo brak programu)")

    def pause(self) -> None:
        with self._lock:
            if not self.machine.pause():
                raise Conflict("pauza odrzucona (program nie biegnie)")

    def resume(self) -> None:
        with self._lock:
            if not self.machine.resume():
                raise Conflict("wznowienie odrzucone (program nie jest wstrzymany)")

    def stop(self) -> None:
        with self._lock:
            self._increments.clear()
            self.machine.stop()

    def set_override(self, feed: float | None = None, rapid: float | None = None,
                     spindle: float | None = None) -> None:
        with self._lock:
            self.machine.set_override(feed=feed, rapid=rapid, spindle=spindle)

    def spindle(self, speed: float, direction: int) -> None:
        code = {1: "M3", -1: "M4", 0: "M5"}[direction]
        with self._lock:
            if not self.machine.mdi(f"S{speed:g} {code}"):
                raise Conflict(f"polecenie wrzeciona {code} S{speed:g} odrzucone")

    def jog(self, axis: str, speed: float) -> None:
        with self._lock:
            self._increments.pop(axis.upper(), None)
            if not self.machine.jog(axis, speed):
                raise SafetyRefused("jog odrzucony (wymagany tryb MANUAL, zasilanie włączone)")

    def jog_increment(self, axis: str, speed: float, distance: float) -> None:
        name = axis.upper()
        with self._lock:
            start = self.machine.snapshot().axis(name).position
            if not self.machine.jog(name, speed):
                raise SafetyRefused("jog przyrostowy odrzucony (tryb MANUAL, zasilanie)")
            self._increments[name] = (start, distance)

    def jog_stop(self, axis: str | None) -> None:
        with self._lock:
            if axis is None:
                self._increments.clear()
            else:
                self._increments.pop(axis.upper(), None)
            self.machine.jog_stop(axis)

    def set_work_offset(self, name: str, values: dict[str, float]) -> None:
        with self._lock:
            self.machine.set_work_offset(name, **values)

    def close(self) -> None:
        self.shutdown()


def require_backend(backend: object | None) -> object:
    if backend is None:
        raise BackendUnavailable("backend maszyny nie jest skonfigurowany")
    return backend


__all__ = ["FakeBackend", "require_backend"]
