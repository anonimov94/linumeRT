"""Usługa narzędzi: baza SQLite, eksport/import ``tool.tbl``, zużycie i historia.

SPDX-License-Identifier: GPL-2.0-or-later

Baza narzędzi (``linumert.tools.db.ToolDB``) jest wspólna dla LinuxCNC i Plant: GUI czyta
i pisze przez tę usługę, a ``tool.tbl`` dla LinuxCNC powstaje z tej samej bazy
(``linumert.tools.tbl``). Jedno źródło prawdy — brak rozjazdu między ekranem a maszyną.
"""

from __future__ import annotations

from pathlib import Path

from linumert.tools.db import Tool, ToolDB, ToolDBError
from linumert.tools.tbl import ToolTableError

from ..errors import Conflict, InvalidRequest, NotFound
from ..schema import (
    Ok,
    ToolList,
    ToolNumber,
    ToolOut,
    ToolTblOut,
    ToolTblRequest,
    ToolUpsertRequest,
    ToolWearRequest,
)
from .paths import ProjectPaths


def _out(tool: Tool) -> ToolOut:
    return ToolOut(
        number=tool.number, pocket=tool.pocket, type=tool.type,
        description=tool.description, holder=tool.holder, diameter=tool.diameter,
        params=dict(tool.params), offsets=dict(tool.offsets),
        life_min=tool.life_min, used_min=tool.used_min,
    )


class ToolService:
    """Operacje domeny ``tool``."""

    domain = "tool"

    def __init__(self, paths: ProjectPaths, db_path: Path | None = None):
        self.paths = paths
        self.db_path = db_path or paths.tools_db
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: ToolDB | None = None

    @property
    def db(self) -> ToolDB:
        if self._db is None:
            self._db = ToolDB(self.db_path)
        return self._db

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    # ---- odczyt ------------------------------------------------------------
    def list(self) -> ToolList:
        return ToolList(tools=[_out(t) for t in self.db.tools()], path=str(self.db_path))

    def get(self, request: ToolNumber) -> ToolOut:
        tool = self.db.get(request.number)
        if tool is None:
            raise NotFound(f"brak narzędzia T{request.number}",
                           details={"number": request.number})
        return _out(tool)

    def history(self, request: ToolNumber) -> dict:
        return {"entries": self.db.history(request.number or None, limit=200)}

    # ---- zapis -------------------------------------------------------------
    def upsert(self, request: ToolUpsertRequest) -> Ok:
        tool = Tool(
            number=request.number, pocket=request.pocket, type=request.type,
            description=request.description, holder=request.holder,
            diameter=request.diameter, params=dict(request.params),
            offsets=dict(request.offsets), life_min=request.life_min,
        )
        issues = tool.validate()
        if issues:
            raise InvalidRequest(
                f"narzędzie T{request.number} ma błędy",
                details={"issues": [issue.message() for issue in issues],
                         "fields": sorted({issue.field or "" for issue in issues})})
        exists = self.db.get(request.number) is not None
        try:
            if exists:
                self.db.update(tool, source="api")
            else:
                self.db.add(tool, source="api")
        except ToolDBError as exc:
            raise Conflict(f"zapis narzędzia T{request.number} nie powiódł się: {exc}") from exc
        return Ok(message=f"{'zaktualizowano' if exists else 'dodano'} T{request.number}",
                  details={"number": request.number})

    def delete(self, request: ToolNumber) -> Ok:
        if self.db.get(request.number) is None:
            raise NotFound(f"brak narzędzia T{request.number}")
        self.db.remove(request.number, source="api")
        return Ok(message=f"usunięto T{request.number}")

    def set_wear(self, request: ToolWearRequest) -> Ok:
        tool = self.db.get(request.number)
        if tool is None:
            raise NotFound(f"brak narzędzia T{request.number}")
        offsets = dict(tool.offsets)
        offsets[request.axis] = round(offsets.get(request.axis, 0.0) + request.value, 6)
        tool.offsets = offsets
        self.db.update(tool, source="api")
        return Ok(message=f"korekcja {request.axis} narzędzia T{request.number}: "
                          f"{offsets[request.axis]:g} mm",
                  details={"offsets": offsets})

    # ---- wymiana z LinuxCNC ------------------------------------------------
    def export_tbl(self, request: ToolTblRequest) -> ToolTblOut:
        target = Path(request.path) if request.path else self.paths.sim / "tool.tbl"
        try:
            written = self.db.export_tbl(target, units=request.units)
        except (ToolDBError, ToolTableError) as exc:
            raise Conflict(f"eksport tool.tbl nie powiódł się: {exc}") from exc
        return ToolTblOut(path=str(written), text=Path(written).read_text(encoding="utf-8"),
                          units=request.units)

    def import_tbl(self, text: str, units: str = "mm") -> Ok:
        try:
            numbers = self.db.import_tbl(text, source="api", units=units)
        except (ToolDBError, ToolTableError) as exc:
            raise InvalidRequest(f"import tool.tbl nie powiódł się: {exc}") from exc
        return Ok(message=f"zaimportowano {len(numbers)} narzędzi",
                  details={"numbers": numbers})


__all__ = ["ToolService"]
