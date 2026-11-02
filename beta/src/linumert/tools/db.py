"""Baza narzędzi w SQLite — źródło prawdy (D13), z historią zmian i eksportem tool.tbl (sesja 032).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 032

- Schemat w migracjach numerowanych (`PRAGMA user_version`); nowa wersja = nowa migracja na
  końcu listy, stare bazy podnoszą się przy otwarciu.
- Każda zmiana (dodanie, edycja, usunięcie, import) trafia do `history` ze stanem przed i po,
  źródłem i czasem z wstrzykiwanego zegara (testy deterministyczne).
- `export_tbl()` zapisuje tool.tbl atomowo (plik tymczasowy + zamiana), więc LinuxCNC nigdy nie
  czyta połowy pliku; po zapisie ekran każe LinuxCNC przeładować tabelę (sesja 032, ekran).
- Import tool.tbl: nowe narzędzia bez typu (ostrzeżenie K-320 w symulacji); istniejące
  zachowują typ i geometrię, zmieniają się tylko pola z tool.tbl (gniazdo, przesunięcia, D,
  komentarz). CSV: eksport i import wszystkich pól (arkusz kalkulacyjny).
Bez I/O w czasie rzeczywistym: baza działa w procesie ekranu/rdzenia (CLAUDE.md §5).
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .tbl import INCH, MAX_POCKET, OFFSET_AXES, TblEntry, format_tbl, parse_tbl, scale_entries
from .types import TYPES, ToolIssue, finite_number, validate_geometry

MIGRATIONS: tuple[str, ...] = (
    # 1: narzędzia i historia
    """
    CREATE TABLE tools (
        number      INTEGER PRIMARY KEY CHECK (number >= 1),
        pocket      INTEGER NOT NULL UNIQUE CHECK (pocket BETWEEN 0 AND 99999),
        type        TEXT,
        description TEXT NOT NULL DEFAULT '',
        holder      TEXT NOT NULL DEFAULT '',
        stl         TEXT,
        params      TEXT NOT NULL DEFAULT '{}',
        offsets     TEXT NOT NULL DEFAULT '{}',
        diameter    REAL,
        lathe       TEXT NOT NULL DEFAULT '{}',
        life_min    REAL,
        used_min    REAL NOT NULL DEFAULT 0
    );
    CREATE TABLE history (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        time    REAL NOT NULL,
        number  INTEGER NOT NULL,
        action  TEXT NOT NULL CHECK (action IN ('add', 'update', 'remove', 'import')),
        source  TEXT NOT NULL,
        before  TEXT,
        after   TEXT
    );
    CREATE INDEX history_number ON history(number);
    """,
)

CSV_FIELDS = ("number", "pocket", "type", "description", "holder", "stl", "diameter",
              "life_min", "used_min", "params", "offsets", "lathe")


class ToolDBError(ValueError):
    """Operacja odrzucona; `issues` — błędy z kodami katalogu alarmów (P-52xx)."""

    def __init__(self, issues: list[ToolIssue]):
        super().__init__("; ".join(i.message() for i in issues))
        self.issues = issues


@dataclass
class Tool:
    number: int
    pocket: int
    type: str | None = None
    description: str = ""
    holder: str = ""
    stl: str | None = None
    params: dict[str, float] = field(default_factory=dict)   # geometria typu [mm, °]
    offsets: dict[str, float] = field(default_factory=dict)  # X…W z tool.tbl (Z = długość)
    diameter: float | None = None                            # D w tool.tbl
    lathe: dict[str, float] = field(default_factory=dict)    # I, J, Q (tokarka)
    life_min: float | None = None
    used_min: float = 0.0

    def tool_diameter(self) -> float | None:
        """Effective D for LinuxCNC: nominal d + diameter wear, or raw table D."""
        if "d" in self.params:
            return float(self.params["d"]) + float(self.params.get("d_wear", 0.0))
        return self.diameter

    def validate(self) -> list[ToolIssue]:
        issues = []
        n = self.number
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            issues.append(ToolIssue("P-5201", {"tool": n, "field": "number",
                                               "expected": "liczba całkowita >= 1"}, "number"))
        if isinstance(self.pocket, bool) or not isinstance(self.pocket, int) or \
                not 0 <= self.pocket <= MAX_POCKET:
            issues.append(ToolIssue("P-5201", {"tool": n, "field": "pocket",
                                               "expected": f"gniazdo 0…{MAX_POCKET}"}, "pocket"))
        mappings = {}
        for name in ("params", "offsets", "lathe"):
            value = getattr(self, name)
            if not isinstance(value, dict):
                issues.append(ToolIssue("P-5201", {"tool": n, "field": name,
                                                   "expected": "obiekt z nazwami pól"}, name))
                value = {}
            mappings[name] = value
        for name, value in mappings["offsets"].items():
            if name not in OFFSET_AXES:
                issues.append(ToolIssue("P-5201", {"tool": n, "field": f"offsets.{name}",
                                                   "expected": "oś X Y Z A B C U V W"}))
            if not finite_number(value):
                field_name = f"offsets.{name}"
                issues.append(ToolIssue("P-5201", {"tool": n, "field": field_name,
                                                   "expected": "skończona liczba"}, field_name))
        for name, value in mappings["lathe"].items():
            if (name not in ("I", "J", "Q") or not finite_number(value)
                    or (name == "Q" and (not 0 <= value <= 9 or value != int(value)))):
                field_name = f"lathe.{name}"
                expected = "liczba całkowita 0…9" if name == "Q" else "I/J: skończona liczba"
                issues.append(ToolIssue("P-5201", {"tool": n, "field": field_name,
                                                   "expected": expected}, field_name))
        if self.diameter is not None and (not finite_number(self.diameter) or self.diameter < 0):
            issues.append(ToolIssue("P-5201", {"tool": n, "field": "diameter",
                                               "expected": "skończona liczba >= 0"}, "diameter"))
        for name, value in (("life_min", self.life_min), ("used_min", self.used_min)):
            if name == "life_min" and value is None:
                continue
            if (not finite_number(value) or value < 0
                    or (name == "life_min" and value == 0)):
                expected = "skończona liczba > 0 minut albo brak" if name == "life_min" else \
                    "skończona liczba >= 0 minut"
                issues.append(ToolIssue("P-5201", {"tool": n, "field": name,
                                                   "expected": expected}, name))
        for text, name in ((self.description, "description"), (self.holder, "holder")):
            if "\n" in text or ";" in text:
                issues.append(ToolIssue("P-5201", {"tool": n, "field": name,
                                                   "expected": "tekst w jednej linii bez ;"},
                                        name))
        geometry = (validate_geometry(n, self.type, self.params, self.stl)
                    if isinstance(self.params, dict) else [])
        if isinstance(self.params, dict) and not geometry:
            wear = self.params.get("d_wear", 0.0)
            if wear and "d" not in self.params:
                issues.append(ToolIssue("P-5201", {"tool": n, "field": "d_wear",
                                                   "expected": "nominalna średnica d"}, "d_wear"))
            elif "d" in self.params and self.tool_diameter() <= 0:
                issues.append(ToolIssue("P-5201", {"tool": n, "field": "d_wear",
                                                   "expected": "D po korekcji > 0"}, "d_wear"))
        return issues + geometry

    def warnings(self) -> list[ToolIssue]:
        """Ostrzeżenia dla symulacji: brak typu → walec zastępczy (K-320)."""
        return [] if self.type is not None else [ToolIssue("K-320", {"tool": self.number})]

    def to_row(self) -> dict[str, Any]:
        return {"number": self.number, "pocket": self.pocket, "type": self.type,
                "description": self.description, "holder": self.holder, "stl": self.stl,
                "params": json.dumps(self.params, sort_keys=True),
                "offsets": json.dumps(self.offsets, sort_keys=True),
                "diameter": self.diameter, "lathe": json.dumps(self.lathe, sort_keys=True),
                "life_min": self.life_min, "used_min": self.used_min}

    @classmethod
    def from_row(cls, row: sqlite3.Row | dict[str, Any]) -> Tool:
        return cls(number=int(row["number"]), pocket=int(row["pocket"]), type=row["type"],
                   description=row["description"], holder=row["holder"], stl=row["stl"],
                   params=json.loads(row["params"]), offsets=json.loads(row["offsets"]),
                   diameter=row["diameter"], lathe=json.loads(row["lathe"]),
                   life_min=row["life_min"], used_min=float(row["used_min"]))

    def to_tbl(self) -> TblEntry:
        values = {k: float(v) for k, v in self.offsets.items()}
        diameter = self.tool_diameter()
        if diameter is not None:
            values["D"] = diameter
        values.update({k: float(v) for k, v in self.lathe.items() if k in ("I", "J")})
        q = self.lathe.get("Q")
        return TblEntry(self.number, self.pocket, values,
                        int(q) if q is not None else None, self.description)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


class ToolDB:
    """Baza narzędzi. `path` = plik SQLite (":memory:" w testach); `clock` = czas historii."""

    def __init__(self, path: Path | str, clock: Callable[[], float] = time.time):
        self.path = str(path)
        self.clock = clock
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> ToolDB:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- schemat -------------------------------------------------------------------------
    @property
    def schema_version(self) -> int:
        return int(self.db.execute("PRAGMA user_version").fetchone()[0])

    def _migrate(self) -> None:
        version = self.schema_version
        if version > len(MIGRATIONS):
            raise ToolDBError([ToolIssue("P-5204", {"line": 0, "detail":
                               f"baza w wersji {version} jest nowsza niż program "
                               f"({len(MIGRATIONS)})"})])
        for number in range(version, len(MIGRATIONS)):
            with self.db:
                self.db.executescript(MIGRATIONS[number])
                self.db.execute(f"PRAGMA user_version = {number + 1}")

    # ---- odczyt --------------------------------------------------------------------------
    def get(self, number: int) -> Tool | None:
        row = self.db.execute("SELECT * FROM tools WHERE number = ?", (number,)).fetchone()
        return Tool.from_row(row) if row else None

    def tools(self) -> list[Tool]:
        return [Tool.from_row(r) for r in
                self.db.execute("SELECT * FROM tools ORDER BY number").fetchall()]

    def history(self, number: int | None = None, *,
                limit: int | None = None) -> list[dict[str, Any]]:
        """Chronological entries; limit selects the most recent entries. Model-Author: Codex."""
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool)
                                  or limit < 1):
            raise ValueError("limit historii musi być dodatnią liczbą całkowitą")
        query = "SELECT * FROM history" + (" WHERE number = ?" if number is not None else "")
        args = () if number is None else (number,)
        query += " ORDER BY id" if limit is None else " ORDER BY id DESC LIMIT ?"
        rows = self.db.execute(query, args if limit is None else (*args, limit)).fetchall()
        if limit is not None:
            rows.reverse()
        return [{"time": r["time"], "number": r["number"], "action": r["action"],
                 "source": r["source"],
                 "before": json.loads(r["before"]) if r["before"] else None,
                 "after": json.loads(r["after"]) if r["after"] else None} for r in rows]

    # ---- zmiany --------------------------------------------------------------------------
    def _conflicts(self, tool: Tool, replacing: int | None) -> list[ToolIssue]:
        issues = tool.validate()
        if replacing is None and self.get(tool.number) is not None:
            issues.append(ToolIssue("P-5202", {"tool": tool.number}, "number"))
        row = self.db.execute("SELECT number FROM tools WHERE pocket = ? AND number != ?",
                              (tool.pocket, tool.number)).fetchone()
        if row is not None:
            issues.append(ToolIssue("P-5203", {"pocket": tool.pocket, "tool": row["number"]},
                                    "pocket"))
        return issues

    def _log(self, number: int, action: str, source: str, before: Tool | None,
             after: Tool | None) -> None:
        self.db.execute(
            "INSERT INTO history (time, number, action, source, before, after) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (self.clock(), number, action, source,
             json.dumps(before.to_row(), sort_keys=True) if before else None,
             json.dumps(after.to_row(), sort_keys=True) if after else None))

    def _write(self, tool: Tool) -> None:
        row = tool.to_row()
        names = ", ".join(row)
        marks = ", ".join(f":{k}" for k in row)
        self.db.execute(f"INSERT OR REPLACE INTO tools ({names}) VALUES ({marks})", row)

    def add(self, tool: Tool, source: str = "ekran") -> None:
        issues = self._conflicts(tool, None)
        if issues:
            raise ToolDBError(issues)
        with self.db:
            self._write(tool)
            self._log(tool.number, "add", source, None, tool)

    def update(self, tool: Tool, source: str = "ekran") -> None:
        before = self.get(tool.number)
        if before is None:
            raise ToolDBError([ToolIssue("P-5206", {"tool": tool.number}, "number")])
        issues = self._conflicts(tool, tool.number)
        if issues:
            raise ToolDBError(issues)
        if before == tool:
            return
        with self.db:
            self._write(tool)
            self._log(tool.number, "update", source, before, tool)

    def remove(self, number: int, source: str = "ekran") -> None:
        before = self.get(number)
        if before is None:
            raise ToolDBError([ToolIssue("P-5206", {"tool": number}, "number")])
        with self.db:
            self.db.execute("DELETE FROM tools WHERE number = ?", (number,))
            self._log(number, "remove", source, before, None)

    # ---- tool.tbl ------------------------------------------------------------------------
    def export_tbl(self, path: Path | str, units: str = "mm") -> Path:
        """Zapis tool.tbl w jednostkach maszyny (`units` = LINEAR_UNITS z INI: mm albo inch)."""
        path = Path(path)
        tools = self.tools()
        issues = [issue for tool in tools for issue in tool.validate()]
        if issues:
            raise ToolDBError(issues)
        entries = scale_entries([t.to_tbl() for t in tools], _factor(units, to_db=False))
        _atomic_write(path, format_tbl(entries))
        return path

    def _apply(self, tools: list[Tool], source: str) -> list[int]:
        """Import wielu narzędzi w jednej transakcji (całość albo nic); gniazda mogą się
        zamieniać między importowanymi narzędziami."""
        issues: list[ToolIssue] = []
        incoming = {t.number for t in tools}
        seen: dict[int, int] = {}
        for tool in tools:
            issues += tool.validate()
            if tool.pocket in seen:
                issues.append(ToolIssue("P-5203", {"pocket": tool.pocket,
                                                   "tool": seen[tool.pocket]}, "pocket"))
            seen[tool.pocket] = tool.number
            marks = ", ".join("?" * len(incoming))
            row = self.db.execute(f"SELECT number FROM tools WHERE pocket = ? AND number NOT IN "
                                  f"({marks})", (tool.pocket, *incoming)).fetchone()
            if row is not None:
                issues.append(ToolIssue("P-5203", {"pocket": tool.pocket,
                                                   "tool": row["number"]}, "pocket"))
        if issues:
            raise ToolDBError(issues)
        pending = [(self.get(t.number), t) for t in tools]
        pending = [(old, new) for old, new in pending if old != new]
        with self.db:
            for old, _ in pending:
                if old is not None:  # zwolnij gniazdo przed zapisem nowych wartości
                    self.db.execute("DELETE FROM tools WHERE number = ?", (old.number,))
            for old, new in pending:
                self._write(new)
                self._log(new.number, "import", source, old, new)
        return [new.number for _, new in pending]

    def import_tbl(self, text: str, source: str = "tool.tbl", units: str = "mm") -> list[int]:
        """Import treści tool.tbl w jednostkach maszyny (całość albo nic). Zwraca numery
        zmienionych narzędzi."""
        entries = scale_entries(parse_tbl(text), _factor(units, to_db=True))
        return self._apply([_merge(self.get(e.number), e) for e in entries], source)

    def import_tbl_file(self, path: Path | str, units: str = "mm") -> list[int]:
        path = Path(path)
        return self.import_tbl(path.read_text(encoding="utf-8"), source=path.name, units=units)

    # ---- CSV -----------------------------------------------------------------------------
    def export_csv(self) -> str:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for tool in self.tools():
            row = tool.to_row()
            writer.writerow({k: "" if row[k] is None else row[k] for k in CSV_FIELDS})
        return out.getvalue()

    def import_csv(self, text: str, source: str = "csv") -> list[int]:
        """Import CSV z `export_csv()` (dodaje albo aktualizuje; całość albo nic)."""
        tools: list[Tool] = []
        issues: list[ToolIssue] = []
        for line, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
            try:
                tools.append(Tool(
                    number=int(row["number"]), pocket=int(row["pocket"]),
                    type=row["type"] or None, description=row["description"],
                    holder=row["holder"], stl=row["stl"] or None,
                    params=json.loads(row["params"] or "{}"),
                    offsets=json.loads(row["offsets"] or "{}"),
                    diameter=float(row["diameter"]) if row["diameter"] else None,
                    lathe=json.loads(row["lathe"] or "{}"),
                    life_min=float(row["life_min"]) if row["life_min"] else None,
                    used_min=float(row["used_min"] or 0)))
            except (KeyError, ValueError, TypeError) as exc:
                issues.append(ToolIssue("P-5204", {"line": line, "detail": f"CSV: {exc}"}))
        if issues:
            raise ToolDBError(issues)
        return self._apply(tools, source)


def _factor(units: str, to_db: bool) -> float:
    if units in ("mm", "metric"):
        return 1.0
    if units in ("inch", "in"):
        return INCH if to_db else 1.0 / INCH
    raise ValueError(f"jednostki tool.tbl: {units!r} (mm albo inch)")


def _merge(old: Tool | None, entry: TblEntry) -> Tool:
    """Narzędzie po imporcie wpisu tool.tbl (zachowuje typ i geometrię istniejącego)."""
    offsets = {k: v for k, v in entry.values.items() if k in OFFSET_AXES}
    lathe = {k: v for k, v in entry.values.items() if k in ("I", "J")}
    if entry.orientation is not None:
        lathe["Q"] = float(entry.orientation)
    diameter = entry.values.get("D")
    if old is None:
        return Tool(entry.number, entry.pocket, description=entry.comment, offsets=offsets,
                    diameter=diameter, lathe=lathe)
    merged = Tool(**{**old.__dict__})
    merged.pocket = entry.pocket
    merged.offsets = offsets
    merged.lathe = lathe
    merged.description = entry.comment
    if "d" in old.params and diameter is not None:
        # D already includes wear. Preserve the correction rather than applying it twice.
        if not math.isclose(diameter, old.tool_diameter(), rel_tol=0.0, abs_tol=1e-9):
            merged.params = {**old.params, "d": diameter - old.params.get("d_wear", 0.0)}
        if old.diameter is not None:
            merged.diameter = diameter
    elif "d" not in old.params:
        merged.diameter = diameter
    return merged


__all__ = ["TYPES", "Tool", "ToolDB", "ToolDBError"]

