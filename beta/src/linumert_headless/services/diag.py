"""Usługa diagnostyki: doctor, dziennik zdarzeń, dekodowanie CiA 402.

SPDX-License-Identifier: GPL-2.0-or-later

Diagnostyka jest tylko do odczytu: nie zmienia konfiguracji i nie uruchamia HAL.
``diag.doctor`` inwentaryzuje środowisko (Python, moduły, polecenia w PATH, PREEMPT_RT)
i wprost oznacza, czego **nie** sprawdził — obecność modułu nie jest dowodem działania.
"""

from __future__ import annotations

from pathlib import Path

from linumert.alarms.catalog import CatalogError
from linumert.diag.cia402 import decode_statusword, describe_error_code
from linumert.diag.doctor import format_report, inspect_environment
from linumert.diag.journal import Journal

from ..errors import InvalidRequest
from ..schema import (
    Cia402Out,
    Cia402Request,
    DiagDoctor,
    DiagJournalOut,
    DiagJournalRequest,
)
from .paths import ProjectPaths


class DiagService:
    """Operacje domeny ``diag``."""

    domain = "diag"

    def __init__(self, paths: ProjectPaths, journal_path: Path | None = None):
        self.paths = paths
        self.journal_path = journal_path or (paths.state / "linumert.log")
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._journal = Journal(self.journal_path)

    def close(self) -> None:
        self._journal.close()

    # ---- doktor ------------------------------------------------------------
    def doctor(self) -> DiagDoctor:
        report = inspect_environment()
        checks = report.get("checks", [])
        ok = all(c.get("status") != "error" for c in checks)
        try:
            text = format_report(report)
        except (CatalogError, KeyError, TypeError):
            text = "\n".join(f"{c.get('name')}: {c.get('status')} — {c.get('detail')}"
                             for c in checks)
        return DiagDoctor(ok=ok, entries=checks, report=text)

    # ---- dziennik ----------------------------------------------------------
    def log(self, level: str, message: str) -> None:
        """Zapis zdarzenia z usługi (GUI nie pisze do dziennika bezpośrednio)."""
        self._journal.add(level, message)

    def journal(self, request: DiagJournalRequest) -> DiagJournalOut:
        # Wpis dziennika to krotka (czas, poziom, komunikat) — kolejność jak w SQLite.
        entries = self._journal.matching(level=request.kind)[: request.limit]
        return DiagJournalOut(
            entries=[{"time": e[0], "level": e[1], "message": e[2]} for e in entries],
            warning=self._journal.warning,
        )

    def journal_csv(self, request: DiagJournalRequest) -> str:
        return self._journal.csv(level=request.kind)

    # ---- CiA 402 -----------------------------------------------------------
    def cia402(self, request: Cia402Request) -> Cia402Out:
        if not 0 <= request.statusword <= 0xFFFF:
            raise InvalidRequest("statusword poza zakresem 0–65535")
        info = decode_statusword(request.statusword)
        return Cia402Out(
            state=str(getattr(info, "state", "")),
            description=str(getattr(info, "description", "") or getattr(info, "state", "")),
            flags={k: bool(v) for k, v in vars(info).items()
                   if isinstance(v, bool)} if hasattr(info, "__dict__") else {},
            error_text=describe_error_code(request.error_code) if request.error_code else "",
        )


__all__ = ["DiagService"]
