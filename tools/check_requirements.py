#!/usr/bin/env python3
"""Pokrycie wymagań REQ testami i scenariuszami (sesja 024, REQ-QA-01).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 024.

Źródła:
  wymagania   tabele `| REQ-XX-NN | ... |` w docs/wymagania/*.md (bez MACIERZ.md i README.md);
  sesje       kolumna „Sesja” w docs/wymagania/MACIERZ.md; wykonane sesje z prompts/DONE.md;
  pokrycie    znacznik `# REQ-XX-NN` w komentarzu testu Pythona (tests/), w komentarzu testu C
              (plant/core/tests/, hal/tests/) albo `requirements: [REQ-XX-NN]` w scenariuszu
              (plant/scenarios/*.yaml).
Wymaganie z co najmniej jedną wykonaną sesją musi mieć pokrycie — inaczej błąd (kod 1).
Wymagania z samymi przyszłymi sesjami są tylko wypisywane („planowane”).
`--write` uaktualnia kolumnę Status w MACIERZ.md: planowane → zaimplementowane (status
„zielone” zostaje). Bez `--write` nieaktualny status to tylko ostrzeżenie.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQ = re.compile(r"REQ-[A-Z]{2}-\d{2}")
ROW = re.compile(r"^\|\s*(REQ-[A-Z]{2}-\d{2})\s*\|")
DONE_LINE = re.compile(r"^(\d{3})\s*\|")
PY_MARK = re.compile(r"#.*?(REQ-[A-Z]{2}-\d{2}(?:[\s,;:]+REQ-[A-Z]{2}-\d{2})*)")


def requirements(root: Path) -> list[str]:
    ids: list[str] = []
    for path in sorted((root / "docs" / "wymagania").glob("*.md")):
        if path.name in ("MACIERZ.md", "README.md"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = ROW.match(line)
            if m and m.group(1) not in ids:
                ids.append(m.group(1))
    return ids


def matrix(root: Path) -> dict[str, tuple[list[str], str]]:
    """REQ → (sesje, status) z MACIERZ.md."""
    out = {}
    for line in (root / "docs" / "wymagania" / "MACIERZ.md").read_text(
            encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out[m.group(1)] = (re.findall(r"\d{3}", cells[1]), cells[-1])
    return out


def done_sessions(root: Path) -> set[str]:
    text = (root / "prompts" / "DONE.md").read_text(encoding="utf-8")
    return {m.group(1) for line in text.splitlines() if (m := DONE_LINE.match(line))}


def coverage(root: Path) -> dict[str, list[str]]:
    """REQ → lista miejsc pokrycia (`ścieżka:linia` albo `scenariusz`)."""
    found: dict[str, list[str]] = {}

    def add(req: str, where: str) -> None:
        found.setdefault(req, []).append(where)

    for path in sorted((root / "tests").rglob("*.py")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for group in PY_MARK.findall(line):
                for req in REQ.findall(group):
                    add(req, f"{path.relative_to(root)}:{n}")
    for base in (root / "plant" / "core" / "tests", root / "hal" / "tests"):
        for path in sorted(base.rglob("*.c")) if base.is_dir() else []:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "/*" in line or "//" in line or line.lstrip().startswith("*"):
                    for req in REQ.findall(line):
                        add(req, f"{path.relative_to(root)}:{n}")
    for path in sorted((root / "plant" / "scenarios").glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        for req in data.get("requirements") or [] if isinstance(data, dict) else []:
            add(str(req), f"scenariusz {path.stem}")
    return found


def check(root: Path, write: bool = False) -> tuple[list[str], list[str], list[str]]:
    """(błędy, ostrzeżenia, linie raportu)."""
    reqs = requirements(root)
    mat = matrix(root)
    done = done_sessions(root)
    cov = coverage(root)
    errors, warnings, lines = [], [], []
    for req in sorted(set(mat) - set(reqs)):
        errors.append(f"{req}: w MACIERZ.md, a nie ma go w docs/wymagania")
    statuses: dict[str, str] = {}
    for req in reqs:
        if req not in mat:
            errors.append(f"{req}: brak wiersza w docs/wymagania/MACIERZ.md")
            continue
        sessions, status = mat[req]
        required = any(s in done for s in sessions)
        places = cov.get(req, [])
        if required and not places:
            errors.append(f"{req}: sesje {', '.join(sessions)} wykonane, brak testu ze znacznikiem "
                          f"# {req} ani scenariusza z requirements: [{req}]")
        want = status if status == "zielone" and places else (
            "zaimplementowane" if places and required else "planowane")
        statuses[req] = want
        if want != status:
            warnings.append(f"{req}: status w MACIERZ.md „{status}”, powinien być „{want}”")
        lines.append(f"{req:10} {'OK ' if places else ('BRAK' if required else 'plan')} "
                     f"{len(places):3} miejsc  sesje {','.join(sessions)}")
    for req in sorted(set(cov) - set(reqs)):
        errors.append(f"{req}: znacznik w {cov[req][0]}, ale nie ma takiego wymagania")
    if write and not errors:
        path = root / "docs" / "wymagania" / "MACIERZ.md"
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            m = ROW.match(line)
            if m and m.group(1) in statuses:
                cells = line.rstrip().rstrip("|").split("|")
                cells[-1] = f" {statuses[m.group(1)]} "
                line = "|".join(cells) + "|"
            out.append(line)
        path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
        warnings = []
    return errors, warnings, lines


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pokrycie wymagań REQ (REQ-QA-01)")
    p.add_argument("--write", action="store_true", help="uaktualnij Status w MACIERZ.md")
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    errors, warnings, lines = check(args.root, args.write)
    if args.verbose:
        print("\n".join(lines))
    for w in warnings:
        print(f"uwaga: {w}")
    for e in errors:
        print(f"BŁĄD: {e}", file=sys.stderr)
    covered = sum(1 for x in lines if " OK " in x)
    print(f"check_requirements: {len(lines)} wymagań, pokryte {covered}, błędy {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
