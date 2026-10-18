"""Manager alarmow: zgloszenie, potwierdzenie, kasowanie, reset i historia w pamieci.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Niezalezny od interfejsu i od LinuxCNC. Zegar jest wstrzykiwany (testy), dostep chroni
blokada, wiec manager moze byc uzywany z kilku watkow. Sluchacze sa wolani po zwolnieniu
blokady; wyjatek sluchacza jest logowany i nie psuje stanu alarmow.

Semantyka kasowania zalezy od pola ``clear`` w katalogu:
- ``auto``  zrodlo woła ``clear``; potwierdzenie tylko oznacza alarm jako zauwazony,
- ``ack``   potwierdzenie kasuje alarm,
- ``reset`` kasuje go ``reset()``; potwierdzenie tylko oznacza alarm jako zauwazony.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .catalog import Catalog, load_catalog

log = logging.getLogger(__name__)

_LEVEL_RANK = {"warning": 1, "simulation": 1, "program": 2, "error": 3}


class AlarmState(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    CLEARED = "cleared"


@dataclass
class Alarm:
    id: int
    code: str
    params: dict[str, Any]
    raised_at: float
    state: AlarmState = AlarmState.ACTIVE
    count: int = 1  # ile razy zgloszono ten sam alarm, gdy byl aktywny
    acknowledged_at: float | None = None
    cleared_at: float | None = None
    _key: tuple = field(default=(), repr=False, compare=False)


Listener = Callable[[str, Alarm], None]


class AlarmManager:
    def __init__(
        self,
        catalog: Catalog | None = None,
        clock: Callable[[], float] = time.monotonic,
        history_limit: int = 1000,
    ):
        self.catalog = catalog or load_catalog()
        self._clock = clock
        self._lock = threading.RLock()
        self._next_id = 1
        self._active: dict[int, Alarm] = {}
        self._history: deque[Alarm] = deque(maxlen=history_limit)
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener) -> None:
        with self._lock:
            self._listeners.append(listener)

    def raise_alarm(self, code: str, **params: Any) -> Alarm:
        """Zglasza alarm. Identyczny (kod + parametry) aktywny alarm tylko zwieksza ``count``."""
        definition = self.catalog.get(code)
        missing = [name for name in definition.params if name not in params]
        if missing:
            raise ValueError(f"{code}: brak parametrow {missing}")
        key = (code, tuple(sorted((name, repr(value)) for name, value in params.items())))
        with self._lock:
            for alarm in self._active.values():
                if alarm._key == key:
                    alarm.count += 1
                    event, result = "repeated", self._copy(alarm)
                    break
            else:
                alarm = Alarm(self._next_id, code, dict(params), self._clock(), _key=key)
                self._next_id += 1
                self._active[alarm.id] = alarm
                event, result = "raised", self._copy(alarm)
        self._notify(event, result)
        return result

    def acknowledge(self, alarm_id: int) -> bool:
        with self._lock:
            alarm = self._active.get(alarm_id)
            if alarm is None:
                return False
            if self.catalog.get(alarm.code).clear == "ack":
                events = [self._finish(alarm)]
            else:
                if alarm.state is AlarmState.ACTIVE:
                    alarm.state = AlarmState.ACKNOWLEDGED
                    alarm.acknowledged_at = self._clock()
                events = [("acknowledged", self._copy(alarm))]
        self._notify_all(events)
        return True

    def acknowledge_all(self) -> int:
        with self._lock:
            ids = list(self._active)
        return sum(self.acknowledge(alarm_id) for alarm_id in ids)

    def clear(self, code: str | None = None, alarm_id: int | None = None) -> int:
        """Kasuje aktywne alarmy o danym kodzie albo o danym id; zwraca ich liczbe."""
        if (code is None) == (alarm_id is None):
            raise ValueError("podaj dokladnie jedno: code albo alarm_id")
        with self._lock:
            targets = [
                alarm
                for alarm in self._active.values()
                if alarm.code == code or alarm.id == alarm_id
            ]
            events = [self._finish(alarm) for alarm in targets]
        self._notify_all(events)
        return len(events)

    def reset(self) -> int:
        """Reset maszyny: kasuje alarmy z ``clear: reset``; reszta czeka na swoje zdarzenie."""
        with self._lock:
            targets = [
                alarm
                for alarm in self._active.values()
                if self.catalog.get(alarm.code).clear == "reset"
            ]
            events = [self._finish(alarm) for alarm in targets]
        self._notify_all(events)
        return len(events)

    def active(self) -> list[Alarm]:
        with self._lock:
            return [self._copy(alarm) for alarm in self._active.values()]

    def history(self, limit: int | None = None) -> list[Alarm]:
        """Skasowane alarmy, od najnowszego."""
        with self._lock:
            items = [self._copy(alarm) for alarm in reversed(self._history)]
        return items if limit is None else items[:limit]

    def worst_level(self) -> str | None:
        """Najpowazniejszy poziom wsrod aktywnych alarmow (error > program > warning)."""
        with self._lock:
            levels = [self.catalog.get(alarm.code).level for alarm in self._active.values()]
        return max(levels, key=_LEVEL_RANK.__getitem__, default=None)

    def message(self, alarm: Alarm, lang: str = "pl") -> str:
        return self.catalog.format(alarm.code, lang, **alarm.params)

    # ---- wnetrze -----------------------------------------------------------
    def _finish(self, alarm: Alarm) -> tuple[str, Alarm]:
        alarm.state = AlarmState.CLEARED
        alarm.cleared_at = self._clock()
        del self._active[alarm.id]
        self._history.append(alarm)
        return "cleared", self._copy(alarm)

    @staticmethod
    def _copy(alarm: Alarm) -> Alarm:
        return dataclasses.replace(alarm, params=dict(alarm.params))

    def _notify_all(self, events: list[tuple[str, Alarm]]) -> None:
        for event, alarm in events:
            self._notify(event, alarm)

    def _notify(self, event: str, alarm: Alarm) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event, alarm)
            except Exception:
                log.exception("sluchacz alarmow zglosil wyjatek (zdarzenie %s)", event)
