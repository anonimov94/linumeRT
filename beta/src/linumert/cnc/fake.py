"""Atrapa maszyny CNC z wirtualnym zegarem do testow bez LinuxCNC.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Zakres: ESTOP/zasilanie, bazowanie, tryby MANUAL/MDI/AUTO, ruch liniowy G0/G1 z override,
G4, G53, G54..G59.3, G90/G91, wrzeciono M3/M4/M5, M6 (bez tabeli narzedzi), M0/M2/M30,
programowe limity osi. Jednostki: mm, posuw F w mm/min, predkosci wewnetrznie w mm/s.
Pozycja rzeczywista rowna sie zadanej (bez bledu nadazania); dynamike daje dopiero Plant.
Czas plynie tylko przez ``advance`` / ``run_until_idle``, wiec testy sa deterministyczne.
Atrapa NIE jest wzorcem zachowania LinuxCNC: to uproszczony model do testow logiki rdzenia.
"""

from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field

from .model import AXIS_LETTERS, AxisSnapshot, InterpState, MachineSnapshot, Mode, TaskState

WORK_OFFSET_NAMES = ("G54", "G55", "G56", "G57", "G58", "G59", "G59.1", "G59.2", "G59.3")
_WORK_CODES = {54.0: 0, 55.0: 1, 56.0: 2, 57.0: 3, 58.0: 4, 59.0: 5, 59.1: 6, 59.2: 7, 59.3: 8}
_NOOP_GCODES = {17.0, 21.0, 40.0, 49.0, 80.0, 94.0}
_NOOP_MCODES = {1, 7, 8, 9}
_WORD = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
_COMMENT = re.compile(r"\([^)]*\)|;.*")
_EPS = 1e-12


@dataclass
class _Segment:
    kind: str  # "move" | "home" | "dwell"
    target: dict[str, float] = field(default_factory=dict)
    speed: float = 0.0  # mm/s przed override
    rapid: bool = False
    left: float = 0.0  # dwell: pozostaly czas [s]


