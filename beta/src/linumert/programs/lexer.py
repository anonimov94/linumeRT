"""Lekser i kontrola składni G-code LinuxCNC (rs274ngc) z błędami linia/kolumna (sesja 044).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 044

Zakres (własna implementacja na podstawie opisu języka w dokumentacji LinuxCNC 2.9, bez kodu
interpretera): słowa (litera + wartość), komentarze `( )` i `;`, numer linii N, usuwanie
bloku `/`, ograniczniki `%`, parametry (`#1`, `##2`, `#[...]`, `#<nazwa>`, `#<_globalny>`)
i przypisania `#…=…`, wyrażenia `[...]` z operatorami i funkcjami, słowa O (`o100 sub`,
`o<nazwa> call [..]`, if/elseif/else/endif, while/endwhile, do/while, repeat/endrepeat,
return, break, continue) z kontrolą parowania bloków w całym pliku.
Nie sprawdza semantyki (grupy modalne, brak posuwu, zakresy) — to robi interpreter LinuxCNC
(`linuxcnc_check.py`, gdy dostępny). Zgodność werdyktów z rs274 pilnuje
`tests/test_lexer.py` (marker `linuxcnc`).

Spacje i tabulatory poza komentarzami są ignorowane (jak w rs274ngc), wielkość liter też.
Kolumny w błędach liczone od 1 w oryginalnej linii.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from linumert.alarms.catalog import load_catalog

# E jest słowem w LinuxCNC 2.9 (G70/G76, M66–M68); O to słowo O, obsługiwane osobno.
WORD_LETTERS = set("ABCDEFGHIJKLMNPQRSTUVWXYZ")
FUNCTIONS = ("ABS", "ACOS", "ASIN", "ATAN", "COS", "EXISTS", "EXP", "FIX", "FUP", "LN",
             "ROUND", "SIN", "SQRT", "TAN")
OPERATORS = ("MOD", "AND", "XOR", "EQ", "NE", "GT", "GE", "LT", "LE", "OR")
O_KEYWORDS = ("ENDSUB", "SUB", "CALL", "RETURN", "ELSEIF", "ELSE", "ENDIF", "IF", "ENDWHILE",
              "WHILE", "DO", "ENDREPEAT", "REPEAT", "BREAK", "CONTINUE")
_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)")
_NAME = re.compile(r"[A-Z0-9_]+")

_CATALOG = None


def _catalog():
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_catalog()
    return _CATALOG


@dataclass(frozen=True)
class LexIssue:
    """Błąd składni: kod P-51xx, linia i kolumna (od 1) oraz parametry komunikatu."""

    code: str
    line: int
    col: int
    params: dict[str, Any] = field(default_factory=dict)

    def message(self, lang: str = "pl") -> str:
        return _catalog().format(self.code, lang, line=self.line, col=self.col, **self.params)


@dataclass
class Word:
    letter: str
    value: str          # tekst wartości (liczba, parametr albo wyrażenie), wielkie litery
    col: int


@dataclass
class OWord:
    label: str          # "100" albo "<nazwa>"
    keyword: str        # SUB, CALL, IF, ...
    args: list[str]
    col: int


@dataclass
class Line:
    number: int
    text: str
    words: list[Word] = field(default_factory=list)
    assignments: list[tuple[str, str]] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    oword: OWord | None = None
    block_delete: bool = False
    percent: bool = False


@dataclass
class LexResult:
    lines: list[Line]
    issues: list[LexIssue]

    @property
    def ok(self) -> bool:
        return not self.issues


class _Stop(Exception):
    def __init__(self, issue: LexIssue):
        super().__init__(issue.code)
        self.issue = issue


class _Cursor:
    """Kod linii bez spacji i komentarzy, z kolumnami w oryginale."""

    def __init__(self, chars: list[tuple[str, int]], line: int):
        self.s = "".join(c for c, _ in chars).upper()
        self.cols = [col for _, col in chars]
        self.i = 0
        self.line = line

    def col(self, i: int | None = None) -> int:
        i = self.i if i is None else i
        if i < len(self.cols):
            return self.cols[i]
        return (self.cols[-1] + 1) if self.cols else 1

    def peek(self, n: int = 1) -> str:
        return self.s[self.i:self.i + n]

    def at_end(self) -> bool:
        return self.i >= len(self.s)

    def fail(self, code: str, at: int | None = None, **params: Any) -> _Stop:
        return _Stop(LexIssue(code, self.line, self.col(at), params))

    # ---- wartości --------------------------------------------------------------------------
    def number(self) -> str:
        m = _NUMBER.match(self.s, self.i)
        if not m:
            raise self.fail("P-5105", text=self.s[self.i:self.i + 8] or "∅")
        if self.s[m.end():m.end() + 1] == ".":  # 1.2.3
            tail = re.compile(r"[0-9.]*").match(self.s, m.end())
            assert tail is not None
            raise self.fail("P-5105", text=self.s[self.i:tail.end()])
        self.i = m.end()
        return m.group(0)

    def param(self) -> str:
        start = self.i
        self.i += 1  # '#'
        c = self.peek()
        if c == "<":
            end = self.s.find(">", self.i)
            name = self.s[self.i + 1:end] if end >= 0 else ""
            if end < 0 or not name or not _NAME.fullmatch(name):
                raise self.fail("P-5108", start, text=self.s[start:start + 12])
            self.i = end + 1
        elif c == "#":
            self.param()
        elif c == "[":
            self.bracket()
        elif c.isdigit():
            m = re.compile(r"\d+").match(self.s, self.i)
            assert m is not None
            self.i = m.end()
            if self.peek() == ".":
                raise self.fail("P-5108", start, text=self.s[start:self.i + 1])
        else:
            raise self.fail("P-5108", start, text=self.s[start:start + 6] or "#")
        return self.s[start:self.i]

    def real_value(self, letter: str) -> str:
        start = self.i
        c = self.peek()
        if self.at_end():
            raise self.fail("P-5104", letter=letter)
        if c == "#":
            self.param()
        elif c == "[":
            self.bracket()
        elif c.isalpha():
            self.function()
        elif c in "+-.0123456789":
            self.number()
        else:
            raise self.fail("P-5104", letter=letter)
        return self.s[start:self.i]

    def function(self) -> None:
        for name in FUNCTIONS:
            if self.s.startswith(name, self.i):
                start = self.i
                self.i += len(name)
                if self.peek() != "[":
                    raise self.fail("P-5110", detail=f"po {name} oczekiwano [")
                self.bracket()
                if name == "ATAN":
                    if self.peek() != "/":
                        raise self.fail("P-5110", start, detail="ATAN wymaga postaci ATAN[a]/[b]")
                    self.i += 1
                    if self.peek() != "[":
                        raise self.fail("P-5110", detail="ATAN[a]/[b]: brak [b]")
                    self.bracket()
                return
        m = re.compile(r"[A-Z]+").match(self.s, self.i)
        raise self.fail("P-5107", name=m.group(0) if m else self.peek())

    def bracket(self) -> None:
        """Wyrażenie `[ operand (operator operand)* ]`."""
        open_at = self.i
        self.i += 1
        self.operand(open_at)
        while True:
            if self.at_end():
                raise self.fail("P-5106", open_at)
            if self.peek() == "]":
                self.i += 1
                return
            self.operator()
            self.operand(open_at)

    def operand(self, open_at: int) -> None:
        if self.at_end():
            raise self.fail("P-5106", open_at)
        c = self.peek()
        if c == "]":
            raise self.fail("P-5110", detail="puste wyrażenie albo brak argumentu")
        if c == "-" and self.s[self.i + 1:self.i + 2] in ("#", "[") or (
                c == "-" and self.s[self.i + 1:self.i + 2].isalpha()):
            self.i += 1  # minus jednoargumentowy przed parametrem, nawiasem albo funkcją
            c = self.peek()
        if c == "#":
            self.param()
        elif c == "[":
            self.bracket()
        elif c.isalpha():
            self.function()
        elif c in "+-.0123456789":
            self.number()
        else:
            raise self.fail("P-5110", detail=f"nieoczekiwany znak {c}")

    def operator(self) -> None:
        if self.s.startswith("**", self.i):
            self.i += 2
            return
        c = self.peek()
        if c in "+-*/":
            self.i += 1
            return
        for name in OPERATORS:
            if self.s.startswith(name, self.i):
                self.i += len(name)
                return
        m = re.compile(r"[A-Z]+").match(self.s, self.i)
        if m:
            raise self.fail("P-5107", name=m.group(0))
        raise self.fail("P-5110", detail=f"oczekiwano operatora, jest {c}")


def _split_comments(text: str, line_no: int) -> tuple[list[tuple[str, int]], list[str]]:
    """Znaki kodu (bez spacji i komentarzy) z kolumnami i treść komentarzy."""
    chars: list[tuple[str, int]] = []
    comments: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == ";":
            comments.append(text[i + 1:])
            break
        if c == "(":
            end = text.find(")", i + 1)
            nested = text.find("(", i + 1)
            if end < 0:
                raise _Stop(LexIssue("P-5101", line_no, i + 1))
            if 0 <= nested < end:
                raise _Stop(LexIssue("P-5102", line_no, nested + 1))
            comments.append(text[i + 1:end])
            i = end + 1
            continue
        if c == ")":
            raise _Stop(LexIssue("P-5101", line_no, i + 1))
        if c not in " \t\r":
            chars.append((c, i + 1))
        i += 1
    return chars, comments


def _lex_line(text: str, number: int) -> Line:
    line = Line(number, text)
    chars, line.comments = _split_comments(text, number)
    cur = _Cursor(chars, number)
    if cur.s == "%":
        line.percent = True
        return line
    if cur.peek() == "/":
        line.block_delete = True
        cur.i += 1
    first = True
    while not cur.at_end():
        c = cur.peek()
        col = cur.col()
        if c == "O":
            line.oword = _oword(cur)
            break
        if c == "#":
            name = cur.param()
            if cur.peek() != "=":
                raise cur.fail("P-5108", text=name)
            cur.i += 1
            line.assignments.append((name, cur.real_value("=")))
        elif c in WORD_LETTERS:
            cur.i += 1
            if c == "N":
                if not first:
                    raise cur.fail("P-5111", cur.i - 1)
                m = re.compile(r"\d+").match(cur.s, cur.i)
                if not m:
                    raise cur.fail("P-5104", letter="N")
                cur.i = m.end()
                line.words.append(Word("N", m.group(0), col))
            else:
                line.words.append(Word(c, cur.real_value(c), col))
        else:
            raise cur.fail("P-5103", letter=c)
        first = False
    return line


def _oword(cur: _Cursor) -> OWord:
    col = cur.col()
    cur.i += 1
    if cur.peek() == "<":
        end = cur.s.find(">", cur.i)
        name = cur.s[cur.i + 1:end] if end >= 0 else ""
        if end < 0 or not _NAME.fullmatch(name or "?"):
            raise cur.fail("P-5109", detail="niepoprawna nazwa o<...>")
        label = f"<{name}>"
        cur.i = end + 1
    else:
        m = re.compile(r"\d+").match(cur.s, cur.i)
        if not m:
            raise cur.fail("P-5109", detail="po O oczekiwano numeru albo <nazwy>")
        label = str(int(m.group(0)))
        cur.i = m.end()
    keyword = next((k for k in O_KEYWORDS if cur.s.startswith(k, cur.i)), None)
    if keyword is None:
        raise cur.fail("P-5109", detail="brak słowa kluczowego (sub, call, if, while, …)")
    cur.i += len(keyword)
    args = []
    while not cur.at_end():
        if cur.peek() != "[":
            raise cur.fail("P-5109", detail=f"po {keyword.lower()} dozwolone są tylko [wyrażenia]")
        start = cur.i
        cur.bracket()
        args.append(cur.s[start:cur.i])
    needs_arg = keyword in ("IF", "ELSEIF", "WHILE", "REPEAT")
    if needs_arg and len(args) != 1:
        raise cur.fail("P-5109", detail=f"{keyword.lower()} wymaga jednego [warunku]")
    if keyword not in ("CALL", "RETURN", "IF", "ELSEIF", "WHILE", "REPEAT") and args:
        raise cur.fail("P-5109", detail=f"{keyword.lower()} nie przyjmuje argumentów")
    return OWord(label, keyword, args, col)


_OPEN = {"SUB": "ENDSUB", "IF": "ENDIF", "WHILE": "ENDWHILE", "DO": "WHILE",
         "REPEAT": "ENDREPEAT"}


def _structure(lines: list[Line]) -> list[LexIssue]:
    """Parowanie bloków słów O w całym pliku (etykiety muszą się zgadzać)."""
    issues: list[LexIssue] = []
    stack: list[tuple[str, str, Line, OWord]] = []  # (otwarcie, etykieta, linia, słowo)

    def err(line: Line, ow: OWord, detail: str) -> None:
        issues.append(LexIssue("P-5109", line.number, ow.col, {"detail": detail}))

    for line in lines:
        ow = line.oword
        if ow is None:
            continue
        k, label = ow.keyword, ow.label
        top = stack[-1] if stack else None
        if k == "WHILE" and top is not None and top[0] == "DO" and top[1] == label:
            stack.pop()  # koniec pętli do … while
        elif k in _OPEN:
            stack.append((k, label, line, ow))
        elif k in ("ENDSUB", "ENDIF", "ENDWHILE", "ENDREPEAT"):
            opener = {"ENDSUB": "SUB", "ENDIF": "IF", "ENDWHILE": "WHILE",
                      "ENDREPEAT": "REPEAT"}[k]
            if top is None or top[0] != opener or top[1] != label:
                err(line, ow, f"o{label} {k.lower()} bez pasującego o{label} {opener.lower()}")
            else:
                stack.pop()
        elif k in ("ELSE", "ELSEIF"):
            if top is None or top[0] != "IF" or top[1] != label:
                err(line, ow, f"o{label} {k.lower()} poza blokiem o{label} if")
        elif k in ("BREAK", "CONTINUE"):
            if not any(s[0] in ("WHILE", "DO", "REPEAT") and s[1] == label for s in stack):
                err(line, ow, f"o{label} {k.lower()} poza pętlą o{label}")
        elif k == "RETURN":
            if not any(s[0] == "SUB" and s[1] == label for s in stack):
                err(line, ow, f"o{label} return poza podprogramem o{label} sub")
    for opener, label, line, ow in stack:
        closer = _OPEN[opener].lower()
        err(line, ow, f"o{label} {opener.lower()} bez o{label} {closer}")
    return issues


def lex(text: str) -> LexResult:
    """Lekser całego pliku: linie i wszystkie błędy (po jednym na linię + struktura O)."""
    lines: list[Line] = []
    issues: list[LexIssue] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        try:
            lines.append(_lex_line(raw, number))
        except _Stop as stop:
            issues.append(stop.issue)
            lines.append(Line(number, raw))
    issues += _structure(lines)
    issues.sort(key=lambda i: (i.line, i.col))
    return LexResult(lines, issues)


def check(text: str) -> list[LexIssue]:
    """Błędy składni programu (pusta lista = składnia poprawna)."""
    return lex(text).issues
