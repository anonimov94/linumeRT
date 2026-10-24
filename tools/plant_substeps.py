#!/usr/bin/env python3
"""plant_substeps: wynik atrapy Plant w funkcji `timing.substeps` (krótkie G0/G1 z bazowaniem).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24 (ustalenie sesji 049, raport docs/raporty/plant_substeps.md)

    PYTHONPATH=core:plant/server:simulation python3 tools/plant_substeps.py [n ...]

Dla każdej maszyny i programu wypisuje PASS/FAIL, maks. błąd nadążania XYZ [mm] i niespełnione
kryteria (ukończony, brak alarmu, 0 zgubionych kroków). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACHINES = {
    "mill_servo_table": "plant/scenarios/machines/mill_servo_table_y2.yaml",
    "router_gantry_steppers": "config/machines/router_gantry_steppers.yaml",
}
PROGRAMS = {
    "mill_servo_table": ["G0 Z-15", "G1 Z-15 F600", "G0 X100 Y80"],
    "router_gantry_steppers": ["G0 X10", "G0 X100", "G1 X100 F600", "G0 Y100"],
}


def main(argv: list[str] | None = None) -> int:
    from linumert_plant.scenario import Scenario, Step, run_mock

    counts = [int(a) for a in (argv if argv is not None else sys.argv[1:])] or [1, 2, 4, 8]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "probe.ngc"
        for machine, yaml_path in MACHINES.items():
            for program in PROGRAMS[machine]:
                for n in counts:
                    path.write_text(f"G90\nG0 Z-5\n{program}\nM2\n", encoding="utf-8")
                    scen = Scenario("plant_substeps", None, ROOT / yaml_path, duration=60,
                                    substeps=n, program=path,
                                    steps=[Step("enable", at=0), Step("home", at=0.01),
                                           Step("program", at=0.1)])
                    scen.expect = ([{"completed": True}, {"no_alarm": True}] +
                                   [{"lost_steps": {"axis": a, "max": 0}} for a in "XYZ"])
                    result = run_mock(scen)
                    fe = {a: round(v, 3) for a, v in result.ferr_max.items() if a in "XYZ"}
                    bad = "; ".join(f"{c.name}: {c.detail}" for c in result.criteria
                                    if not c.passed)
                    print(f"{machine:24s} {program:14s} n={n:3d} "
                          f"{'PASS' if result.passed else 'FAIL'} {fe} {bad}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
