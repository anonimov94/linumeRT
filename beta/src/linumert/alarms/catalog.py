"""Loader katalogu alarmow z walidacja (catalog.yaml to jedyne zrodlo kodow i tekstow).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import re
import string
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LANGUAGES = ("pl", "en")
CLEAR_MODES = ("auto", "ack", "reset")
DEFAULT_PATH = Path(__file__).with_name("catalog.yaml")

_CODE = re.compile(r"^([WEKP])-(\d{3,4})$")
_LEVELS = {"W": "warning", "E": "error", "K": "simulation", "P": "program"}


class CatalogError(ValueError):
    """Katalog jest niepoprawny; komunikat zawiera wszystkie wykryte problemy."""


@dataclass(frozen=True)
class AlarmDef:
    code: str
    level: str  # warning | error | simulation | program (z prefiksu kodu)
    clear: str  # auto | ack | reset
    params: tuple[str, ...]
    texts: dict[str, str]


def _placeholders(text: str) -> set[str] | None:
    """Nazwy pol {nazwa} w tekscie; None, gdy tekst ma pola pozycyjne lub zlozone."""
    names = set()
    for _, field, spec, conv in string.Formatter().parse(text):
        if field is None:
            continue
        if not field.isidentifier() or spec or conv:
            return None
        names.add(field)
    return names


def _build(entry: Any, index: int, problems: list[str]) -> AlarmDef | None:
    if not isinstance(entry, dict):
        problems.append(f"wpis #{index}: oczekiwano slownika")
        return None
    code = entry.get("code")
    label = code if isinstance(code, str) else f"#{index}"
    match = _CODE.match(code) if isinstance(code, str) else None
    if not match:
        problems.append(f"{label}: niepoprawny kod (oczekiwano W|E|K|P-NNN[N])")
        return None
    start = len(problems)
    clear = entry.get("clear")
    if clear not in CLEAR_MODES:
        problems.append(f"{label}: pole clear musi byc jednym z {CLEAR_MODES}")
    params = entry.get("params")
    if not isinstance(params, list) or not all(isinstance(p, str) for p in params):
        problems.append(f"{label}: pole params musi byc lista nazw")
        params = []
    texts = {}
    for lang in LANGUAGES:
        text = entry.get(lang)
        if not isinstance(text, str) or not text.strip():
            problems.append(f"{label}: brak tekstu {lang}")
            continue
        names = _placeholders(text)
        if names is None:
            problems.append(f"{label}: tekst {lang} ma niedozwolone pola formatu")
        elif names != set(params):
            problems.append(
                f"{label}: pola tekstu {lang} {sorted(names)} != params {sorted(params)}"
            )
        texts[lang] = text
    if len(problems) > start:
        return None
    return AlarmDef(code, _LEVELS[match.group(1)], clear, tuple(params), texts)


class Catalog:
    def __init__(self, definitions: list[AlarmDef]):
        self._by_code = {item.code: item for item in definitions}

    def __contains__(self, code: object) -> bool:
        return code in self._by_code

    def __iter__(self) -> Iterator[AlarmDef]:
        return iter(self._by_code.values())

    def __len__(self) -> int:
        return len(self._by_code)

    def codes(self) -> tuple[str, ...]:
        return tuple(self._by_code)

    def get(self, code: str) -> AlarmDef:
        try:
            return self._by_code[code]
        except KeyError:
            raise KeyError(f"nieznany kod alarmu {code!r}") from None

    def format(self, code: str, lang: str = "pl", **params: Any) -> str:
        definition = self.get(code)
        if lang not in definition.texts:
            raise KeyError(f"brak jezyka {lang!r} dla {code}")
        missing = [name for name in definition.params if name not in params]
        if missing:
            raise ValueError(f"{code}: brak parametrow {missing}")
        return definition.texts[lang].format(**params)


def load_catalog(path: Path | str | None = None) -> Catalog:
    source = Path(path) if path is not None else DEFAULT_PATH
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise CatalogError(f"{source.name}: oczekiwano listy wpisow")
    problems: list[str] = []
    definitions = []
    seen: set[str] = set()
    for index, entry in enumerate(data, start=1):
        definition = _build(entry, index, problems)
        if definition is None:
            continue
        if definition.code in seen:
            problems.append(f"{definition.code}: powtorzony kod")
        seen.add(definition.code)
        definitions.append(definition)
    if problems:
        raise CatalogError("; ".join(problems))
    return Catalog(definitions)
