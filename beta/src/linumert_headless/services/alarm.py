"""Usługa alarmów: katalog, aktywne, historia, potwierdzanie.

SPDX-License-Identifier: GPL-2.0-or-later

Alarmy pochodzą z katalogu YAML (``linumert.alarms.catalog``) i mają komunikaty PL/EN.
GUI dostaje **kod + sformatowany komunikat**, więc nie trzyma własnych tłumaczeń.
Potwierdzenie (ack) nie kasuje przyczyny: E-STOP i interlocki pozostają w HAL/sprzęcie
(CLAUDE.md §6) — to tylko obsługa operatorska.
"""

from __future__ import annotations

from linumert.alarms.catalog import CatalogError, load_catalog
from linumert.alarms.manager import Alarm, AlarmManager, AlarmState

from ..errors import InvalidRequest, NotFound
from ..schema import (
    AlarmAckRequest,
    AlarmCodeOut,
    AlarmCodesOut,
    AlarmList,
    AlarmOut,
    AlarmRaiseRequest,
    Ok,
)


def _out(alarm: Alarm, manager: AlarmManager, lang: str = "pl") -> AlarmOut:
    """``Alarm`` nie ma pól ``level``/``raised``/``acknowledged``.

    Poziom siedzi w katalogu (``catalog.get(code).level``), czas w ``raised_at``,
    a stan w ``state: AlarmState``. Czytanie ich przez ``getattr`` z domyślną
    wartością cicho oddawało pusty poziom, zero i "niepotwierdzony" — GUI nie
    widziało ani powagi alarmu, ani potwierdzenia.
    """
    try:
        message = manager.message(alarm, lang)
    except (CatalogError, KeyError, ValueError):
        message = alarm.code
    try:
        level = str(manager.catalog.get(alarm.code).level)
    except (CatalogError, KeyError):
        level = ""
    state = alarm.state
    return AlarmOut(
        id=alarm.id, code=alarm.code, level=level, message=message,
        raised=float(alarm.raised_at),
        acknowledged=state is AlarmState.ACKNOWLEDGED,
        state=str(getattr(state, "value", state)),
        count=int(alarm.count),
        params=dict(alarm.params or {}),
    )


class AlarmService:
    """Operacje domeny ``alarm``."""

    domain = "alarm"

    def __init__(self, manager: AlarmManager | None = None, lang: str = "pl"):
        try:
            self.catalog = load_catalog()
        except CatalogError:
            self.catalog = None
        self.manager = manager or AlarmManager(self.catalog)
        self.lang = lang

    def list(self, limit: int = 100) -> AlarmList:
        return AlarmList(
            active=[_out(a, self.manager, self.lang) for a in self.manager.active()],
            history=[_out(a, self.manager, self.lang)
                     for a in self.manager.history(limit=limit)],
            worst_level=self.manager.worst_level(),
        )

    def codes(self) -> AlarmCodesOut:
        """Katalog kodów — GUI buduje z niego listę i opisy.

        Katalog (``linumert.alarms.catalog``) exposes ``codes()`` (krotka kodów) i
        ``get(code)`` → ``AlarmDef(code, level, clear, params, texts)``; komunikaty
        siedzą w ``texts`` pod kluczami języków, nie w polach ``message_pl/_en``.
        """
        if self.catalog is None:
            return AlarmCodesOut(codes=[])
        items = []
        for code in self.catalog.codes():
            definition = self.catalog.get(code)
            texts = dict(getattr(definition, "texts", {}) or {})
            items.append(AlarmCodeOut(
                code=definition.code,
                level=str(getattr(definition, "level", "")),
                clear=str(getattr(definition, "clear", "")),
                params=list(getattr(definition, "params", ()) or ()),
                message_pl=texts.get("pl", ""),
                message_en=texts.get("en", ""),
            ))
        return AlarmCodesOut(codes=items)

    def raise_alarm(self, request: AlarmRaiseRequest) -> AlarmOut:
        try:
            alarm = self.manager.raise_alarm(request.code, **request.params)
        except (CatalogError, KeyError) as exc:
            known = sorted(self.catalog.codes())[:40] if self.catalog is not None else []
            raise NotFound(f"nieznany kod alarmu {request.code}",
                           details={"code": request.code, "known": known,
                                    "reason": str(exc)}) from exc
        return _out(alarm, self.manager, self.lang)

    def acknowledge(self, request: AlarmAckRequest) -> Ok:
        if request.alarm_id is None:
            count = self.manager.acknowledge_all()
            return Ok(message=f"potwierdzono {count} alarmów", details={"count": count})
        if not self.manager.acknowledge(request.alarm_id):
            raise InvalidRequest(f"brak alarmu o id {request.alarm_id}",
                                 details={"alarm_id": request.alarm_id})
        return Ok(message=f"potwierdzono alarm {request.alarm_id}")

    def reset(self) -> Ok:
        count = self.manager.reset()
        return Ok(message=f"wyczyszczono {count} alarmów", details={"count": count})


__all__ = ["AlarmService"]