class FakeMachine:
    def __init__(
        self,
        axes: tuple[str, ...] = ("X", "Y", "Z"),
        limits: dict[str, tuple[float, float]] | None = None,
        rapid_speed: float = 200.0,
        homing_speed: float = 20.0,
        default_feed: float = 600.0,
        require_homing: bool = True,
        start: dict[str, float] | None = None,
    ):
        names = tuple(a.upper() for a in axes)
        bad = [a for a in names if a not in AXIS_LETTERS]
        if bad or len(set(names)) != len(names):
            raise ValueError(f"niepoprawne osie: {axes!r}")
        self.axis_names = names
        self.time = 0.0
        self.task_state = TaskState.ESTOP
        self.mode = Mode.MANUAL
        self.rapid_speed = rapid_speed
        self.homing_speed = homing_speed
        self.require_homing = require_homing
        self.feed_override = 1.0
        self.rapid_override = 1.0
        self.spindle_override = 1.0
        self._pos = dict.fromkeys(names, 0.0)
        self._pos.update({k.upper(): v for k, v in (start or {}).items()})
        self._homed: set[str] = set()
        self._limits = {a: (-1000.0, 1000.0) for a in names}
        self._limits.update({k.upper(): v for k, v in (limits or {}).items()})
        self._feed = default_feed
        self._absolute = True
        self._motion = "G0"
        self._work = 0
        self._offsets = {i: dict.fromkeys(names, 0.0) for i in range(len(WORK_OFFSET_NAMES))}
        self._spindle_dir = 0
        self._spindle_speed = 0.0
        self._tool = 0
        self._next_tool = 0
        self._queue: deque[_Segment] = deque()
        self._program: list[str] = []
        self._program_name = ""
        self._pc = 0
        self._running = False
        self._paused = False
        self._ending = False
        self._line = 0
        self._errors: list[str] = []
        self._jog: dict[str, float] = {}  # os -> predkosc [mm/s] ze znakiem

    # ---- zegar i migawka -------------------------------------------------
    def clock(self) -> float:
        return self.time

    def snapshot(self) -> MachineSnapshot:
        axes = tuple(
            AxisSnapshot(
                name=a,
                position=self._pos[a],
                commanded=self._pos[a],
                homed=a in self._homed,
                soft_min=self._limits[a][0],
                soft_max=self._limits[a][1],
            )
            for a in self.axis_names
        )
        if self._paused:
            interp = InterpState.PAUSED
        elif self._queue and self._queue[0].kind == "dwell":
            interp = InterpState.WAITING
        elif self._queue or self._running:
            interp = InterpState.READING
        else:
            interp = InterpState.IDLE
        distance = "G90" if self._absolute else "G91"
        mcode = {1: "M3", -1: "M4", 0: "M5"}[self._spindle_dir]
        return MachineSnapshot(
            timestamp=self.time,
            task_state=self.task_state,
            mode=self.mode,
            interp_state=interp,
            axes=axes,
            current_line=self._line,
            program_file=self._program_name,
            feed_override=self.feed_override,
            rapid_override=self.rapid_override,
            spindle_override=self.spindle_override,
            spindle_speed=self._spindle_speed,
            spindle_direction=self._spindle_dir,
            tool_number=self._tool,
            work_offset_name=WORK_OFFSET_NAMES[self._work],
            work_offset=dict(self._offsets[self._work]),
            active_gcodes=(self._motion, "G17", distance, "G21", WORK_OFFSET_NAMES[self._work]),
            active_mcodes=(mcode,),
            errors=tuple(self._errors),
        )

    def clear_errors(self) -> None:
        self._errors.clear()

    # ---- stan zasilania i tryby -----------------------------------------
    def estop(self) -> None:
        self.task_state = TaskState.ESTOP
        self._stop_motion()
        self._homed.clear()  # uproszczenie: po E-stop trzeba bazowac ponownie
        self._spindle_dir = 0

    def estop_reset(self) -> bool:
        if self.task_state is not TaskState.ESTOP:
            return self._fail("reset E-stop: maszyna nie jest w E-stop")
        self.task_state = TaskState.ESTOP_RESET
        return True

    def power_on(self) -> bool:
        if self.task_state not in (TaskState.ESTOP_RESET, TaskState.OFF):
            return self._fail("zasilanie: wymagany reset E-stop")
        self.task_state = TaskState.ON
        return True

    def power_off(self) -> bool:
        if self.task_state is not TaskState.ON:
            return self._fail("wylaczenie: maszyna nie jest wlaczona")
        self.task_state = TaskState.OFF
        self._stop_motion()
        self._homed.clear()
        return True

    def set_mode(self, mode: Mode) -> bool:
        if not self._require_on("zmiana trybu"):
            return False
        if self._busy():
            return self._fail("zmiana trybu podczas ruchu lub programu")
        if mode is not Mode.MANUAL and not self._homing_ok():
            return self._fail("nie wszystkie osie zbazowane")
        self.mode = mode
        return True

    # ---- polecenia ---------------------------------------------------------
    def home(self, axes: tuple[str, ...] | None = None) -> bool:
        if not self._require_on("bazowanie"):
            return False
        if self.mode is not Mode.MANUAL or self._busy():
            return self._fail("bazowanie: wymagany tryb MANUAL bez ruchu")
        names = tuple(a.upper() for a in axes) if axes else self.axis_names
        unknown = [a for a in names if a not in self._pos]
        if unknown:
            return self._fail(f"bazowanie: nieznane osie {unknown}")
        self._queue.append(_Segment("home", dict.fromkeys(names, 0.0), self.homing_speed))
        return True

    def mdi(self, text: str) -> bool:
        if not self._require_on("MDI"):
            return False
        if self.mode is not Mode.MDI or self._busy():
            return self._fail("MDI: wymagany tryb MDI bez ruchu")
        self._line = 0
        ok = self._execute(text)
        self._pump()
        return ok

    def load_program(self, lines: list[str], name: str = "program.ngc") -> bool:
        if self._busy():
            return self._fail("wczytanie programu podczas pracy")
        self._program = list(lines)
        self._program_name = name
        self._pc = 0
        self._line = 0
        return True

    def run(self, from_line: int = 1) -> bool:
        if not self._require_on("start programu"):
            return False
        if self.mode is not Mode.AUTO or self._busy() or not self._program:
            return self._fail("start programu: wymagany tryb AUTO i wczytany program")
        self._pc = max(from_line - 1, 0)
        self._running = True
        self._paused = False
        self._pump()
        return True

    def pause(self) -> bool:
        if not self._running:
            return self._fail("pauza: program nie dziala")
        self._paused = True
        return True

    def resume(self) -> bool:
        if not self._paused:
            return self._fail("wznowienie: program nie jest wstrzymany")
        self._paused = False
        self._pump()
        return True

    def stop(self) -> None:
        self._stop_motion()

    def set_override(
        self, feed: float | None = None, rapid: float | None = None, spindle: float | None = None
    ) -> None:
        if feed is not None:
            self.feed_override = min(max(feed, 0.0), 2.0)
        if rapid is not None:
            self.rapid_override = min(max(rapid, 0.0), 1.0)
        if spindle is not None:
            self.spindle_override = min(max(spindle, 0.0), 2.0)

    def jog(self, axis: str, speed: float) -> bool:
        """Ciagly jog osi (MANUAL, bez ruchu programu); ``speed`` w mm/s ze znakiem."""
        if not self._require_on("jog"):
            return False
        name = axis.upper()
        if name not in self._pos:
            return self._fail(f"jog: nieznana os {axis!r}")
        if self.mode is not Mode.MANUAL or self._busy():
            return self._fail("jog: wymagany tryb MANUAL bez ruchu")
        self._jog[name] = speed
        return True

    def jog_stop(self, axis: str | None = None) -> None:
        if axis is None:
            self._jog.clear()
        else:
            self._jog.pop(axis.upper(), None)

    def set_work_offset(self, name: str, **axes: float) -> None:
        index = WORK_OFFSET_NAMES.index(name)
        for axis, value in axes.items():
            self._offsets[index][axis.upper()] = value

    # ---- czas ----------------------------------------------------------------
    def advance(self, dt: float) -> None:
        remaining = max(dt, 0.0)
        self.time += remaining
        for name, speed in self._jog.items():
            low, high = self._limits[name]
            self._pos[name] = min(max(self._pos[name] + speed * remaining, low), high)
        self._pump()
        while remaining > _EPS and self._queue and not self._paused:
            remaining -= self._step(self._queue[0], remaining)
            self._pump()

    def run_until_idle(self, max_time: float = 3600.0, step: float = 0.05) -> float:
        """Przesuwa zegar do konca ruchu/programu; zwraca uplyniety czas wirtualny."""
        start = self.time
        while self._busy() and not self._paused:
            if self.time - start >= max_time:
                raise TimeoutError("atrapa nie zakonczyla ruchu w limicie czasu")
            self.advance(step)
        return self.time - start

    # ---- wnetrze -----------------------------------------------------------
    def _fail(self, message: str) -> bool:
        self._errors.append(message)
        return False

    def _require_on(self, what: str) -> bool:
        if self.task_state is not TaskState.ON:
            return self._fail(f"{what}: maszyna nie jest wlaczona")
        return True

    def _homing_ok(self) -> bool:
        return not self.require_homing or self._homed >= set(self.axis_names)

    def _busy(self) -> bool:
        return bool(self._queue) or self._running

    def _stop_motion(self) -> None:
        self._jog.clear()
        self._queue.clear()
        self._running = False
        self._paused = False
        self._ending = False
        self._line = 0

    def _abort(self, message: str) -> bool:
        self._stop_motion()
        return self._fail(message)

    def _pump(self) -> None:
        """Wykonuje kolejne linie programu AUTO, dopoki nie powstanie ruch lub postoj."""
        while self._running and not self._paused and not self._queue:
            if self._ending or self._pc >= len(self._program):
                self._stop_motion()
                return
            self._line = self._pc + 1
            text = self._program[self._pc]
            self._pc += 1
            self._execute(text)

    def _step(self, seg: _Segment, remaining: float) -> float:
        if seg.kind == "dwell":
            used = min(seg.left, remaining)
            seg.left -= used
            if seg.left <= _EPS:
                self._queue.popleft()
            return used
        delta = {a: v - self._pos[a] for a, v in seg.target.items()}
        dist = math.sqrt(sum(d * d for d in delta.values()))
        scale = 1.0
        if seg.kind == "move":
            scale = self.rapid_override if seg.rapid else self.feed_override
        speed = seg.speed * scale
        if dist <= _EPS:
            self._finish(seg)
            return 0.0
        if speed <= 0.0:
            return remaining  # override 0 %: stoi w miejscu
        needed = dist / speed
        used = min(needed, remaining)
        if used >= needed - _EPS:
            self._pos.update(seg.target)
            self._finish(seg)
            return needed
        ratio = used / needed
        for axis, d in delta.items():
            self._pos[axis] += d * ratio
        return used

    def _finish(self, seg: _Segment) -> None:
        self._queue.popleft()
        if seg.kind == "home":
            self._homed.update(seg.target)

    def _execute(self, text: str) -> bool:
        words = _WORD.findall(_COMMENT.sub("", text.upper()))
        gcodes: list[float] = []
        mcodes: list[int] = []
        values: dict[str, float] = {}
        for letter, number in words:
            value = float(number)
            if letter == "G":
                gcodes.append(round(value, 1))
            elif letter == "M":
                mcodes.append(int(value))
            elif letter != "N":
                values[letter] = value
        if "F" in values:
            self._feed = values["F"]
        if "S" in values:
            self._spindle_speed = values["S"]
        if "T" in values:
            self._next_tool = int(values["T"])
        for code in mcodes:
            if not self._apply_mcode(code):
                return False
        one_shot = False
        for code in gcodes:
            if code in (0.0, 1.0):
                self._motion = "G0" if code == 0.0 else "G1"
            elif code == 90.0 or code == 91.0:
                self._absolute = code == 90.0
            elif code == 53.0:
                one_shot = True
            elif code in _WORK_CODES:
                self._work = _WORK_CODES[code]
            elif code != 4.0 and code not in _NOOP_GCODES:
                return self._abort(f"nieobslugiwany G{code:g}")
        if 4.0 in gcodes:
            if "P" not in values or values["P"] < 0:
                return self._abort("G4 wymaga P >= 0")
            self._queue.append(_Segment("dwell", left=values["P"]))
        axes = {a: values[a] for a in self.axis_names if a in values}
        return self._queue_move(axes, one_shot) if axes else True

    def _apply_mcode(self, code: int) -> bool:
        if code in (3, 4, 5):
            self._spindle_dir = {3: 1, 4: -1, 5: 0}[code]
        elif code == 6:
            self._tool = self._next_tool
        elif code == 0:
            if self._running:
                self._paused = True
        elif code in (2, 30):
            if self._running:
                self._ending = True  # koniec programu po dokonczeniu ruchu z tej linii
        elif code not in _NOOP_MCODES:
            return self._abort(f"nieobslugiwany M{code}")
        return True

    def _queue_move(self, axes: dict[str, float], one_shot: bool) -> bool:
        target: dict[str, float] = {}
        for axis, value in axes.items():
            if one_shot:
                goal = value
            elif self._absolute:
                goal = value + self._offsets[self._work][axis]
            else:
                goal = self._pos[axis] + value
            low, high = self._limits[axis]
            if not low <= goal <= high:
                return self._abort(f"limit programowy osi {axis}")
            target[axis] = goal
        rapid = self._motion == "G0"
        if not rapid and self._feed <= 0:
            return self._abort("brak posuwu F")
        speed = self.rapid_speed if rapid else self._feed / 60.0
        self._queue.append(_Segment("move", target, speed, rapid))
        return True
