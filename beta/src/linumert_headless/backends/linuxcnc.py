"""Backend LinuxCNC (`LinuxCNCBackend`).

SPDX-License-Identifier: GPL-2.0-or-later

Ten sam port ``MachinePort`` co atrapa, więc usługi, transporty i GUI nie wiedzą, z którym
backendem rozmawiają. Czytanie stanu idzie przez ``linumert.cnc.linuxcnc_reader`` (wspólny
model ``MachineSnapshot``), polecenia przez ``linuxcnc.command``.

Zasady bezpieczeństwa (CLAUDE.md §6):
- brak odblokowania E-STOP przez GUI: ``estop_reset`` wymaga jawnej zgody i roli serwisu,
- polecenia zatrzymujące są wysyłane bezwarunkowo,
- błędy z ``linuxcnc.error`` trafiają do migawki (``errors``) i do dziennika, nie do tracebacka.

Wymaga LinuxCNC 2.9 (RIP albo pakiet Debiana). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import importlib
from typing import Any

from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert.cnc.model import MachineSnapshot, Mode

from ..errors import BackendUnavailable, Conflict, SafetyRefused

_MODE = {Mode.MANUAL: "MODE_MANUAL", Mode.AUTO: "MODE_AUTO", Mode.MDI: "MODE_MDI"}


class LinuxCNCBackend:
    """``MachinePort`` na ``linuxcnc.command``/``linuxcnc.stat``."""

    name = "linuxcnc"

    def __init__(self, module: Any = None, reader: LinuxCNCReader | None = None,
                 timeout: float = 2.0):
        self._module = module
        self._timeout = timeout
        self._command: Any = None
        # Czytnik sam tworzy `linuxcnc.stat()`; nazwy osi bierze z `stat.axis_mask`.
        self.reader = reader or LinuxCNCReader(module=module)

    # ---- dostęp do modułu --------------------------------------------------
    def _lc(self) -> Any:
        if self._module is None:
            try:
                self._module = importlib.import_module("linuxcnc")
            except ImportError as exc:
                raise BackendUnavailable(
                    "brak modułu linuxcnc — uruchom aplikację na LinuxCNC 2.9 "
                    "albo użyj backendu 'fake'") from exc
        return self._module

    def _cmd(self) -> Any:
        if self._command is None:
            self._command = self._lc().command()
        return self._command

    def _wait(self) -> None:
        cmd = self._cmd()
        cmd.wait_complete(self._timeout)

    # ---- stan --------------------------------------------------------------
    def tick(self) -> None:
        """Stan LinuxCNC płynie sam; odpytanie zdarza się w ``snapshot``."""

    def now(self) -> float:
        """Zegar czytaka — migawki LinuxCNC są stemplowane czasem systemowym."""
        return self._clock()

    def snapshot(self) -> MachineSnapshot:
        try:
            return self.reader.read()
        except Exception as exc:
            raise BackendUnavailable(f"odczyt stanu LinuxCNC nie powiódł się: {exc}") from exc

    # ---- polecenia ---------------------------------------------------------
    def estop(self) -> None:
        self._cmd().estop(self._lc().ESTOP_ACTIVATE)

    def estop_reset(self) -> None:
        self._cmd().estop(self._lc().ESTOP_RESET)

    def power_on(self) -> None:
        self._cmd().state(self._lc().STATE_ON)
        self._wait()

    def power_off(self) -> None:
        self._cmd().state(self._lc().STATE_OFF)
        self._wait()

    def set_mode(self, mode: Mode) -> None:
        self._cmd().mode(getattr(self._lc(), _MODE[mode]))
        self._wait()

    def home(self, axis: str | None) -> None:
        if axis is None:
            self._cmd().home(-1)
            return
        self._cmd().home(self._joint(axis))

    def mdi(self, text: str) -> None:
        self._cmd().mode(self._lc().MODE_MDI)
        self._wait()
        self._cmd().mdi(text)

    def load_program(self, name: str, text: str) -> None:
        """LinuxCNC czyta program z pliku — backend przyjmuje ścieżkę w ``name``."""
        self._cmd().mode(self._lc().MODE_AUTO)
        self._wait()
        self._cmd().program_open(name)
        self._wait()
        _ = text  # treść jest już w pliku; parametr zachowuje kształt portu

    def run(self, from_line: int = 1) -> None:
        self._cmd().mode(self._lc().MODE_AUTO)
        self._wait()
        self._cmd().auto(self._lc().AUTO_RUN, from_line)

    def pause(self) -> None:
        self._cmd().auto(self._lc().AUTO_PAUSE)

    def resume(self) -> None:
        self._cmd().auto(self._lc().AUTO_RESUME)

    def stop(self) -> None:
        self._cmd().abort()
        self._wait()

    def set_override(self, feed: float | None = None, rapid: float | None = None,
                     spindle: float | None = None) -> None:
        cmd = self._cmd()
        if feed is not None:
            cmd.feedrate(feed)
        if rapid is not None:
            cmd.rapidrate(rapid)
        if spindle is not None:
            cmd.spindleoverride(spindle)

    def spindle(self, speed: float, direction: int) -> None:
        cmd = self._cmd()
        cmd.mode(self._lc().MODE_MDI)
        self._wait()
        code = {1: "M3", -1: "M4", 0: "M5"}[direction]
        cmd.mdi(f"S{speed:g} {code}")

    def jog(self, axis: str, speed: float) -> None:
        cmd = self._cmd()
        cmd.mode(self._lc().MODE_MANUAL)
        self._wait()
        if speed == 0.0:
            cmd.jog(self._lc().JOG_STOP, False, self._joint(axis))
            return
        cmd.jog(self._lc().JOG_CONTINUOUS, False, self._joint(axis), speed)

    def jog_increment(self, axis: str, speed: float, distance: float) -> None:
        cmd = self._cmd()
        cmd.mode(self._lc().MODE_MANUAL)
        self._wait()
        cmd.jog(self._lc().JOG_INCREMENT, False, self._joint(axis), speed, distance)

    def jog_stop(self, axis: str | None) -> None:
        cmd = self._cmd()
        if axis is None:
            for name in self.snapshot().axis_names:
                cmd.jog(self._lc().JOG_STOP, False, self._joint(name))
            return
        cmd.jog(self._lc().JOG_STOP, False, self._joint(axis))

    def set_work_offset(self, name: str, values: dict[str, float]) -> None:
        raise Conflict("ustawienie offsetu w LinuxCNC idzie przez MDI (G10 L2); "
                       "użyj machine.mdi albo offset.set z generacją G10")

    # ---- pomocnicze --------------------------------------------------------
    def _joint(self, axis: str) -> int:
        """Numer jointa z nazwy osi; lista osi pochodzi z migawki (``stat.axis_mask``)."""
        names = list(self.snapshot().axis_names)
        letter = axis.upper()
        if letter not in names:
            raise SafetyRefused(f"nieznana oś {axis!r}", details={"axes": names})
        return names.index(letter)

    def close(self) -> None:
        self._command = None


def available() -> bool:
    """Czy moduł LinuxCNC jest importowalny (bez uruchamiania maszyny)."""
    try:
        importlib.import_module("linuxcnc")
    except ImportError:
        return False
    return True


__all__ = ["LinuxCNCBackend", "available"]
