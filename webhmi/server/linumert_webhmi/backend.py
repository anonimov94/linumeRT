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
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from linumert.cnc import FakeMachine, MachineSnapshot, Mode
from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert.cnc.model import AXIS_LETTERS

from .schema import PROGRAM_NAME

MAX_PROGRAMS = 200
DEFAULT_PROGRAMS = Path("~/linuxcnc/nc_files")  # CLAUDE.md §9; INI ma pierwszeństwo


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


def _ready_for_setup(snap: MachineSnapshot, what: str) -> None:
    """Zero detalu i wczytanie programu: ON, bez ruchu, wszystkie osie zbazowane."""
    if snap.task_state.value != "on":
        raise CommandError(f"{what}: maszyna nie jest w stanie ON")
    if snap.interp_state.value != "idle":
        raise CommandError(f"{what}: wymagany brak ruchu (interpreter IDLE)")
    if not snap.all_homed:
        raise CommandError(f"{what}: wymagane bazowanie wszystkich osi")


def _zero_axes(snap: MachineSnapshot, axis: str | None) -> tuple[str, ...]:
    names = snap.axis_names
    if axis is None:
        return tuple(n for n in names if n in "XYZ")
    if axis.upper() not in names:
        raise CommandError(f"zero detalu: nieznana oś {axis!r}")
    return (axis.upper(),)


def list_programs(directory: Path | None) -> tuple[str, ...]:
    """Pliki programów w katalogu (bez podkatalogów), posortowane; brak katalogu = pusto."""
    if directory is None:
        return ()
    try:
        names = sorted(e.name for e in os.scandir(directory)
                       if e.is_file() and PROGRAM_NAME.fullmatch(e.name))
    except OSError:
        return ()
    return tuple(names[:MAX_PROGRAMS])


def program_path(directory: Path | None, name: str) -> Path:
    """Ścieżka programu z katalogu programów; nazwa spoza listy jest odrzucana."""
    if directory is None:
        raise CommandError("program: brak katalogu programów ([DISPLAY]PROGRAM_PREFIX)")
    if name not in list_programs(directory):
        raise CommandError(f"program: brak pliku {name!r} w katalogu programów")
    return Path(directory) / name


class MachineBackend(Protocol):
    def snapshot(self) -> MachineSnapshot: ...
    def estop(self) -> None: ...
    def estop_reset(self) -> None: ...
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
    def work_zero(self, axis: str | None) -> None: ...
    def programs(self) -> tuple[str, ...]: ...
    def open_program(self, name: str) -> None: ...
    def tick(self) -> None: ...


class ReportBackend:
    """Offline observations only: no controller module, command transport or virtual motion."""

    read_only = True

    def __init__(self, report):
        self.report = report

    def snapshot(self):
        return MachineSnapshot(timestamp=time.monotonic())

    def tick(self):
        pass

    def programs(self):
        return ()

    def jog_stop(self, axis=None):
        pass  # no command transport exists in this backend


class FakeBackend:
    """Atrapa napędzana zegarem ściennym; ``tick`` przesuwa czas o rzeczywiste ``dt``."""

    def __init__(self, machine: FakeMachine | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 programs_dir: Path | None = None):
        self.machine = machine or FakeMachine(rapid_speed=200.0)
        self.programs_dir = programs_dir
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
        # Jak kanał błędów LinuxCNC: każdy komunikat trafia do jednej migawki.
        snap = self.machine.snapshot()
        self.machine.clear_errors()
        return snap

    def estop(self) -> None:
        self.machine.estop()

    def estop_reset(self) -> None:
        self.machine.estop_reset()

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

    def work_zero(self, axis: str | None) -> None:
        snap = self.machine.snapshot()
        _ready_for_setup(snap, "zero detalu")
        if snap.mode is not Mode.MANUAL:
            raise CommandError("zero detalu: wymagany tryb MANUAL")
        positions = {a.name: a.position for a in snap.axes}
        self.machine.set_work_offset(snap.work_offset_name, **{
            name: positions[name] for name in _zero_axes(snap, axis)})

    def programs(self) -> tuple[str, ...]:
        return list_programs(self.programs_dir)

    def open_program(self, name: str) -> None:
        _ready_for_setup(self.machine.snapshot(), "wczytanie programu")
        path = program_path(self.programs_dir, name)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise CommandError(f"program: nie można odczytać {name!r}") from error
        self._need(self.machine.load_program(lines, str(path)))


