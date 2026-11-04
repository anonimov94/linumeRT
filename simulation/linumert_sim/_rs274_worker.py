"""Proces potomny `parse_rs274`: awaria `gcode.parse` nie zabija procesu wywołującego.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-01

Słowa T/M6 i M61 Q są wycinane, bo numer narzędzia pochodzi z tekstu (`tool_changes`).
Nieobsługiwana analiza zmian narzędzi to błąd programu, bez przejścia na parser podzbioru.
Wynik: plik `.npz`; kod `WORKER_PROGRAM_ERROR` = błąd programu (`run_parse_worker`).
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from linumert.programs.linuxcnc_check import WORKER_PROGRAM_ERROR, limit_worker_lifetime
from linumert.programs.toolpath import strip_tool_words, tool_data_available

from linumert_sim.path import PathCanon, tool_changes


def main(argv: list[str]) -> int:
    source, unitcode, initcode, target, timeout = argv
    limit_worker_lifetime(timeout)
    import gcode  # type: ignore[import-not-found]

    path = Path(source)
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        changes, notes = tool_changes(text)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return WORKER_PROGRAM_ERROR
    stripped, _ = strip_tool_words(text, include_m61=True)
    tool_data_available()  # mapuje tablicę dla G43 Hn i G41 Dn, gdy LinuxCNC działa
    canon = PathCanon(tool_changes=changes)
    for note in notes:
        canon.out.note(note)
    # Zapisy parametrów interpretera zostają w analizie, z dala od stanu operatora
    # (jak load_ngc po poprawce N1 Codex, PR #123).
    with tempfile.TemporaryDirectory(prefix="linumert-path-") as directory:
        var = Path(directory) / "path.var"
        var.write_text("", encoding="utf-8")
        canon.parameter_file = str(var)
        parsed = Path(directory) / path.name
        parsed.write_text(stripped, encoding="utf-8")
        try:
            result, seq = gcode.parse(str(parsed), canon, unitcode, initcode)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return WORKER_PROGRAM_ERROR
    if result > gcode.MIN_ERROR:
        print(f"linia {seq}: {gcode.strerror(result)}", file=sys.stderr)
        return WORKER_PROGRAM_ERROR
    moves = canon.movelist()
    np.savez(target, start=moves.start, end=moves.end, line=moves.line, tool=moves.tool,
             kind=moves.kind, feed=moves.feed, spindle=moves.spindle,
             notes=np.array(moves.notes, dtype=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
