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

import dataclasses
import importlib
import time
from pathlib import Path
from typing import Any

from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert.cnc.model import AXIS_LETTERS, MachineSnapshot, Mode

from ..errors import BackendUnavailable, Conflict, InvalidRequest, SafetyRefused

_MODE = {Mode.MANUAL: "MODE_MANUAL", Mode.AUTO: "MODE_AUTO", Mode.MDI: "MODE_MDI"}
# Numer P układu w G10 L2.
_WORK_P = {"G54": 1, "G55": 2, "G56": 3, "G57": 4, "G58": 5, "G59": 6,
           "G59.1": 7, "G59.2": 8, "G59.3": 9}


# Kanał błędów LinuxCNC oddaje komunikat raz, a migawki czytają też usługi i pętla stanu.
ERROR_RETENTION_S = 10.0


class LinuxCNCBackend:
    """``MachinePort`` na ``linuxcnc.command``/``linuxcnc.stat``."""

    name = "linuxcnc"
    # Interpreter LinuxCNC wykonuje podprogramy o<...> call (makra M6, lrt_probe).
    capabilities = frozenset({"subroutines"})

    def __init__(self, module: Any = None, reader: LinuxCNCReader | None = None,
                 timeout: float = 2.0):
        self._module = module
        self._timeout = timeout
        self._command: Any = None
        # Czytnik sam tworzy `linuxcnc.stat()`; nazwy osi bierze z `stat.axis_mask`.
        self.reader = reader or LinuxCNCReader(module=module)
        # Wiek migawki liczymy tym samym zegarem, którym czytnik ją stempluje.
        self._clock = getattr(self.reader, "_clock", time.monotonic)
        self._errors: list[tuple[float, str]] = []

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
            snap = self.reader.read()
        except Exception as exc:
            raise BackendUnavailable(f"odczyt stanu LinuxCNC nie powiódł się: {exc}") from exc
        now = self._clock()
        fresh = set(snap.errors)
        self._errors = [e for e in self._errors
                        if now - e[0] < ERROR_RETENTION_S and e[1] not in fresh]
        self._errors += [(now, text) for text in dict.fromkeys(snap.errors)]
        return dataclasses.replace(snap, errors=tuple(text for _, text in self._errors))

    # ---- polecenia ---------------------------------------------------------
    def estop(self) -> None:
        self._cmd().state(self._lc().STATE_ESTOP)

    def estop_reset(self) -> None:
        self._cmd().state(self._lc().STATE_ESTOP_RESET)

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
        """LinuxCNC bazuje jointy w trybie MANUAL bez teleop; portal startuje całą grupą."""
        joint = -1 if axis is None else self._joints_of(axis)[0]
        cmd = self._cmd()
        cmd.mode(self._lc().MODE_MANUAL)
        self._wait()
        cmd.teleop_enable(0)
        self._wait()
        cmd.home(joint)

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
        if speed == 0.0:
            self.jog_stop(axis)
            return
        joint_mode, number = self._jog_target(axis)
        self._cmd().jog(self._lc().JOG_CONTINUOUS, joint_mode, number, speed)

    def jog_increment(self, axis: str, speed: float, distance: float) -> None:
        """Kierunek niesie znak prędkości, dystans jest dodatni (jak w ``linuxcnc.jog``)."""
        joint_mode, number = self._jog_target(axis)
        self._cmd().jog(self._lc().JOG_INCREMENT, joint_mode, number, speed, distance)

    def jog_stop(self, axis: str | None) -> None:
        """Stop idzie bezwarunkowo w obu trybach: nie zależy od stanu bazowania."""
        cmd, stop = self._cmd(), self._lc().JOG_STOP
        for name in self.snapshot().axis_names if axis is None else (axis.upper(),):
            cmd.jog(stop, False, AXIS_LETTERS.index(name))
            for joint in self._joints_of(name):
                cmd.jog(stop, True, joint)

    def set_work_offset(self, name: str, values: dict[str, float]) -> None:
        if name not in _WORK_P:
            raise InvalidRequest(f"nieznany układ {name}", details={"known": sorted(_WORK_P)})
        snap = self.snapshot()
        if snap.task_state.value != "on":
            raise SafetyRefused("offset wymaga włączonego zasilania",
                                details={"task_state": snap.task_state.value})
        if snap.interp_state.value != "idle":
            raise Conflict("offset: maszyna wykonuje ruch albo program",
                           details={"interp_state": snap.interp_state.value})
        unknown = sorted({a.upper() for a in values} - set(snap.axis_names))
        if unknown:
            raise InvalidRequest(f"maszyna nie ma osi {unknown}",
                                 details={"axes": list(snap.axis_names)})
        if values:
            words = " ".join(f"{a.upper()}{v:.6f}" for a, v in values.items())
            self.mdi(f"G10 L2 P{_WORK_P[name]} {words}")

    # ---- pomocnicze --------------------------------------------------------
    def _joints_of(self, axis: str) -> tuple[int, ...]:
        """Jointy osi z konfiguracji; oś i joint to co innego na maszynie z portalem."""
        names = list(self.snapshot().axis_names)
        letter = axis.upper()
        if letter not in names:
            raise SafetyRefused(f"nieznana oś {axis!r}", details={"axes": names})
        joints = self.reader.joint_map(names)
        if len(names) > 1 and all(joints[name] == joints[letter] for name in names):
            raise Conflict("INI bez [JOINT_n]AXIS: nie wiadomo, które jointy należą do osi",
                           details={"axis": letter})
        return joints[letter]

    def _jog_target(self, axis: str) -> tuple[bool, int]:
        """Tryb i numer dla ``jog``: po bazowaniu oś (teleop), przed bazowaniem joint.

        Przed bazowaniem jeden joint portalu rozjechałby bramę, więc taki jog jest odrzucany.
        """
        joints = self._joints_of(axis)
        snap = self.snapshot()
        homed = snap.all_homed
        if not homed and len(joints) != 1:
            raise SafetyRefused(f"jog osi portalowej {axis.upper()} wymaga bazowania",
                                details={"joints": list(joints)})
        # Odświeżanie jogu co 100 ms: zmiana trybu w ruchu to odmowa i komunikat LinuxCNC.
        cmd, lc = self._cmd(), self._lc()
        if snap.mode is not Mode.MANUAL:
            cmd.mode(lc.MODE_MANUAL)
            self._wait()
        stat = self.reader.stat
        stat.poll()
        if stat.motion_mode != (lc.TRAJ_MODE_TELEOP if homed else lc.TRAJ_MODE_FREE):
            cmd.teleop_enable(1 if homed else 0)
            self._wait()
        return (False, AXIS_LETTERS.index(axis.upper())) if homed else (True, joints[0])

    def active_ini(self) -> Path:
        self.snapshot()
        return Path(self.reader.stat.ini_filename).resolve()

    def active_tool_table(self) -> Path | None:
        """``[EMCIO]TOOL_TABLE`` działającej konfiguracji (ścieżka względem katalogu INI)."""
        path = self.active_ini()
        name = self._lc().ini(str(path)).find("EMCIO", "TOOL_TABLE")
        return (path.parent / name).resolve() if name else None

    def reload_tools(self) -> None:
        self._cmd().load_tool_table()
        self._wait()

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
