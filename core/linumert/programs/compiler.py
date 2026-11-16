"""Kompilator programu dialogowego `.lnx` → `.ngc` LinuxCNC (sesja 039).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 039

Wynik jest deterministyczny: brak dat, ścieżek bezwzględnych i losowości; ten sam program
i te same wersje generatorów dają identyczny plik (test golden). Struktura:

    ( linumeRT: program <nazwa> )
    ( zrodlo: <plik.lnx>, schemat .lnx 1 )
    ;@STOCK ...                              (gdy program ma przygotówkę)
    G21                                      (jednostki programu: G21 mm / G20 cale)
    ( krok 1: <generator> v<wersja> - <komentarz> )
    ( OP 1 [o100]: <rodzaj> | T3 D10 S8000 M3 | F1200 FZ300 | Z -5..2 mm )
    o100 if [1]                              (blok operacji: wykonywany zawsze raz)
    ...linie generatora...
    o100 endif
    ( krok 2 pominiety: ... )                (krok wyłączony)
    M2

Każda operacja (włączony krok) ma własny numer O = numer kroku × 100 i komentarz z danymi
(polecenie właściciela 2026-11-05, PROPOZYCJA w DECYZJE): narzędzie z ostatniego kroku
`tool_change`, średnica (pole `tool_d` albo baza narzędzi), obroty, posuwy i zakres Z z linii
generatora. Numery N+1…N+99 są wolne dla bloków O generatora tej operacji; powtórzony numer O
w dwóch krokach albo równy numerowi operacji to P-5013.

Błąd walidacji dowolnego kroku blokuje cały wynik (`CompileError` z listą Issue) — nic nie
jest zapisywane. Kompilator sprawdza też wynik generatora: linia bez znaku nowej linii,
nawiasy komentarzy zamknięte, brak M98/M99 (podprogramy LinuxCNC: `o<nazwa> call`, §8)
i brak M2/M30 (koniec programu dopisuje kompilator).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from linumert.generators.base import SAFE_Z_MOVE, Issue, fmt
from linumert.generators.registry import DEFAULT_REGISTRY, GeneratorRegistry
from linumert.generators.tooling import ToolLookup, check_steps

from .lnx import SCHEMA_VERSION, LnxProgram, atomic_write, load_lnx
from .stock import format_stock_line

_FORBIDDEN = re.compile(r"(?<![A-Z0-9.#])M0*(98|99|2|30)(?![0-9.])", re.IGNORECASE)
_COMMENT = re.compile(r"\([^()]*\)")
_OWORD_NUMBER = re.compile(r"^\s*/?\s*(?:N\d+\s*)?O\s*(\d+)(?=\s*[A-Z])", re.IGNORECASE)
_Z_WORD = re.compile(r"(?<![A-Z#<_])Z\s*([-+]?(?:\d+\.?\d*|\.\d+))", re.IGNORECASE)
OP_NUMBER_STEP = 100  # numer O operacji = numer kroku × 100


class CompileError(ValueError):
    """Program nie daje się skompilować; `issues` — błędy P-xxxx ze wskazaniem kroku."""

    def __init__(self, issues: list[Issue]):
        super().__init__("; ".join(i.message() for i in issues))
        self.issues = issues


def _comment(text: str) -> str:
    """Tekst do komentarza G-code: bez nawiasów i nowych linii (nawiasy zamyka LinuxCNC)."""
    clean = text.replace("(", "[").replace(")", "]").replace("\n", " ").strip()
    return f"( {clean} )"


def _check_output(lines: list[str], step: int) -> list[Issue]:
    issues: list[Issue] = []
    for line in lines:
        if not isinstance(line, str) or "\n" in line or "\r" in line:
            issues.append(Issue("P-5013", {"step": step, "word": "znak nowej linii"}))
            continue
        code = _COMMENT.sub("", line.split(";", 1)[0])
        if "(" in code or ")" in code:
            issues.append(Issue("P-5013", {"step": step, "word": "niezamknięty komentarz"}))
            continue
        match = _FORBIDDEN.search(code)
        if match:
            issues.append(Issue("P-5013", {"step": step, "word": match.group(0).upper()}))
    return issues


def _o_numbers(lines: list[str]) -> set[int]:
    """Numery bloków O (oN if/while/sub…) w liniach generatora, poza komentarzami."""
    out = set()
    for line in lines:
        match = _OWORD_NUMBER.match(_COMMENT.sub("", line.split(";", 1)[0]))
        if match:
            out.add(int(match.group(1)))
    return out


def _z_range(lines: list[str]) -> tuple[float, float] | None:
    """Zakres Z z liczbowych słów Z (bez G53 i komentarzy) — informacja, nie analiza ścieżki."""
    values = []
    for line in lines:
        code = _COMMENT.sub("", line.split(";", 1)[0])
        if re.search(r"G0*53(?![0-9.])", code, re.IGNORECASE):
            continue
        values += [float(v) for v in _Z_WORD.findall(code)]
    return (min(values), max(values)) if values else None


def _op_info(number: int, title: str, values: dict, tool: dict, lines: list[str],
             tools: ToolLookup | None, inch: bool) -> str:
    """Komentarz operacji: rodzaj, narzędzie, obroty, posuwy, zakres Z (jednostki programu)."""
    parts = [f"OP {number} [o{number * OP_NUMBER_STEP}]: {title}"]
    t = values.get("tool", tool.get("tool"))
    words = [f"T{t}"] if t else []
    diameter = values.get("tool_d")
    if diameter is None and t and tools is not None:
        found = tools(t)
        mm = found.tool_diameter() if found is not None else None
        diameter = None if mm is None else (mm / 25.4 if inch else mm)
    if diameter is not None:
        words.append(f"D{fmt(diameter)}")
    rpm = values.get("rpm", tool.get("rpm"))
    spin = values.get("direction")
    spin = spin if spin in ("M3", "M4") else tool.get("direction", "M3")
    if t and rpm:
        words.append(f"S{round(rpm)} {spin}")
    if words:
        parts.append(" ".join(words))
    feeds = [f"F{fmt(values['feed'])}"] if values.get("feed") else []
    if values.get("plunge"):
        feeds.append(f"FZ{fmt(values['plunge'])}")
    if feeds:
        parts.append(" ".join(feeds))
    z = _z_range(lines)
    if z is not None:
        parts.append(f"Z {fmt(z[0])}..{fmt(z[1])} {'in' if inch else 'mm'}")
    return " | ".join(parts)


def _safe_z_line(safe_z: float, inch: bool) -> str:
    """Wycofanie G53 w jednostkach programu, zaokrąglone w dół: nigdy ponad limit maszyny."""
    value = safe_z / 25.4 if inch else safe_z
    return f"G53 G0 Z{fmt(math.floor(value * 10000) / 10000)}"


def compile_program(program: LnxProgram, registry: GeneratorRegistry | None = None,
                    source: str | None = None, tools: ToolLookup | None = None,
                    safe_z: float | None = None) -> str:
    """Program → tekst `.ngc` (CompileError przy dowolnym błędzie).

    `tools` (np. `ToolDB.get`): kroki sprawdzane dodatkowo z bazą narzędzi (P-5206…P-5211).
    `safe_z` [mm] (`limits.safe_z_from_ini`): wysokość G53 aktywnej maszyny zamiast `G53 G0 Z0`
    z generatorów; bez niej tekst nie zależy od maszyny (test golden).
    """
    registry = registry or DEFAULT_REGISTRY
    issues: list[Issue] = []
    body: list[str] = []
    checked: list[tuple[int, str, dict]] = []
    inch = program.units == "inch"
    tool: dict = {}  # ostatni krok tool_change: numer, obroty, kierunek
    op_numbers = {n * OP_NUMBER_STEP for n in range(1, len(program.steps) + 1)}
    used_o: dict[int, int] = {}  # numer O generatora -> krok
    for number, step in enumerate(program.steps, start=1):
        label = f"krok {number}: {step.generator} v{step.version}"
        if step.comment:
            label += f" - {step.comment}"
        generator = registry.get(step.generator, step.version)
        if generator is None:
            issues.append(Issue("P-5011", {"step": number, "name": step.generator,
                                           "version": step.version}))
            continue
        if not step.enabled:
            body.append(_comment(label.replace(f"krok {number}:", f"krok {number} pominiety:")))
            continue
        values, problems = generator.normalize(step.params, number)
        if not problems:
            problems = generator.check(values, number)
        if problems:
            issues += problems
            continue
        checked.append((number, step.generator, values))
        lines = generator.generate(values)
        if step.generator == "header":
            inch = values["units"] == "G20"
        if safe_z is not None:
            lines = [_safe_z_line(safe_z, inch) if line == SAFE_Z_MOVE else line for line in lines]
        problems = _check_output(lines, number)
        for o in sorted(_o_numbers(lines)):
            if o in op_numbers or used_o.get(o, number) != number:
                problems.append(Issue("P-5013", {"step": number,
                                                 "word": f"o{o} (powtórzony numer O)"}))
            used_o[o] = number
        if problems:
            issues += problems
            continue
        o = number * OP_NUMBER_STEP
        body.append(_comment(label))
        body.append(_comment(_op_info(number, generator.title, values, tool, lines, tools,
                                      inch)))
        body.append(f"o{o} if [1]")
        body += lines
        body.append(f"o{o} endif")
        if step.generator == "tool_change":
            tool = {"tool": values["tool"], "rpm": values["rpm"],
                    "direction": values["direction"]}
    if tools is not None:
        issues += check_steps(checked, tools, program.units)
    if issues:
        raise CompileError(issues)
    head = [_comment(f"linumeRT: program {program.name}")]
    if source:
        head.append(_comment(f"zrodlo: {Path(source).name}, schemat .lnx {SCHEMA_VERSION}"))
    if program.comment:
        head.append(_comment(program.comment))
    if program.stock is not None:
        head.append(format_stock_line(program.stock))
    head.append("G21" if program.units == "mm" else "G20")
    return "\n".join(head + body + ["M2"]) + "\n"


def compile_file(lnx_path: Path | str, ngc_path: Path | str | None = None,
                 registry: GeneratorRegistry | None = None,
                 tools: ToolLookup | None = None, safe_z: float | None = None) -> Path:
    """Kompiluje plik `.lnx` i zapisuje `.ngc` atomowo (domyślnie obok, z rozszerzeniem .ngc).

    Przy błędzie (LnxError albo CompileError) istniejący `.ngc` zostaje nietknięty.
    """
    lnx_path = Path(lnx_path)
    program = load_lnx(lnx_path)
    text = compile_program(program, registry, source=lnx_path.name, tools=tools,
                           safe_z=safe_z)
    target = Path(ngc_path) if ngc_path is not None else lnx_path.with_suffix(".ngc")
    return atomic_write(target, text)
