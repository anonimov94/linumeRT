"""Narzędzia dla symulacji i ekranu: baza narzędzi (SQLite) ↔ tool.tbl ↔ bryły `Cutter`.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

Ścieżki z INI (CLAUDE.md §9): `[LINUMERT]TOOL_DB` (domyślnie `linumert_tools.db` obok INI),
`[LINUMERT]TOOL_SEED` (YAML z przykładowymi narzędziami do pierwszego uruchomienia),
`[EMCIO]TOOL_TABLE`. Baza jest źródłem typu i geometrii; tool.tbl (Z, D) dostaje LinuxCNC.
Średnica w tool.tbl = D + korekcja średnicy (`d_wear`, ±1 mm).
"""

from __future__ import annotations

import configparser
from pathlib import Path

import yaml

from linumert.tools.db import Tool, ToolDB

from .cutter import Cutter, make_cutter


def read_ini(path: str | Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None, inline_comment_prefixes=None,
                                   comment_prefixes=("#", ";"))
    cp.optionxform = str  # klucze INI LinuxCNC są wielkimi literami
    try:
        cp.read(path, encoding="utf-8")
    except configparser.Error:
        pass
    return cp


def ini_value(ini: configparser.ConfigParser, section: str, key: str,
              default: str | None = None) -> str | None:
    try:
        return ini.get(section, key).strip()
    except (configparser.Error, KeyError):
        return default


def _units(value: str) -> str:
    units = {"mm": "mm", "metric": "mm", "inch": "inch", "in": "inch"}
    try:
        return units[value.strip().lower()]
    except (KeyError, AttributeError):
        raise ValueError(
            f"Jednostki tabeli narzędzi: {value!r}; oczekiwano mm albo inch") from None


def table_units(ini_path: str | Path) -> str:
    """Machine units from INI; the database remains in mm. Model-Author: Codex."""
    return _units(ini_value(read_ini(ini_path), "TRAJ", "LINEAR_UNITS", "mm"))


def _rel(ini_path: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else ini_path.parent / p


def tool_paths(ini_path: str | Path) -> tuple[Path, Path, Path | None]:
    """(baza narzędzi, tool.tbl, plik startowy YAML albo None)."""
    ini_path = Path(ini_path).resolve()
    ini = read_ini(ini_path)
    db = _rel(ini_path, ini_value(ini, "LINUMERT", "TOOL_DB", "linumert_tools.db"))
    tbl = _rel(ini_path, ini_value(ini, "EMCIO", "TOOL_TABLE", "tool.tbl"))
    seed = ini_value(ini, "LINUMERT", "TOOL_SEED")
    return db, tbl, (_rel(ini_path, seed) if seed else None)


def seed_tools(path: Path) -> list[Tool]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out = []
    for t in data.get("tools", []):
        params = {k: float(v) for k, v in (t.get("params") or {}).items()}
        d = params.get("d")
        wear = params.get("d_wear", 0.0)
        out.append(Tool(number=int(t["number"]), pocket=int(t.get("pocket", t["number"])),
                        type=t.get("type"), description=str(t.get("description", "")),
                        params=params, offsets={"Z": float(t.get("length", 0.0))},
                        diameter=(d + wear) if d is not None else t.get("diameter")))
    return out


def open_db(ini_path: str | Path) -> tuple[ToolDB, Path]:
    """Otwiera bazę; pusta baza dostaje narzędzia z TOOL_SEED albo z tool.tbl."""
    db_path, tbl, seed = tool_paths(ini_path)
    units = table_units(ini_path)
    db = ToolDB(db_path)
    if not db.tools():
        if seed is not None and seed.is_file():
            db._apply(seed_tools(seed), "seed")  # noqa: SLF001 - import wsadowy (całość albo nic)
            db.export_tbl(tbl, units=units)
        elif tbl.is_file():
            db.import_tbl_file(tbl, units=units)
    return db, tbl


def save_tool(db: ToolDB, tool: Tool, tbl: Path, *, units: str = "mm") -> None:
    """Dodaje/zmienia narzędzie w mm i zapisuje tool.tbl w `units` (D = d + korekcja)."""
    units = _units(units)
    d = tool.params.get("d")
    if d is not None:
        tool.diameter = d + tool.params.get("d_wear", 0.0)
    if db.get(tool.number) is None:
        db.add(tool)
    else:
        db.update(tool)
    db.export_tbl(tbl, units=units)


def cutters(db_tools: dict[int, Tool], table: list[tuple[int, float, float]]) -> dict[int, Cutter]:
    """Bryły narzędzi: `table` = [(T, Z, D)] z LinuxCNC (stat.tool_table), geometria z bazy."""
    out = {}
    for number, z, d in table:
        if number <= 0:
            continue
        tool = db_tools.get(number)
        kind = tool.type if tool is not None else None
        params = dict(tool.params) if tool is not None else {}
        if tool is not None and "d" not in params and tool.diameter:
            params["d"] = tool.diameter
        base_d = params.get("d", d) if params else d
        out[number] = make_cutter(number, z, base_d or d or 1.0, kind, params)
    return out

