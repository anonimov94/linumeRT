#!/usr/bin/env python3
"""Przygotówka `;@STOCK` → cel sondy Plant w machine.yaml (sesja 054 p.2).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-20.

Sonda w Plant (`probe.target`, układ maszyny) ma trafiać w ten sam materiał, który widzi
symulacja HMI. Położenie liczone jak w symulacji (`linumert_sim.placement.stock_bounds`):
zero układu detalu (OFFSET z linii `;@STOCK`) z pliku parametrów LinuxCNC (.var) albo podane
wprost. Walec (CYL) jest zapisywany jako prostopadłościan opisany — cel sondy Plant ma tylko
typ `box` i `plate`.

    python tools/stock_probe.py config/machines/mill_servo_table.yaml \\
        --ngc ~/linuxcnc/nc_files/detal.ngc --var ~/linuxcnc/configs/mill/linumert.var
    python tools/stock_probe.py machine.yaml --stock ";@STOCK BOX X100 Y80 Z20" \\
        --origin 300 400 -90 --write

Bez `--write` drukuje tylko nowy cel. `--write` zmienia wyłącznie linię `target:` w sekcji
`probe:` (zapis atomowy, komentarze zostają). Kod wyjścia: 0 = OK, 2 = błąd danych.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("core", "simulation"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

from linumert.programs.stock import StockError, parse_stock_line  # noqa: E402
from linumert_sim.placement import (  # noqa: E402
    find_stock_line,
    read_var_offsets,
    stock_bounds,
)

_TARGET = re.compile(r"^(?P<indent>[ \t]+)target:.*$", re.MULTILINE)


def _num(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def probe_target(stock, origin_xyz) -> str:
    """Cel sondy (styl przepływowy YAML) dla przygotówki w układzie maszyny."""
    x0, y0, x1, y1, z0, z1 = stock_bounds(stock, origin_xyz)
    lo = ", ".join(_num(v) for v in (x0, y0, z0))
    hi = ", ".join(_num(v) for v in (x1, y1, z1))
    return f"{{type: box, min: [{lo}], max: [{hi}]}}"


def replace_target(text: str, target: str) -> str:
    """Podmiana linii `target:` w sekcji `probe:` (ValueError, gdy sekcji brak)."""
    match = re.search(r"^probe:[ \t]*\n((?:[ \t]+.*\n?|[ \t]*\n)*)", text, re.MULTILINE)
    if match is None:
        raise ValueError("machine.yaml nie ma sekcji probe:")
    block = match.group(1)
    found = _TARGET.search(block)
    if found is None:
        raise ValueError("sekcja probe: nie ma linii target:")
    new_block = block[:found.start()] + f"{found.group('indent')}target: {target}" + \
        block[found.end():]
    return text[:match.start(1)] + new_block + text[match.end(1):]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("machine", type=Path, help="machine.yaml z sekcją probe:")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--stock", help="linia ;@STOCK")
    src.add_argument("--ngc", type=Path, help="program z linią ;@STOCK w nagłówku")
    pos = ap.add_mutually_exclusive_group(required=True)
    pos.add_argument("--var", type=Path, help="plik parametrów LinuxCNC (układy G54…G59.3)")
    pos.add_argument("--origin", type=float, nargs=3, metavar=("X", "Y", "Z"),
                     help="zero układu detalu w układzie maszyny [mm]")
    ap.add_argument("--write", action="store_true", help="zapisz cel do machine.yaml")
    args = ap.parse_args(argv)

    line = args.stock or find_stock_line(args.ngc)
    if not line:
        print(f"błąd: brak linii ;@STOCK w {args.ngc}", file=sys.stderr)
        return 2
    try:
        stock = parse_stock_line(line)
    except StockError as exc:
        print(f"błąd: {exc}", file=sys.stderr)
        return 2
    if args.origin is not None:
        origin = tuple(args.origin)
    else:
        offsets = read_var_offsets(args.var)
        if not offsets:
            print(f"błąd: nie można odczytać {args.var}", file=sys.stderr)
            return 2
        origin = offsets[stock.offset]
    target = probe_target(stock, origin)
    print(target)
    if not args.write:
        return 0
    try:
        text = replace_target(args.machine.read_text(encoding="utf-8"), target)
    except (OSError, ValueError) as exc:
        print(f"błąd: {exc}", file=sys.stderr)
        return 2
    tmp = args.machine.with_name(args.machine.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(args.machine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
