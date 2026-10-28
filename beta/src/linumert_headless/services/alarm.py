"""Usługa alarmów: katalog, aktywne, historia, potwierdzanie.

SPDX-License-Identifier: GPL-2.0-or-later

Alarmy pochodzą z katalogu YAML (``linumert.alarms.catalog``) i mają komunikaty PL/EN.
GUI dostaje **kod + sformatowany komunikat**, więc nie trzyma własnych tłumaczeń.
Potwierdzenie (ack) nie kasuje przyczyny: E-STOP i interlocki pozostają w HAL/sprzęcie
(CLAUDE.md §6) — to tylko obsługa operatorska.
"""

from __future__ import annotations

from linumert.alarms.catalog import CatalogError, load_catalog
from linumert.alarms.manager import Alarm, AlarmManager

from ..errors import InvalidRequest, NotFound
from ..schema import AlarmAckRequest, AlarmList, AlarmOut, AlarmRaiseRequest, Ok


def _out(alarm: Alarm, manager: AlarmManager, lang: str = "pl") -> AlarmOut:
    try:
        message = manager.message(alarm, lang)
    except (CatalogError, KeyError):
        message = alarm.code
    return AlarmOut(
        id=alarm.id, code=alarm.code, level=str(getattr(alarm, "level", "")),
        message=message, raised=float(getattr(alarm, "raised", 0.0) or 0.0),
        acknowledged=bool(getattr(alarm, "acknowledged", False)),
        params=dict(getattr(alarm, "params", {}) or {}),
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

    def codes(self) -> dict:
        """Katalog kodów — GUI buduje z niego listę i opisy."""
        if self.catalog is None:
            return {"codes": []}
        return {"codes": [
            {"code": d.code, "level": getattr(d, "level", ""),
             "message_pl": getattr(d, "message_pl", ""), "message_en": getattr(d, "message_en", "")}
            for d in getattr(self.catalog, "definitions", {}).values()
        ]}

    def raise_alarm(self, request: AlarmRaiseRequest) -> AlarmOut:
        try:
            alarm = self.manager.raise_alarm(request.code, **request.params)
        except (CatalogError, KeyError) as exc:
            known = sorted(getattr(self.catalog, "definitions", {}) or {})[:40]
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
