"""Plik tabeli narzędzi LinuxCNC `tool.tbl`: odczyt i zapis bez strat (sesja 032).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 032

Format (dokumentacja LinuxCNC 2.9, „Tool Table Format”): jedna linia na narzędzie, słowa
rozdzielone spacją: T (numer, wymagany), P (gniazdo 0…99999, wymagane, 0 = wrzeciono),
przesunięcia X Y Z A B C U V W, D (średnica), I J (kąty, tokarka), Q (orientacja 0…9, tokarka),
`;` komentarz do końca linii. Linie zaczynające się od `;` są pomijane przez LinuxCNC.
Wartości są w jednostkach maszyny (LINEAR_UNITS z INI); baza trzyma mm — `scale_entries()`.
Zapis kanoniczny: rosnąco po T, kolumny w kolejności dokumentacji, pola zerowe pominięte poza
T, P, Z i D — `format(parse(x))` jest stałe, a `parse(format(t)) == t` (test roundtrip).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .types import ToolIssue

OFFSET_AXES = ("X", "Y", "Z", "A", "B", "C", "U", "V", "W")
FLOAT_WORDS = OFFSET_AXES + ("D", "I", "J")
# Dokumentacja 2.9 podaje 1000 (zmieniacz losowy), ale przykładowy sim.tbl z LinuxCNC ma P99999
# i LinuxCNC go wczytuje — przyjmujemy jak LinuxCNC.
MAX_POCKET = 99999
INCH = 25.4
_NUM = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


class ToolTableError(ValueError):
    """Niepoprawny plik tabeli narzędzi; `issues` z numerem linii (P-5204)."""

    def __init__(self, issues: list[ToolIssue]):
        super().__init__("; ".join(i.message() for i in issues))
        self.issues = issues


@dataclass
class TblEntry:
    number: int
    pocket: int
    values: dict[str, float] = field(default_factory=dict)  # X…W, D, I, J
    orientation: int | None = None                          # Q
    comment: str = ""


def fmt_value(value: float) -> str:
    """Liczba w zapisie stałym, do 6 miejsc po przecinku, bez „-0”."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _issue(line: int, detail: str) -> ToolIssue:
    return ToolIssue("P-5204", {"line": line, "detail": detail})


def parse_tbl(text: str) -> list[TblEntry]:
    """Treść tool.tbl → wpisy (ToolTableError ze wszystkimi błędami)."""
    entries: list[TblEntry] = []
    issues: list[ToolIssue] = []
    numbers: dict[int, int] = {}
    pockets: dict[int, int] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        body, _, comment = raw.partition(";")
        if not body.strip():
            continue  # pusta albo komentarz
        words: dict[str, str] = {}
        bad = False
        for word in body.split():
            letter, value = word[:1].upper(), word[1:]
            if letter not in ("T", "P", "Q") + FLOAT_WORDS:
                issues.append(_issue(line_no, f"nieznane słowo {word}"))
                bad = True
                continue
            if letter in words:
                issues.append(_issue(line_no, f"słowo {letter} powtórzone"))
                bad = True
                continue
            words[letter] = value
        for required in ("T", "P"):
            if required not in words:
                issues.append(_issue(line_no, f"brak wymaganego słowa {required}"))
                bad = True
        if bad:
            continue
        entry = _entry(words, comment.strip(), line_no, issues)
        if entry is None:
            continue
        if entry.number in numbers:
            issues.append(_issue(line_no, f"T{entry.number} już w linii {numbers[entry.number]}"))
            continue
        if entry.pocket in pockets:
            issues.append(_issue(line_no, f"P{entry.pocket} już w linii {pockets[entry.pocket]}"))
            continue
        numbers[entry.number] = pockets[entry.pocket] = line_no
        entries.append(entry)
    if issues:
        raise ToolTableError(issues)
    return entries


def _entry(words: dict[str, str], comment: str, line: int,
           issues: list[ToolIssue]) -> TblEntry | None:
    def integer(letter: str, lo: int, hi: int) -> int | None:
        text = words[letter]
        if not re.fullmatch(r"\+?\d+", text) or not lo <= int(text) <= hi:
            issues.append(_issue(line, f"{letter}{text}: oczekiwano liczby całkowitej {lo}…{hi}"))
            return None
        return int(text)

    number = integer("T", 1, 2**31 - 1)
    pocket = integer("P", 0, MAX_POCKET)
    orientation = integer("Q", 0, 9) if "Q" in words else None
    values: dict[str, float] = {}
    for letter in FLOAT_WORDS:
        if letter in words:
            text = words[letter]
            if not _NUM.match(text) or not math.isfinite(float(text)):
                issues.append(_issue(line, f"{letter}{text}: oczekiwano liczby"))
                return None
            value = float(text)
            if value != 0.0 or letter in ("Z", "D"):  # zero = brak przesunięcia
                values[letter] = value
    if "D" in values and values["D"] < 0:
        issues.append(_issue(line, "D: średnica nie może być ujemna"))
        return None
    if number is None or pocket is None or ("Q" in words and orientation is None):
        return None
    return TblEntry(number, pocket, values, orientation, comment)


LENGTH_WORDS = OFFSET_AXES[:3] + OFFSET_AXES[6:] + ("D",)  # X Y Z U V W D; A B C, I J to kąty


def scale_entries(entries: list[TblEntry], factor: float) -> list[TblEntry]:
    """Wpisy z długościami pomnożonymi przez `factor` (mm → cale: 1/25,4; cale → mm: 25,4)."""
    return [TblEntry(e.number, e.pocket,
                     {k: (v * factor if k in LENGTH_WORDS else v) for k, v in e.values.items()},
                     e.orientation, e.comment) for e in entries]


def format_tbl(entries: list[TblEntry]) -> str:
    """Wpisy → tekst tool.tbl w postaci kanonicznej (rosnąco po T)."""
    lines = []
    for e in sorted(entries, key=lambda e: e.number):
        words = [f"T{e.number}", f"P{e.pocket}"]
        for letter in FLOAT_WORDS:
            value = e.values.get(letter)
            if value is None or (value == 0.0 and letter not in ("Z", "D")):
                continue
            words.append(f"{letter}{fmt_value(value)}")
        if e.orientation is not None:
            words.append(f"Q{e.orientation}")
        if e.comment:
            words.append(f";{e.comment}")
        lines.append(" ".join(words))
    return "\n".join(lines) + ("\n" if lines else "")