class LinuxCNCBackend:
    """Polecenia przez ``linuxcnc.command``; odczyt przez ``LinuxCNCReader`` (tylko odczyt)."""

    WAIT_TIMEOUT_S = 2.0

    def __init__(self, module: Any = None, reader: LinuxCNCReader | None = None,
                 command: Any = None, programs_dir: Path | None = None):
        self._programs_dir = programs_dir
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
        """(tryb jointa, numer) dla ``cmd.jog``. Po bazowaniu zawsze teleop, numerem osi z
        dziewięciu liter: LinuxCNC 2.9 odmawia jogu jointa z ``HOME_SEQUENCE`` < 0 („home_sequence
        is synchronized”, każdy joint konfiguracji Plant). Przed bazowaniem tylko oś z jednym
        jointem; jeden joint portalu rozjechałby bramę."""
        joints = self._joints_of(axis)
        if self._recent().all_homed:
            return False, AXIS_LETTERS.index(axis.upper())
        if len(joints) == 1:
            return True, joints[0]
        raise CommandError(f"jog osi portalowej {axis.upper()} wymaga bazowania")

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

    def binding_state(self, pins=()) -> dict:
        """Last NML pose plus subsequent tooldata read; no extra error-channel poll."""
        stat = self._reader._stat
        names = ("linear_units", "inpos", "current_vel", "tool_offset", "g5x_index",
                 "g5x_offset", "g92_offset", "rotation_xy")
        out = {name: getattr(stat, name, None) for name in names}
        out["ini"] = getattr(stat, "ini_filename", None)
        out["motion_line"] = getattr(stat, "motion_line", None)
        out["task_done"] = getattr(stat, "state", None) == getattr(self._lc(), "RCS_DONE", object())
        joints = getattr(stat, "joint", None)
        out["joint_following_errors"] = None if joints is None else {
            "units": "mm" if getattr(stat, "linear_units", None) == 1 else None,
            "values": [joint.get("ferror_current") for joint in joints]}
        table = getattr(stat, "tool_table", None)
        out["tool_table"] = None if table is None else [
            {"id": row.id, "offsets": [getattr(row, a + "offset") for a in "xyzabcuvw"],
             **{name: getattr(row, name) for name in
                ("diameter", "frontangle", "backangle", "orientation")}}
            for row in table if row.id >= 0]
        if pins:
            try:
                import hal

                out["hal"] = {name: hal.get_value(name) for name in pins}
            except (ImportError, RuntimeError, ValueError):
                out["hal"] = None
        return out

    def estop(self) -> None:
        self._cmd().state(self._lc().STATE_ESTOP)

    def estop_reset(self) -> None:
        # Tylko po potwierdzeniu w HAL (podwójny Reset, D37): zatrzask E-STOP w HAL nadal
        # odrzuci reset, gdy obwód safety albo łańcuch HMI jest otwarty.
        self._cmd().state(self._lc().STATE_ESTOP_RESET)

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

    def confirm_job_state(self, *, paused=False):
        """Require a newly echoed command serial before using NML as a Start receipt.

        Reassert AUTO while idle, or PAUSE while already paused. Neither enables
        the machine or resumes motion. Error messages remain for the reader.
        """
        lc, cmd, stat = self._lc(), self._cmd(), self._reader._stat
        if paused:
            cmd.auto(lc.AUTO_PAUSE)
        else:
            cmd.mode(lc.MODE_AUTO)
        serial = cmd.serial
        deadline = time.monotonic() + self.WAIT_TIMEOUT_S
        while time.monotonic() < deadline:
            stat.poll()
            wanted = lc.INTERP_PAUSED if paused else lc.INTERP_IDLE
            if (stat.echo_serial_number == serial and stat.task_state == lc.STATE_ON
                    and stat.task_mode == lc.MODE_AUTO and stat.interp_state == wanted):
                return
            time.sleep(.005)
        raise CommandError("Sterowanie nie potwierdziło świeżego stanu zadania w 2 s")

    def run_confirmed(self, from_line):
        self._cmd().auto(self._lc().AUTO_RUN, from_line)

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
        snap = self._recent()
        if snap.mode is Mode.AUTO and snap.interp_state.value in ("reading", "waiting", "paused"):
            # LinuxCNC cannot jog in active AUTO and rejects JOG_STOP there.
            # Program Stop is the independent abort(), sent by Gateway.
            return
        lc, cmd = self._lc(), self._cmd()
        names = self._joint_axes()
        joints = self._reader.joint_map(names)  # stop bez warunków: także przy niepełnej mapie
        for name in (axis.upper(),) if axis else names:
            if name in names:
                # Ruch po bazowaniu jest w teleop (numer osi), przed nim w jointach: stop obu.
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

    def _wait_idle(self, timeout: float) -> None:
        """Czeka, aż interpreter wróci do IDLE (po MDI); czyta stat bez kanału błędów."""
        lc, stat = self._lc(), self._reader._stat
        deadline = time.monotonic() + timeout
        while True:
            stat.poll()
            if stat.interp_state == lc.INTERP_IDLE:
                return
            if time.monotonic() >= deadline:
                raise CommandError("LinuxCNC nie zakończył polecenia MDI w 2 s")
            time.sleep(0.01)

    def work_zero(self, axis: str | None) -> None:
        """Bieżąca pozycja staje się zerem aktywnego układu detalu (G10 L20 P0)."""
        snap = self._recent()
        _ready_for_setup(snap, "zero detalu")
        if snap.mode is not Mode.MANUAL:
            raise CommandError("zero detalu: wymagany tryb MANUAL")
        words = " ".join(f"{name}0" for name in _zero_axes(snap, axis))
        lc, cmd = self._lc(), self._cmd()
        cmd.mode(lc.MODE_MDI)
        self._wait(cmd)
        try:
            cmd.mdi(f"G10 L20 P0 {words}")
            self._wait(cmd)
            self._wait_idle(self.WAIT_TIMEOUT_S)
        finally:  # operator wraca do MANUAL, w którym kliknął
            cmd.mode(lc.MODE_MANUAL)
            self._wait(cmd)

    def _program_dir(self) -> Path | None:
        if self._programs_dir is None:
            stat = self._reader._stat
            ini_file = getattr(stat, "ini_filename", "") if stat is not None else ""
            if not ini_file:
                return None  # stat jeszcze nieodczytany; kolejna próba przy następnym odczycie
            factory = getattr(self._lc(), "ini", None)
            prefix = factory(ini_file).find("DISPLAY", "PROGRAM_PREFIX") if factory else None
            base = Path(prefix).expanduser() if prefix else DEFAULT_PROGRAMS.expanduser()
            self._programs_dir = base if base.is_absolute() else (
                Path(ini_file).parent / base).resolve()
        return self._programs_dir

    def programs(self) -> tuple[str, ...]:
        return list_programs(self._program_dir())

    def open_program(self, name: str) -> None:
        _ready_for_setup(self._recent(), "wczytanie programu")
        path = program_path(self._program_dir(), name)
        lc, cmd = self._lc(), self._cmd()
        cmd.mode(lc.MODE_AUTO)
        self._wait(cmd)
        cmd.program_open(str(path))
        self._wait(cmd)
