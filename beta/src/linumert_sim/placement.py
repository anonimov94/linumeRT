"""Położenie przygotówki `;@STOCK` w układzie maszyny i odczyt układów detalu z pliku .var.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

ORIGIN mówi, gdzie na przygotówce leży zero układu detalu (OFFSET, np. G54). TOP = naddatek
na górze: wierzch materiału leży TOP mm nad zerem Z (dla ORIGIN=TOP_*), wysokość Z/H obejmuje
naddatek. Przygotówka jest ustawiana raz (przy wczytaniu programu albo ręcznie) i potem stoi —
jak prawdziwy materiał, który nie przesuwa się przy zmianie G54.
"""

from __future__ import annotations

from pathlib import Path

from .zmap import StockMap

# Parametry LinuxCNC: G54 = 5221…5223, kolejne układy co 20 (G59.3 = 5381)
OFFSET_INDEX = {"G54": 1, "G55": 2, "G56": 3, "G57": 4, "G58": 5, "G59": 6, "G59.1": 7,
                "G59.2": 8, "G59.3": 9}


def read_var_offsets(path: str | Path) -> dict[str, tuple[float, float, float]]:
    """Układy detalu G54…G59.3 (X, Y, Z) z pliku parametrów LinuxCNC."""
    values: dict[int, float] = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    try:
                        values[int(parts[0])] = float(parts[1])
                    except ValueError:
                        continue
    except OSError:
        return {}
    out = {}
    for name, n in OFFSET_INDEX.items():
        base = 5201 + 20 * n
        out[name] = tuple(values.get(base + i, 0.0) for i in range(3))
    return out


def find_stock_line(path: str | Path, max_lines: int = 200) -> str | None:
    """Pierwsza linia `;@STOCK` z nagłówka programu (pierwsze `max_lines` linii)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= max_lines:
                    break
                if line.strip().upper().startswith(";@STOCK"):
                    return line.strip()
    except OSError:
        return None
    return None


def stock_bounds(stock, origin_xyz) -> tuple[float, float, float, float, float, float]:
    """(x0, y0, x1, y1, z0, z1) przygotówki w układzie maszyny."""
    if stock.shape == "BOX":
        sx, sy, sz = stock.x, stock.y, stock.z
    else:
        sx = sy = stock.d
        sz = stock.h
    vert, horiz = stock.origin.split("_", 1)
    if horiz == "CENTER":
        x0, y0 = -sx / 2, -sy / 2
    else:
        front, side = horiz.split("_")
        x0 = 0.0 if side == "LEFT" else -sx
        y0 = 0.0 if front == "FRONT" else -sy
    if vert == "TOP":
        z1 = stock.top
        z0 = z1 - sz
    else:
        z0 = 0.0
        z1 = sz
    ox, oy, oz = origin_xyz
    return (ox + x0, oy + y0, ox + x0 + sx, oy + y0 + sy, oz + z0, oz + z1)


def place_stock(stock, origin_xyz, cell: float = 0.5) -> StockMap:
    x0, y0, x1, y1, z0, z1 = stock_bounds(stock, origin_xyz)
    return StockMap(stock.shape, x0, y0, x1, y1, z0, z1, cell)
