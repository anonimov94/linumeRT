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
NIEZWERYFIKOWANE NA SPRZĘCIE. Celowany odbiór LinuxCNC sim: test_webhmi_live_linuxcnc.py.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any, Protocol

from linumert.cnc import FakeMachine, MachineSnapshot, Mode
from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert.cnc.model import AXIS_LETTERS


class CommandError(Exception):
    """Polecenie odrzucone przez maszynę lub bramę; ``str(error)`` trafia do operatora."""


def _increment_target(snap: MachineSnapshot, axis: str, speed: float,
                      distance: float, scale: float = 1.0) -> float:
    if (snap.task_state.value != "on" or snap.mode is not Mode.MANUAL
            or snap.interp_state.value != "idle" or not snap.all_homed):
        raise CommandError("jog przyrostowy: wymagane ON, MANUAL, bez ruchu i bazowanie")
    if (not math.isfinite(speed) or not 0 < abs(speed) <= 50
            or not math.isfinite(distance) or not 0 < distance <= 1):
        raise CommandError("jog przyrostowy: niepoprawna prędkość lub droga")
    row = next((a for a in snap.axes if a.name == axis.upper()), None)
    if row is None:
        raise CommandError("jog przyrostowy: nieznana oś")
    target = row.position + math.copysign(distance * scale, speed)
    if row.limit_hit or not row.soft_min <= target <= row.soft_max:
        raise CommandError("jog przyrostowy: limit osi")
    return target


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
    def jog_increment(self, axis: str, speed: float, distance: float) -> None: ...
    def jog_stop(self, axis: str | None) -> None: ...
    def tick(self) -> None: ...


class FakeBackend:
    """Atrapa napędzana zegarem ściennym; ``tick`` przesuwa czas o rzeczywiste ``dt``."""

    def __init__(self, machine: FakeMachine | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self.machine = machine or FakeMachine(rapid_speed=200.0)
        self._clock = clock
        self._last = clock()
        self._increments: dict[str, tuple[float, float]] = {}

    def tick(self) -> None:
        now = self._clock()
        dt = max(now - self._last, 0.0)
        positions = {a.name: a.position for a in self.machine.snapshot().axes}
        for axis, (target, speed) in list(self._increments.items()):
            remaining = (target - positions[axis]) * math.copysign(1, speed)
            if remaining <= 1e-10:
                self.jog_stop(axis)
            elif dt > 0:
                self._need(self.machine.jog(axis, math.copysign(
                    min(abs(speed), remaining / dt), speed)))
        self.machine.advance(dt)
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

    def jog_increment(self, axis: str, speed: float, distance: float) -> None:
        snap = self.machine.snapshot()
        name = axis.upper()
        target = _increment_target(snap, name, speed, distance)
        self.jog(name, speed)
        self._increments[name] = (target, speed)

    def jog_stop(self, axis: str | None) -> None:
        if axis is None:
            self._increments.clear()
        else:
            self._increments.pop(axis.upper(), None)
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
        self._linear_units: float | None = None

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

    def _joints_of(self, axis: str) -> tuple[int, ...]:
        """Jointy osi z mapy czytnika; na portalu numer osi to nie numer jointa."""
        names = self._joint_axes()
        letter = axis.upper()
        if letter not in names:
            raise CommandError(f"nieznana oś {axis!r}")
        joints = self._reader.joint_map(names)
        if len(names) > 1 and all(joints[name] == joints[letter] for name in names):
            raise CommandError("INI bez [JOINT_n]AXIS: nie wiadomo, które jointy należą do osi")
        return joints[letter]

    def _jog_target(self, axis: str) -> tuple[bool, int]:
        """(tryb jointa, numer) dla ``cmd.jog``. Jeden joint portalu rozjechałby bramę, więc
        oś portalową jogujemy tylko po bazowaniu, w teleop, numerem osi z dziewięciu liter."""
        joints = self._joints_of(axis)
        if len(joints) == 1:
            return True, joints[0]
        if not self._recent().all_homed:
            raise CommandError(f"jog osi portalowej {axis.upper()} wymaga bazowania")
        return False, AXIS_LETTERS.index(axis.upper())

    def _send_jog(self, joint_mode: bool, jog_type: Any, number: int, *values: float) -> None:
        cmd = self._cmd()
        cmd.teleop_enable(0 if joint_mode else 1)
        if not joint_mode:
            self._wait(cmd)
        cmd.jog(jog_type, joint_mode, number, *values)

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
        # LinuxCNC reports machine units per mm; G20/G21 does not change these.
        units = getattr(self._reader._stat, "linear_units", None)
        self._linear_units = float(units) if units is not None else None
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
        # -1 = cała maszyna wg HOME_SEQUENCE; joint portalu startuje całą swoją grupę.
        joint = self._joints_of(axis)[0] if axis else -1
        cmd = self._cmd()
        cmd.mode(self._lc().MODE_MANUAL)
        self._wait(cmd)
        cmd.teleop_enable(0)
        self._wait(cmd)
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
        if self._recent().mode is not Mode.MANUAL:
            raise CommandError("jog: wymagany tryb MANUAL")
        # Jog przegubu (jjogmode=True): nie wymaga trybu teleop; wyjątek to oś portalu.
        # command.jog takes machine units/SECOND (AXIS get_jog_speed), not per minute.
        joint_mode, number = self._jog_target(axis)
        velocity = speed
        if axis.upper() not in "ABC":
            units = self._linear_units
            if units is None or not math.isfinite(units) or units <= 0:
                raise CommandError("jog: brak poprawnej skali jednostek maszyny")
            velocity *= units  # API mm/s -> native units/s; angular axes use degrees/s.
        self._send_jog(joint_mode, self._lc().JOG_CONTINUOUS, number, velocity)

    def jog_stop(self, axis: str | None) -> None:
        lc, cmd = self._lc(), self._cmd()
        names = self._joint_axes()
        joints = self._reader.joint_map(names)  # stop bez warunków: także przy niepełnej mapie
        for name in (axis.upper(),) if axis else names:
            if name in names:
                if len(joints[name]) > 1:
                    cmd.jog(lc.JOG_STOP, False, AXIS_LETTERS.index(name))
                for joint in joints[name]:
                    cmd.jog(lc.JOG_STOP, True, joint)

    def jog_increment(self, axis: str, speed: float, distance: float) -> None:
        if self._recent().mode is not Mode.MANUAL:
            raise CommandError("jog: wymagany tryb MANUAL")
        joint_mode, number = self._jog_target(axis)
        scale = 1.0
        if axis.upper() not in "ABC":
            units = self._linear_units
            if units is None or not math.isfinite(units) or units <= 0:
                raise CommandError("jog: brak poprawnej skali jednostek maszyny")
            scale = units
        _increment_target(self._recent(), axis, speed, distance, scale)
        self._send_jog(joint_mode, self._lc().JOG_INCREMENT, number, speed * scale,
                       distance * scale)
