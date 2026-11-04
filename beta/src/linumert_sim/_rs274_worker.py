"""Proces potomny `gcode.parse`: awaria interpretera nie zabija procesu wywołującego.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-01

Bez zmapowanej tablicy narzędzi LinuxCNC 2.9 kończy `gcode.parse` sygnałem SIGSEGV przy m.in.
`T`, `M6`, `G43 Hn`, `G41 Dn`, `G10 L1`, `M61`, a pętla w programie nie ma końca
(`check_abort` nie ma czego sprawdzać). Wynik: plik `.npz`; kod 3 = błąd programu.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

import numpy as np

from linumert_sim.path import WORKER_PROGRAM_ERROR, PathCanon, tool_changes

_COMMENT = re.compile(r"\([^)]*\)|;.*$")
_TOOL_WORDS = re.compile(
    r"(?<![A-Za-z0-9.])(?:[Tt]\s*(?:\d+|#<[^>]*>|#\d+|\[[^\]]*\])|[Mm]\s*0*6(?!\d))")


def tool_data_available() -> bool:
    """Czy LinuxCNC utworzył ~/.tool.mmap; poll() mapuje tablicę dla G43 Hn i G41 Dn."""
    if not (Path(os.environ.get("HOME", "/tmp")) / ".tool.mmap").exists():
        return False
    try:
        import linuxcnc  # type: ignore[import-not-found]

        linuxcnc.stat().poll()
    except Exception:  # noqa: BLE001 - brak NML/modułu = brak danych narzędzi
        return False
    return True


def strip_tool_words(text: str) -> str:
    """Wycina słowa T i M6 poza komentarzami; numeracja linii bez zmian."""
    out = []
    for line in text.splitlines(keepends=True):
        parts, last = [], 0
        for m in _COMMENT.finditer(line):
            parts.append(_TOOL_WORDS.sub("", line[last:m.start()]))
            parts.append(m.group(0))
            last = m.end()
        parts.append(_TOOL_WORDS.sub("", line[last:]))
        out.append("".join(parts))
    return "".join(out)


def main(argv: list[str]) -> int:
    source, unitcode, initcode, target = argv
    import gcode  # type: ignore[import-not-found]

    path = Path(source)
    text = path.read_text(encoding="utf-8", errors="replace")
    changes, notes = tool_changes(text)
    stripped = strip_tool_words(text)
    tool_data_available()  # mapuje tablicę dla G43 Hn i G41 Dn, gdy LinuxCNC działa
    canon = PathCanon(tool_changes=changes)
    for note in notes:
        canon.out.note(note)
    with tempfile.TemporaryDirectory(prefix="linumert-path-") as directory:
        var = Path(directory) / "path.var"
        var.write_text("", encoding="utf-8")
        canon.parameter_file = str(var)
        parsed = Path(directory) / path.name
        parsed.write_text(stripped, encoding="utf-8")
        result, seq = gcode.parse(str(parsed), canon, unitcode, initcode)
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
