"""Format programu dialogowego `.lnx` (JSON z wersją schematu, D12; sesja 039).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 039

    {"schema_version": 1,
     "name": "pokrywa",
     "units": "mm",
     "comment": "...",                 (opcjonalnie)
     "stock": {"shape": "BOX", "x": 120, "y": 80, "z": 30, ...},   (opcjonalnie, stock.py)
     "steps": [{"generator": "pocket_rect", "version": 1, "params": {...},
                "enabled": true, "comment": "..."}]}

`lnx_schema.json` jest generowany z modelu (`write_schema()`); test pilnuje zgodności pliku.
Zapis atomowy (plik tymczasowy + zamiana), kodowanie UTF-8, klucze w stałej kolejności, więc
zapisany plik zmienia się tylko przy zmianie treści (diff w Git).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .stock import Stock

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("lnx_schema.json")


class LnxError(ValueError):
    """Plik .lnx niepoprawny; `issues` to komunikaty po polsku ze ścieżką pola (P-5012)."""

    def __init__(self, issues: list[str]):
        super().__init__("; ".join(issues))
        self.issues = issues

    def alarms(self) -> list[Any]:
        """Błędy jako alarmy P-5012 katalogu (do listy błędów w ekranie)."""
        from linumert.generators.base import Issue

        return [Issue("P-5012", {"detail": text}) for text in self.issues]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(_Strict):
    """Krok programu: generator w konkretnej wersji i jego parametry."""

    generator: str = Field(min_length=1, max_length=40)
    version: int = Field(ge=1)
    params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    comment: str | None = Field(default=None, max_length=200)


class LnxProgram(_Strict):
    schema_version: Literal[1] = SCHEMA_VERSION
    name: str = Field(min_length=1, max_length=80)
    units: Literal["mm", "inch"] = "mm"
    comment: str | None = Field(default=None, max_length=500)
    stock: Stock | None = None
    steps: list[Step] = Field(default_factory=list)


def json_schema() -> dict[str, Any]:
    schema = LnxProgram.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "linumeRT .lnx (program dialogowy)"
    return schema


def write_schema(path: Path = SCHEMA_PATH) -> Path:
    path.write_text(json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def _issues(exc: ValidationError) -> list[str]:
    out = []
    for error in exc.errors():
        where = ".".join(str(p) for p in error["loc"])
        message = str(error["msg"]).removeprefix("Value error, ")
        out.append(f"{where}: {message}" if where else message)
    return out


def parse_lnx(data: Any) -> LnxProgram:
    """Dane JSON → program (LnxError z listą błędów)."""
    if isinstance(data, dict) and data.get("schema_version") not in (None, SCHEMA_VERSION):
        raise LnxError([f"schema_version: {data.get('schema_version')!r} — ta wersja linumeRT "
                        f"czyta wersję {SCHEMA_VERSION}"])
    try:
        return LnxProgram.model_validate(data)
    except ValidationError as exc:
        raise LnxError(_issues(exc)) from None


def load_lnx(path: Path | str) -> LnxProgram:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LnxError([f"{path}: brak pliku"]) from None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LnxError([f"{path}: to nie jest poprawny plik JSON ({exc})"]) from None
    return parse_lnx(data)


def dump_lnx(program: LnxProgram) -> str:
    data = program.model_dump(mode="json", exclude_none=True)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def atomic_write(path: Path | str, text: str) -> Path:
    """Zapis tekstu przez plik tymczasowy w tym samym katalogu i zamianę (bez połówek pliku)."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return path


def save_lnx(program: LnxProgram, path: Path | str) -> Path:
    return atomic_write(path, dump_lnx(program))
