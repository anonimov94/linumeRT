"""Klasa bazowa generatorów cykli (programowanie dialogowe, sesja 039).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 039

Generator = nazwa, wersja, opis pól formularza (`fields`), walidacja (lista błędów P-xxxx
z katalogu alarmów), generowanie linii G-code LinuxCNC i podgląd 2D. Generator jest czystą
funkcją parametrów: ten sam zestaw parametrów i ta sama wersja dają te same linie (kompilator
.lnx zapisuje wersję generatora w programie). Generatory wytwarzają wyłącznie tekst G-code
(CLAUDE.md §6): podprogramy `o<nazwa> call`, nigdy M98/M99 (§8) — pilnuje tego kompilator.

Nakładki zgodności dla wtyczek i starszego kodu: `is_valid(params) -> bool` oraz
`generate_ngc(params, filename) -> str` (pełny program z jednym krokiem).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any, ClassVar, Literal

from linumert.alarms.catalog import load_catalog

FieldKind = Literal["float", "int", "bool", "choice", "text"]
Polyline = list[tuple[float, float]]


@dataclass(frozen=True)
class Field:
    """Pole formularza generatora."""

    name: str
    kind: FieldKind
    label: str                      # etykieta po polsku (tłumaczenia: sesja 037)
    unit: str = ""
    default: Any = None             # None = pole wymagane
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    exclusive_minimum: bool = False  # True: wartość musi być > minimum

    @property
    def required(self) -> bool:
        return self.default is None


@dataclass(frozen=True)
class Issue:
    """Błąd walidacji: kod z katalogu alarmów, jego parametry i pole formularza."""

    code: str
    params: dict[str, Any] = dc_field(default_factory=dict)
    field: str | None = None

    def message(self, lang: str = "pl") -> str:
        return _catalog().format(self.code, lang, **self.params)


_CATALOG = None


def _catalog():
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_catalog()
    return _CATALOG


def fmt(value: float, decimals: int = 4) -> str:
    """Liczba dla G-code: zapis stały, bez wykładnika i zbędnych zer, bez „-0”."""
    if not math.isfinite(value):
        raise ValueError(f"wartość nieskończona albo NaN w G-code: {value!r}")
    text = f"{value:.{decimals}f}"
    if "." in text:  # bez części ułamkowej (decimals = 0) zer nie obcinamy: 8000, nie 8
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "", "-") else text


class BaseMacroGenerator(ABC):
    """Generator jednego kroku programu dialogowego."""

    name: ClassVar[str]
    version: ClassVar[int]
    title: ClassVar[str]               # nazwa w menu, po polsku
    fields: ClassVar[tuple[Field, ...]] = ()

    # ---- parametry -----------------------------------------------------------------------
    def normalize(self, params: dict[str, Any], step: int = 0) -> tuple[dict[str, Any],
                                                                          list[Issue]]:
        """Parametry z wartościami domyślnymi i rzutowaniem typów + błędy pól (P-5014/15/03)."""
        issues: list[Issue] = []
        known = {f.name for f in self.fields}
        out: dict[str, Any] = {}
        for name in sorted(set(params) - known):
            issues.append(Issue("P-5015", {"step": step, "field": name,
                                           "expected": "pole znane generatorowi"}, name))
        for f in self.fields:
            if f.name not in params or params[f.name] is None:
                if f.required:
                    issues.append(Issue("P-5014", {"step": step, "field": f.name}, f.name))
                    continue
                out[f.name] = f.default
                continue
            value, problem = _coerce(f, params[f.name])
            if problem is not None:
                issues.append(Issue("P-5015", {"step": step, "field": f.name,
                                               "expected": problem}, f.name))
                continue
            limit = _range_problem(f, value)
            if limit is not None:
                display = str(value) if f.kind == "int" else fmt(value)
                issues.append(Issue("P-5003", {"name": f.name, "value": display[:80],
                                               "limit": limit}, f.name))
                continue
            out[f.name] = value
        return out, issues

    def validate(self, params: dict[str, Any], step: int = 0) -> list[Issue]:
        """Wszystkie błędy parametrów (pusta lista = poprawne)."""
        values, issues = self.normalize(params, step)
        if not issues:
            issues = list(self.check(values, step))
        return issues

    def check(self, values: dict[str, Any], step: int) -> list[Issue]:
        """Reguły między polami (nadpisywane w generatorach); `values` po `normalize`."""
        del values, step
        return []

    # ---- wynik ---------------------------------------------------------------------------
    @abstractmethod
    def generate(self, values: dict[str, Any]) -> list[str]:
        """Linie G-code dla poprawnych parametrów (bez znaków nowej linii)."""

    def preview_2d(self, values: dict[str, Any]) -> list[Polyline]:
        """Podgląd 2D w płaszczyźnie XY [mm] (lista łamanych); domyślnie brak."""
        del values
        return []

    # ---- nakładki zgodności ------------------------------------------------------------
    def is_valid(self, params: dict[str, Any]) -> bool:
        return not self.validate(params)

    def generate_ngc(self, params: dict[str, Any], filename: str) -> str:
        """Pełny program z jednym krokiem (bez przygotówki); ValueError przy błędach."""
        from linumert.generators.registry import GeneratorRegistry
        from linumert.programs.compiler import compile_program
        from linumert.programs.lnx import LnxProgram, Step

        registry = GeneratorRegistry()
        registry.register(type(self))
        program = LnxProgram(name=filename,
                             steps=[Step(generator=self.name, version=self.version,
                                         params=params)])
        return compile_program(program, registry, source=filename)


def _coerce(f: Field, raw: Any) -> tuple[Any, str | None]:
    if f.kind == "bool":
        return (raw, None) if isinstance(raw, bool) else (None, "tak/nie (true/false)")
    if f.kind == "int":
        if isinstance(raw, bool) or not isinstance(raw, int):
            if isinstance(raw, float) and raw.is_integer():
                return int(raw), None
            return None, "liczba całkowita"
        return raw, None
    if f.kind == "float":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None, "liczba"
        try:
            raw = float(raw)
        except OverflowError:
            return None, "liczba skończona"
        if not math.isfinite(raw):
            return None, "liczba skończona"
        return float(raw), None
    if f.kind == "choice":
        if raw not in f.choices:
            return None, "jedna z: " + ", ".join(f.choices)
        return raw, None
    if not isinstance(raw, str) or "\n" in raw or "(" in raw or ")" in raw:
        return None, "tekst w jednej linii bez nawiasów"
    return raw, None


def _range_problem(f: Field, value: Any) -> str | None:
    if f.kind not in ("float", "int"):
        return None
    lo, hi = f.minimum, f.maximum
    too_low = lo is not None and (value <= lo if f.exclusive_minimum else value < lo)
    too_high = hi is not None and value > hi
    if not (too_low or too_high):
        return None
    left = "brak" if lo is None else (f"> {fmt(lo)}" if f.exclusive_minimum else f">= {fmt(lo)}")
    right = "brak" if hi is None else f"<= {fmt(hi)}"
    unit = f" {f.unit}" if f.unit else ""
    return f"{left}, {right}{unit}"
