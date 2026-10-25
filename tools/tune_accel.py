#!/usr/bin/env python3
"""Dobór przyspieszeń osi na Plant z budżetu uchybu nadążania (M1).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-25.

    PYTHONPATH=core:plant/server python3 tools/tune_accel.py \\
        plant/scenarios/machines/mill_servo_table_y2.yaml --budget 0.2 --out raport.md

Bez `--write` tylko raportuje; z `--write` wpisuje zalecane `max_acceleration` do pliku.
Opis metody: plant/server/linumert_plant/accel_tuning.py. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("core", "plant/server"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

from linumert_plant.accel_tuning import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
