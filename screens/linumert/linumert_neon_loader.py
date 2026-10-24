# SPDX-License-Identifier: GPL-2.0-or-later
"""Classic × Neon: wczytanie programu przez interpreter LinuxCNC w osobnym procesie.

Model-Author: Claude · 2026-10-24. Monitor skórek uruchamia ten moduł jako jednorazowy proces
(`python linumert_neon_loader.py plik.ngc`), żeby `gcode.parse` nie blokował wątku GUI; wynik
to JSON na stdout. Bez komend LinuxCNC, pinów HAL i sygnału życia. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import json
import sys
from pathlib import Path

MAX_OUTPUT = 64 * 1024 * 1024
TIMEOUT_S = 20.0


def toolpath_to_json(toolpath):
    return json.dumps({
        "version": 1,
        "moves": [[m.line, m.rapid, m.feed, m.points.round(4).tolist()] for m in toolpath.moves],
        "offset": [float(v) for v in toolpath.offset],
        "notes": list(toolpath.notes),
    }, allow_nan=False, separators=(",", ":"))


def toolpath_from_json(payload, source=()):
    """Odtworzenie ścieżki z wyjścia procesu; nieprawidłowe dane = ValueError."""
    from linumert.programs.toolpath import Toolpath, make_move

    if len(payload) > MAX_OUTPUT:
        raise ValueError("Ścieżka programu przekracza limit podglądu.")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Nieprawidłowa odpowiedź procesu wczytującego.")
    if "error" in data:
        raise ValueError(str(data["error"])[:500])
    if data.get("version") != 1 or not isinstance(data.get("moves"), list):
        raise ValueError("Nieobsługiwana wersja ścieżki.")
    moves = []
    for item in data["moves"]:
        if not (isinstance(item, list) and len(item) == 4):
            raise ValueError("Nieprawidłowy ruch w ścieżce.")
        line, rapid, feed, points = item
        if type(line) is not int or type(rapid) is not bool or not isinstance(points, list):
            raise ValueError("Nieprawidłowy ruch w ścieżce.")
        moves.append(make_move(line, rapid, float(feed), points))
    offset = data.get("offset", [0, 0, 0])
    notes = [str(n) for n in data.get("notes", [])]
    return Toolpath(moves, source, offset, notes)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / "core")]
    from linumert.programs.linuxcnc_check import InterpreterUnavailable
    from linumert.programs.toolpath import load_ngc

    if len(argv) != 1:
        print(json.dumps({"error": "Użycie: linumert_neon_loader.py program.ngc"}))
        return 2
    try:
        toolpath = load_ngc(argv[0])
    except (InterpreterUnavailable, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(toolpath_to_json(toolpath))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
