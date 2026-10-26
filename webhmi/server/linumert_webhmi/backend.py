"""Backendy bramy web: polecenia i stan maszyny (atrapa albo LinuxCNC).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

``MachineBackend`` to jedyny punkt styku bramy z maszyną. Dwie implementacje:
``FakeBackend`` (atrapa ``linumert.cnc.FakeMachine`` z zegarem ściennym, testy i PoC bez
LinuxCNC) oraz ``LinuxCNCBackend`` (``linuxcnc.command`` + ``LinuxCNCReader``, moduł
wstrzykiwany, więc mapowanie poleceń testuje się bez LinuxCNC).

Bezpieczeństwo (CLAUDE.md §6): brama nigdy nie zwalnia E-STOP. Wystawia ``estop`` (odbiera
zezwolenie) i ``power_on`` dopiero po resecie wykonanym poza bramą (zatrzask HAL, D35/D37).
Każdy błąd polecenia to ``CommandError`` z komunikatem po polsku.
NIEZWERYFIKOWANE NA SPRZĘCIE; ``LinuxCNCBackend`` niezweryfikowany na LinuxCNC 2.9 RIP.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

from linumert.cnc import FakeMachine, MachineSnapshot, Mode
from linumert.cnc.linuxcnc_reader import LinuxCNCReader


class CommandError(Exception):
    """Polecenie odrzucone przez maszynę lub bramę; ``str(error)`` trafia do operatora."""


class MachineBackend(Protocol):
    def snapshot(self) -> MachineSnapshot: ...
    def estop(self) -> None: ...
    def power_on(self) -> None: ...
    def power_off(self) -> None: ...
    def set_mode(self, mode: Mode) -> None: ...
    def home(self, axis: str | None) -> None: ...
    def mdi(self, text: str) -> None: ...
    def run(self, from_line: int) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def set_override(self, feed: float | None, rapid: float | None,
                     spindle: float | None) -> None: ...
    def jog(self, axis: str, speed: float) -> None: ...
    def jog_stop(self, axis: str | None) -> None: ...
    def tick(self) -> None: ...


class FakeBackend:
    """Atrapa napędzana zegarem ściennym; ``tick`` przesuwa czas o rzeczywiste ``dt``."""

    def __init__(self, machine: FakeMachine | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self.machine = machine or FakeMachine(rapid_speed=200.0)
        self._clock = clock
        self._last = clock()

    def tick(self) -> None:
        now = self._clock()
        self.machine.advance(max(now - self._last, 0.0))
        self._last = now

    def _need(self, ok: bool) -> None:
        if not ok:
            errors = self.machine.snapshot().errors
            self.machine.clear_errors()
            raise CommandError(errors[-1] if errors else "polecenie odrzucone")

    def snapshot(self) -> MachineSnapshot:
        return self.machine.snapshot()

    def estop(self) -> None:
        self.machine.estop()

    def power_on(self) -> None:
        self._need(self.machine.power_on())

    def power_off(self) -> None:
        self._need(self.machine.power_off())

    def set_mode(self, mode: Mode) -> None:
        self._need(self.machine.set_mode(mode))

    def home(self, axis: str | None) -> None:
        self._need(self.machine.home((axis,) if axis else None))

    def mdi(self, text: str) -> None:
        self._need(self.machine.mdi(text))

    def run(self, from_line: int) -> None:
        self._need(self.machine.run(from_line))

    def pause(self) -> None:
        self._need(self.machine.pause())

    def resume(self) -> None:
        self._need(self.machine.resume())

    def stop(self) -> None:
        self.machine.stop()

    def set_override(self, feed: float | None, rapid: float | None,
                     spindle: float | None) -> None:
        self.machine.set_override(feed=feed, rapid=rapid, spindle=spindle)

    def jog(self, axis: str, speed: float) -> None:
        self._need(self.machine.jog(axis, speed))

    def jog_stop(self, axis: str | None) -> None:
        self.machine.jog_stop(axis)


class LinuxCNCBackend:
    """Polecenia przez ``linuxcnc.command``; odczyt przez ``LinuxCNCReader`` (tylko odczyt)."""

    WAIT_TIMEOUT_S = 2.0

    def __init__(self, module: Any = None, reader: LinuxCNCReader | None = None,
                 command: Any = None):
        self._module = module
        self._reader = reader or LinuxCNCReader(module=module)
        self._command = command
        self._last: MachineSnapshot | None = None

    def _lc(self) -> Any:
        if self._module is None:
            self._module = self._reader._linuxcnc()
        return self._module

    def _cmd(self) -> Any:
        if self._command is None:
            self._command = self._lc().command()
        return self._command

    def _recent(self) -> MachineSnapshot:
        """Ostatnia migawka z wątku odpytującego. ``read()`` opróżnia kanał błędów LinuxCNC,
        więc polecenia go nie wołają, żeby nie zabierać operatorowi komunikatów."""
        return self._last if self._last is not None else self.snapshot()

    def _joint_axes(self) -> tuple[str, ...]:
        return self._recent().axis_names

    def _joint_index(self, axis: str) -> int:
        names = self._joint_axes()
        if axis.upper() not in names:
            raise CommandError(f"nieznana oś {axis!r}")
        return names.index(axis.upper())

    def _wait(self, cmd: Any) -> None:
        result = cmd.wait_complete(self.WAIT_TIMEOUT_S)
        if result == -1:
            raise CommandError("LinuxCNC nie potwierdził polecenia w 2 s")
        if result == getattr(self._lc(), "RCS_ERROR", object()):
            raise CommandError("LinuxCNC odrzucił polecenie (RCS_ERROR)")

    def tick(self) -> None:  # stan LinuxCNC płynie sam
        return None

    def snapshot(self) -> MachineSnapshot:
        self._last = self._reader.read()
        return self._last

    def estop(self) -> None:
        self._cmd().state(self._lc().STATE_ESTOP)

    def power_on(self) -> None:
        lc, cmd = self._lc(), self._cmd()
        if self._recent().task_state.value not in ("estop_reset", "off"):
            raise CommandError("zasilanie: najpierw reset E-STOP (zatrzask sprzętowy)")
        cmd.state(lc.STATE_ON)

    def power_off(self) -> None:
        self._cmd().state(self._lc().STATE_OFF)

    def set_mode(self, mode: Mode) -> None:
        lc, cmd = self._lc(), self._cmd()
        cmd.mode({Mode.MANUAL: lc.MODE_MANUAL, Mode.MDI: lc.MODE_MDI,
                  Mode.AUTO: lc.MODE_AUTO}[mode])
        self._wait(cmd)

    def home(self, axis: str | None) -> None:
        names = self._joint_axes()
        if axis and axis.upper() not in names:
            raise CommandError(f"nieznana oś {axis!r}")
        targets = (names.index(axis.upper()),) if axis else tuple(range(len(names)))
        cmd = self._cmd()
        cmd.mode(self._lc().MODE_MANUAL)
        self._wait(cmd)
        for joint in targets:
            cmd.home(joint)

    def mdi(self, text: str) -> None:
        lc, cmd = self._lc(), self._cmd()
        cmd.mode(lc.MODE_MDI)
        self._wait(cmd)
        cmd.mdi(text)

    def run(self, from_line: int) -> None:
        lc, cmd = self._lc(), self._cmd()
        cmd.mode(lc.MODE_AUTO)
        self._wait(cmd)
        cmd.auto(lc.AUTO_RUN, from_line)

    def pause(self) -> None:
        self._cmd().auto(self._lc().AUTO_PAUSE)

    def resume(self) -> None:
        self._cmd().auto(self._lc().AUTO_RESUME)

    def stop(self) -> None:
        self._cmd().abort()

    def set_override(self, feed: float | None, rapid: float | None,
                     spindle: float | None) -> None:
        cmd = self._cmd()
        if feed is not None:
            cmd.feedrate(feed)
        if rapid is not None:
            cmd.rapidrate(rapid)
        if spindle is not None:
            cmd.spindleoverride(spindle)

    def jog(self, axis: str, speed: float) -> None:
        lc, cmd = self._lc(), self._cmd()
        if self._recent().mode is not Mode.MANUAL:
            raise CommandError("jog: wymagany tryb MANUAL")
        # Jog przegubu (jjogmode=True), nie osi: nie wymaga trybu teleop. Zakładamy kinematykę
        # tożsamościową (i-ta oś = i-ty przegub), jak czytnik; mm/s -> mm/min dla LinuxCNC.
        joint = self._joint_index(axis)
        cmd.teleop_enable(0)
        cmd.jog(lc.JOG_CONTINUOUS, True, joint, speed * 60.0)

    def jog_stop(self, axis: str | None) -> None:
        lc, cmd = self._lc(), self._cmd()
        names = self._joint_axes()
        for name in (axis.upper(),) if axis else names:
            if name in names:
                cmd.jog(lc.JOG_STOP, True, names.index(name))
