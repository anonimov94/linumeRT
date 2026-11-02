"""Niezmienny model migawki stanu maszyny (bez zaleznosci od LinuxCNC).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Migawka opisuje stan w jednej chwili: tworzy ja czytnik (``linuxcnc_reader``) albo
atrapa (``fake``). Pozycje sa w ukladzie maszynowym (jak ``stat.actual_position``),
w jednostkach maszyny. Rdzen i ekran korzystaja z tego samego modelu przez zwykly import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

AXIS_LETTERS = ("X", "Y", "Z", "A", "B", "C", "U", "V", "W")

# Domyslna swiezosc migawki w sekundach; po tym czasie dane uznajemy za nieaktualne.
DEFAULT_MAX_AGE = 0.5


class TaskState(Enum):
    ESTOP = "estop"
    ESTOP_RESET = "estop_reset"
    OFF = "off"
    ON = "on"


class Mode(Enum):
    MANUAL = "manual"
    AUTO = "auto"
    MDI = "mdi"


class InterpState(Enum):
    IDLE = "idle"
    READING = "reading"
    PAUSED = "paused"
    WAITING = "waiting"


@dataclass(frozen=True)
class AxisSnapshot:
    """Stan jednej osi. ``commanded`` to pozycja zadana, ``position`` rzeczywista."""

    name: str
    position: float = 0.0
    commanded: float = 0.0
    homed: bool = False
    soft_min: float = float("-inf")
    soft_max: float = float("inf")
    limit_hit: bool = False  # aktywny krancowkowy limit twardy (dowolny kierunek)

    @property
    def following_error(self) -> float:
        return self.commanded - self.position


@dataclass(frozen=True)
class MachineSnapshot:
    """Stan maszyny w chwili ``timestamp`` (sekundy zegara zrodla migawki)."""

    timestamp: float
    task_state: TaskState = TaskState.ESTOP
    mode: Mode = Mode.MANUAL
    interp_state: InterpState = InterpState.IDLE
    axes: tuple[AxisSnapshot, ...] = ()
    current_line: int = 0
    program_file: str = ""
    feed_override: float = 1.0  # 1.0 = 100 %
    rapid_override: float = 1.0
    spindle_override: float = 1.0
    spindle_speed: float = 0.0  # obr/min (zadane)
    spindle_direction: int = 0  # -1, 0, 1
    tool_number: int = 0
    tool_offset: dict[str, float] = field(default_factory=dict)
    work_offset_name: str = "G54"
    work_offset: dict[str, float] = field(default_factory=dict)
    active_gcodes: tuple[str, ...] = ()
    active_mcodes: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def axis(self, name: str) -> AxisSnapshot:
        for item in self.axes:
            if item.name == name.upper():
                return item
        raise KeyError(f"brak osi {name!r}")

    @property
    def axis_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.axes)

    @property
    def positions(self) -> dict[str, float]:
        return {item.name: item.position for item in self.axes}

    @property
    def all_homed(self) -> bool:
        return bool(self.axes) and all(item.homed for item in self.axes)

    @property
    def spindle_running(self) -> bool:
        return self.spindle_direction != 0

    def work_position(self, name: str) -> float:
        """Pozycja w biezacym ukladzie roboczym (G54..G59.3).

        Uwzglednia tylko przesuniecie ukladu roboczego; G92 i dlugosc narzedzia
        nie sa tu odejmowane.
        """
        axis = self.axis(name)
        return axis.position - self.work_offset.get(axis.name, 0.0)

    def age(self, now: float) -> float:
        return now - self.timestamp

    def is_fresh(self, now: float, max_age: float = DEFAULT_MAX_AGE) -> bool:
        return 0.0 <= self.age(now) <= max_age
