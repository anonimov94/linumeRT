"""Proces potomny `load_ngc`: awaria `gcode.parse` nie zabija procesu wywołującego.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-01

Wynik: plik `.npz`; kod `WORKER_PROGRAM_ERROR` = błąd programu (`run_parse_worker`).
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from linumert.programs.linuxcnc_check import WORKER_PROGRAM_ERROR, limit_worker_lifetime
from linumert.programs.toolpath import TOOL_SKIPPED_NOTE, parse_preview


def main(argv: list[str]) -> int:
    source, unitcode, initcode, target, timeout = argv
    limit_worker_lifetime(timeout)
    try:
        canon, skipped = parse_preview(Path(source), unitcode, initcode)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return WORKER_PROGRAM_ERROR
    moves = canon.moves
    notes = [*canon.notes, *([TOOL_SKIPPED_NOTE] if skipped else [])]
    np.savez(target,
             points=np.concatenate([m.points for m in moves]) if moves else np.zeros((0, 3)),
             sizes=np.array([len(m.points) for m in moves], dtype=np.int64),
             line=np.array([m.line for m in moves], dtype=np.int64),
             rapid=np.array([m.rapid for m in moves], dtype=bool),
             feed=np.array([m.feed for m in moves], dtype=float),
             offset=canon.g5x + canon.g92, notes=np.array(notes, dtype=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
