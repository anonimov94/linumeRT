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
    ...linie generatora...
    ( krok 2 pominiety: ... )                (krok wyłączony)
    M2

Błąd walidacji dowolnego kroku blokuje cały wynik (`CompileError` z listą Issue) — nic nie
jest zapisywane. Kompilator sprawdza też wynik generatora: linia bez znaku nowej linii,
nawiasy komentarzy zamknięte, brak M98/M99 (podprogramy LinuxCNC: `o<nazwa> call`, §8)
i brak M2/M30 (koniec programu dopisuje kompilator).
"""

from __future__ import annotations

import re
from pathlib import Path

from linumert.generators.base import Issue
from linumert.generators.registry import DEFAULT_REGISTRY, GeneratorRegistry
from linumert.generators.tooling import ToolLookup, check_steps

from .lnx import SCHEMA_VERSION, LnxProgram, atomic_write, load_lnx
from .stock import format_stock_line

_FORBIDDEN = re.compile(r"(?<![A-Z0-9.#])M0*(98|99|2|30)(?![0-9.])", re.IGNORECASE)
_COMMENT = re.compile(r"\([^()]*\)")


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


def compile_program(program: LnxProgram, registry: GeneratorRegistry | None = None,
                    source: str | None = None, tools: ToolLookup | None = None) -> str:
    """Program → tekst `.ngc` (CompileError przy dowolnym błędzie).

    `tools` (np. `ToolDB.get`): kroki sprawdzane dodatkowo z bazą narzędzi (P-5206…P-5211).
    """
    registry = registry or DEFAULT_REGISTRY
    issues: list[Issue] = []
    body: list[str] = []
    checked: list[tuple[int, str, dict]] = []
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
        problems = _check_output(lines, number)
        if problems:
            issues += problems
            continue
        body.append(_comment(label))
        body += lines
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
                 tools: ToolLookup | None = None) -> Path:
    """Kompiluje plik `.lnx` i zapisuje `.ngc` atomowo (domyślnie obok, z rozszerzeniem .ngc).

    Przy błędzie (LnxError albo CompileError) istniejący `.ngc` zostaje nietknięty.
    """
    lnx_path = Path(lnx_path)
    program = load_lnx(lnx_path)
    text = compile_program(program, registry, source=lnx_path.name, tools=tools)
    target = Path(ngc_path) if ngc_path is not None else lnx_path.with_suffix(".ngc")
    return atomic_write(target, text)
