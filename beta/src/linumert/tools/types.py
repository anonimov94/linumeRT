"""Typy narzędzi i walidacja (docs/wymagania/NARZEDZIA_I_KOLIZJE.md §1, sesja 032).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 032

Każdy typ ma listę parametrów wymaganych i opcjonalnych (mm, stopnie) oraz reguły między nimi.
Narzędzie bez typu jest dozwolone (np. zaimportowane z tool.tbl), ale symulacja użyje walca
zastępczego D × L i zgłosi K-320 (`Tool.warnings()`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

from linumert.alarms.catalog import load_catalog


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    unit: str = "mm"
    minimum: float = 0.0
    maximum: float = 2000.0
    exclusive_minimum: bool = True


@dataclass(frozen=True)
class ToolType:
    id: str
    label: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    profile: str = ""


PARAMS: dict[str, Param] = {p.name: p for p in (
    Param("d", "Średnica D"),
    Param("l", "Długość L (wysięg z oprawki)"),
    Param("flute_length", "Długość ostrza"),
    Param("corner_radius", "Promień naroża R"),
    Param("width", "Szerokość tarczy"),
    Param("neck_d", "Średnica szyjki"),
    Param("neck_l", "Długość szyjki"),
    Param("angle", "Kąt", unit="°", maximum=180.0),
    Param("h", "Wysokość H"),
    Param("flutes", "Liczba ostrzy", unit="", maximum=50.0),
    Param("pitch", "Skok gwintu"),
    # Wspólne dla wszystkich typów (symulacja HMI, 2026-10-19): obroty, kierunek, korekcja, oprawka
    Param("max_rpm", "Maks. obroty", unit="obr/min", maximum=200000.0),
    Param("hand", "Kierunek skrawania (1 = prawy M3, -1 = lewy M4)", unit="", minimum=-1.0,
          maximum=1.0, exclusive_minimum=False),
    Param("d_wear", "Korekcja średnicy", minimum=-1.0, maximum=1.0, exclusive_minimum=False),
    Param("holder_d", "Średnica oprawki"),
    Param("holder_l", "Długość oprawki"),
)}

# Pola dozwolone w każdym typie (i w narzędziu bez typu)
COMMON: tuple[str, ...] = ("flutes", "max_rpm", "hand", "d_wear", "holder_d", "holder_l")

TYPES: dict[str, ToolType] = {t.id: t for t in (
    ToolType("flat", "Frez palcowy", ("d", "l", "flute_length"), ("flutes",),
             "walec z płaskim czołem"),
    ToolType("ball", "Frez kulowy", ("d", "l"), ("flute_length", "flutes"),
             "walec + półkula R = D/2"),
    ToolType("bull", "Frez torusowy", ("d", "l", "corner_radius"), ("flute_length", "flutes"),
             "walec z zaokrąglonym narożem"),
    ToolType("tslot", "Frez teowy", ("d", "width", "neck_d", "neck_l"), ("l", "flutes"),
             "tarcza na szyjce"),
    ToolType("lollipop", "Frez lizakowy", ("d", "neck_d", "neck_l"), ("l",), "kula na szyjce"),
    ToolType("chamfer", "Fazownik", ("d", "angle"), ("l",), "stożek"),
    ToolType("drill_118", "Wiertło 118°/120°", ("d", "l"), ("flute_length",), "walec + stożek"),
    ToolType("drill_angle", "Wiertło z kątem", ("d", "angle"), ("l", "flute_length"),
             "walec + stożek (180° = płaskie)"),
    ToolType("face_mill", "Głowica frezarska", ("d", "h"), ("l", "flutes"), "walec D × H"),
    ToolType("tap", "Gwintownik", ("d", "l", "pitch"), ("flute_length",),
             "walec, tylko z obrotami"),
    ToolType("special_stl", "Specjalne (STL)", (), ("d", "l"), "z pliku STL"),
)}


_CATALOG = None


def _catalog():
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_catalog()
    return _CATALOG


@dataclass(frozen=True)
class ToolIssue:
    """Błąd albo ostrzeżenie bazy narzędzi (kod z katalogu alarmów)."""

    code: str
    params: dict[str, Any] = dc_field(default_factory=dict)
    field: str | None = None

    def message(self, lang: str = "pl") -> str:
        return _catalog().format(self.code, lang, **self.params)


def _bad(tool: int, name: str, expected: str) -> ToolIssue:
    return ToolIssue("P-5201", {"tool": tool, "field": name, "expected": expected}, name)


def finite_number(value: Any) -> bool:
    """Real, finite tool value, excluding bool. Model-Author: Codex."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_geometry(number: int, type_id: str | None, params: dict[str, Any],
                      stl: str | None) -> list[ToolIssue]:
    """Parametry narzędzia wobec typu: wymagane, zakresy, reguły między polami."""
    issues: list[ToolIssue] = []
    for name, value in params.items():
        spec = PARAMS.get(name)
        if spec is None:
            issues.append(_bad(number, name, "parametr znany typom narzędzi"))
            continue
        if not finite_number(value):
            issues.append(_bad(number, name, f"liczba [{spec.unit}]".replace(" []", "")))
            continue
        low_ok = value > spec.minimum if spec.exclusive_minimum else value >= spec.minimum
        if not low_ok or value > spec.maximum:
            issues.append(_bad(number, name, f"> {spec.minimum:g} i <= {spec.maximum:g} {spec.unit}"
                               .rstrip()))
    if type_id is None:
        return issues
    tool_type = TYPES.get(type_id)
    if tool_type is None:
        return issues + [ToolIssue("P-5205", {"tool": number, "type": type_id}, "type")]
    for name in tool_type.required:
        if name not in params:
            issues.append(_bad(number, name, f"pole wymagane dla typu {type_id}"))
    allowed = set(tool_type.required) | set(tool_type.optional) | set(COMMON)
    for name in params:
        if name in PARAMS and name not in allowed:
            issues.append(_bad(number, name, f"pole nieużywane przez typ {type_id}"))
    if issues:
        return issues
    p = params
    if type_id == "special_stl" and not stl:
        issues.append(_bad(number, "stl", "plik STL (oś Z, czoło w 0)"))
    if "flute_length" in p and "l" in p and p["flute_length"] > p["l"]:
        issues.append(_bad(number, "flute_length", "<= L"))
    if type_id == "bull" and p["corner_radius"] > p["d"] / 2:
        issues.append(_bad(number, "corner_radius", "<= D/2"))
    if type_id in ("tslot", "lollipop") and p["neck_d"] >= p["d"]:
        issues.append(_bad(number, "neck_d", "< D"))
    if "hand" in p and p["hand"] not in (1, -1):
        issues.append(_bad(number, "hand", "1 (prawy, M3) albo -1 (lewy, M4)"))
    if type_id in ("chamfer",) and p["angle"] >= 180:
        issues.append(_bad(number, "angle", "< 180° dla fazownika"))
    return issues

