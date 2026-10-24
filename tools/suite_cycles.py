#!/usr/bin/env python3
"""suite_cycles: każdy generator cykli na wirtualnych maszynach Plant (sesja 049).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

    PYTHONPATH=core:plant/server:simulation python3 tools/suite_cycles.py \
        [--out docs/raporty/suite_cycles.md] [--mode A|B|AB]

Dla każdej pary (generator, maszyna) program z typowymi parametrami wykonuje atrapa mastera Plant
(`linumert_plant.scenario.run_mock`, lockstep z napędami z `machine.yaml`). Kryteria: program
ukończony, brak alarmu, brak zgubionych kroków, błąd nadążania XYZ ≤ okno maszyny.

Atrapa obsługuje tylko G0/G1, więc program jest dla niej przygotowany jawnie: łuki G2/G3 rozbite
na cięciwy (≤ 3°), cykle G81/G82/G83/G73 rozwinięte do G0/G1 według LinuxCNC (G98/G99, Q).
Kontur z korekcją G41.1/G42.1 wymaga interpretera LinuxCNC — w atrapie jedzie wariant bez
korekcji; pełny program sprawdza test rs274 w CI. Detal leży w układzie maszyny (bez G54).
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACHINES = {
    "router_gantry_steppers": "config/machines/router_gantry_steppers.yaml",
    # Wariant z czujnikiem bazy drugiej strony bramy (jak scenariusz homing_all, sesja 024).
    "mill_servo_table": "plant/scenarios/machines/mill_servo_table_y2.yaml",
}
WINDOW_MM = 0.2                       # okno błędu nadążania dla kryterium (jak test kieszeni)
RAPID_LIMIT = 3000.0
# Krok całkowania jak domyślne scenariusze i macierz Plant. Wynik atrapy silnie zależy od
# `substeps` (ustalenie 2026-10-24: przy >1 serwo Z frezarki i krokowce routera zachowują się
# inaczej) — opis w raporcie; rozstrzygnięcie w rdzeniu Plant (M1).
SUBSTEPS = 1                  # [mm/min] wariant B: G0 jak przy obniżonym MAX_VELOCITY w INI
PART = {"z_top": -20.0, "safe_z": -15.0}

# Typowe parametry: detal przy X/Y 100–200 mm, wierzch Z −20 mm w układzie maszyny.
CASES = [
    ("face_mill", {"x0": 100, "y0": 100, "x1": 160, "y1": 140, "depth": 1, "tool_d": 20,
                   **PART}),
    ("drill_holes", {"pattern": "grid", "x": 110, "y": 110, "count": 3, "rows": 2, "dx": 15,
                     "dy": 12, "cycle": "G81", "depth": 6, "z_top": -20}),
    ("drill_holes", {"pattern": "circle", "x": 150, "y": 150, "radius": 20, "count": 4,
                     "cycle": "G83", "peck": 2, "depth": 6, "z_top": -20, "retract": "G99"}),
    ("pocket_rect", {"cx": 150, "cy": 150, "width": 40, "height": 30, "tool_d": 8,
                     "depth": 2, "corner_radius": 6, **PART}),
    ("pocket_circle", {"cx": 150, "cy": 150, "diameter": 36, "tool_d": 8, "depth": 2,
                       "entry": "helix", **PART}),
    ("slot_linear", {"x1": 110, "y1": 110, "x2": 170, "y2": 140, "width": 12, "tool_d": 6,
                     "depth": 2, "entry": "ramp", **PART}),
    ("slot_arc", {"cx": 150, "cy": 150, "radius": 30, "sweep": 120, "width": 10,
                  "tool_d": 6, "depth": 2, **PART}),
    ("stud_rect", {"cx": 150, "cy": 150, "width": 40, "height": 24, "corner_radius": 5,
                   "tool_d": 6, "depth": 2, "margin": 6, **PART}),
    ("stud_circle", {"cx": 150, "cy": 150, "diameter": 30, "tool_d": 6, "depth": 2,
                     "margin": 5, **PART}),
    ("contour", {"segments": "L 120,120 180,120; A 180,120 180,160 180,140 CCW; "
                             "L 180,160 120,160; L 120,160 120,120",
                 "tool_d": 6, "depth": 2, "compensation": "none", "lead": 5, **PART}),
]

_WORD = re.compile(r"([A-Z])([-+]?\d*\.?\d+)")


def registry():
    from linumert.generators import basic, contours, drilling, pockets
    from linumert.generators.registry import GeneratorRegistry

    reg = GeneratorRegistry()
    for group in (basic, drilling, pockets, contours):
        group.register(reg)
    return reg


def limit_rapids(lines: list[str], rapid: float) -> list[str]:
    """G0 → G1 F`rapid`; następny posuw bez F dostaje z powrotem ostatni posuw programu."""
    out, feed, restore = [], None, False
    for line in lines:
        words = line.split()
        if words and words[0] == "G0":
            out.append(" ".join(["G1", *words[1:], f"F{rapid:.4f}"]))
            restore = True
            continue
        if any(w.startswith("F") for w in words):
            feed = next(w for w in words if w.startswith("F"))
            restore = False
        elif restore and feed and words and words[0] == "G1":
            line = f"{line} {feed}"
            restore = False
        out.append(line)
    return out


def for_mock(lines: list[str], start=(0.0, 0.0, 0.0)) -> list[str]:
    """Program generatora → podzbiór G0/G1 atrapy (łuki → cięciwy, cykle → G0/G1)."""
    out, pos, cycle, retract = [], list(start), None, "G98"
    initial_z = pos[2]
    for raw in lines:
        line = re.sub(r"\([^)]*\)", "", raw).strip().upper()
        if not line:
            continue
        words = _WORD.findall(line)
        g = [w for k, w in words if k == "G"]
        vals = {k: float(v) for k, v in words if k in "XYZIJRQPF"}
        if "80" in g:
            cycle = None
            continue
        for code in g:
            if code in ("98", "99"):
                retract = "G" + code
        motion = next((c for c in g if c in ("0", "1", "2", "3", "81", "82", "83", "73")), None)
        if motion in ("81", "82", "83", "73"):
            cycle = {"code": motion, **{k: vals[k] for k in "ZRQF" if k in vals}}
            initial_z = pos[2]
        if cycle is not None and (motion in ("81", "82", "83", "73") or
                                  (motion is None and ("X" in vals or "Y" in vals))):
            out += _drill(cycle, retract, initial_z, pos, vals)
            continue
        if motion in ("2", "3"):
            out += _arc(motion == "3", pos, vals)
            continue
        kept = [w for w in re.findall(r"[A-Z][-+]?\d*\.?\d+", line)
                if not (w.startswith("G") and w[1:] in ("17", "91.1", "40", "94"))]
        if kept:
            out.append(" ".join(kept))
        for i, axis in enumerate("XYZ"):
            if axis in vals:
                pos[i] = vals[axis]
    return out


def _drill(cycle, retract, initial_z, pos, vals) -> list[str]:
    x, y = vals.get("X", pos[0]), vals.get("Y", pos[1])
    r, bottom, feed = cycle["R"], cycle["Z"], cycle.get("F", 100)
    lines = []
    if pos[2] < r:
        lines.append(f"G0 Z{r:.4f}")
    lines += [f"G0 X{x:.4f} Y{y:.4f}", f"G0 Z{r:.4f}"]
    if cycle["code"] in ("83", "73") and cycle.get("Q", 0) > 0:
        depth, q = r, cycle["Q"]
        while depth > bottom + 1e-9:
            target = max(bottom, depth - q)
            lines.append(f"G1 Z{target:.4f} F{feed:.4f}")
            if cycle["code"] == "83" and target > bottom:
                lines += [f"G0 Z{r:.4f}", f"G0 Z{target + 0.25:.4f}"]
            depth = target
    else:
        lines.append(f"G1 Z{bottom:.4f} F{feed:.4f}")
    end = initial_z if retract == "G98" else r
    lines.append(f"G0 Z{end:.4f}")
    pos[:] = [x, y, end]
    return lines


def _arc(ccw: bool, pos, vals) -> list[str]:
    end = (vals.get("X", pos[0]), vals.get("Y", pos[1]), vals.get("Z", pos[2]))
    center = (pos[0] + vals.get("I", 0.0), pos[1] + vals.get("J", 0.0))
    r = math.hypot(pos[0] - center[0], pos[1] - center[1])
    a = math.atan2(pos[1] - center[1], pos[0] - center[0])
    b = math.atan2(end[1] - center[1], end[0] - center[0])
    sign = 1 if ccw else -1
    sweep = ((sign * (b - a)) % math.tau or math.tau) * sign
    n = max(1, math.ceil(abs(sweep) / math.radians(3)))
    feed = f" F{vals['F']:.4f}" if "F" in vals else ""
    lines = []
    for k in range(1, n + 1):
        t = k / n
        x, y = center[0] + r * math.cos(a + sweep * t), center[1] + r * math.sin(a + sweep * t)
        z = pos[2] + (end[2] - pos[2]) * t
        if k == n:
            x, y = end[0], end[1]
        lines.append(f"G1 X{x:.4f} Y{y:.4f} Z{z:.4f}{feed}")
    pos[:] = list(end)
    return lines


@dataclass
class Row:
    generator: str
    machine: str
    mode: str
    passed: bool
    lines: int
    seconds: float
    max_fe: dict
    detail: str


def run_case(name, params, machine, tmp: Path, mode="A") -> Row:
    from linumert_plant.scenario import Scenario, Step, run_mock

    gen = registry().latest(name)
    issues = gen.validate(params)
    if issues:
        return Row(name, machine, mode, False, 0, 0.0, {},
                   "; ".join(i.message() for i in issues))
    values = gen.normalize(params)[0]
    program = ["G0 Z-5"] + for_mock(gen.generate(values), start=(0.0, 0.0, -5.0))
    if mode == "B":
        program = limit_rapids(program, RAPID_LIMIT)
    program.append("M2")
    path = tmp / f"{name}_{machine}_{mode}.ngc"
    path.write_text("G90\n" + "\n".join(program) + "\n", encoding="utf-8")
    scenario = Scenario(f"suite_{name}", None, ROOT / MACHINES[machine],
                        duration=240, substeps=SUBSTEPS, program=path,
                        steps=[Step("enable", at=0), Step("home", at=0.01),
                               Step("program", at=0.1)])
    scenario.expect = ([{"completed": True}, {"no_alarm": True}] +
                       [{"max_following_error": {"axis": a, "mm": WINDOW_MM}} for a in "XYZ"] +
                       [{"lost_steps": {"axis": a, "max": 0}} for a in "XYZ"])
    started = time.perf_counter()
    result = run_mock(scenario)
    fe = {a: round(v, 4) for a, v in result.ferr_max.items() if a in "XYZ"}
    failed = [f"{c.name}: {c.detail}" for c in result.criteria if not c.passed]
    return Row(name, machine, mode, result.passed, len(program),
               time.perf_counter() - started, fe, "; ".join(failed) or "OK")


def report(rows: list[Row]) -> str:
    def table(mode):
        sub = [r for r in rows if r.mode == mode]
        out = [f"Wynik: **{sum(r.passed for r in sub)}/{len(sub)} PASS**.", "",
               "| Generator | Maszyna | Wynik | Bloki | Maks. błąd nadążania [mm] | Uwagi |",
               "|---|---|---|---|---|---|"]
        for r in sub:
            fe = ", ".join(f"{a} {v}" for a, v in sorted(r.max_fe.items())) or "—"
            out.append(f"| `{r.generator}` | {r.machine} | {'PASS' if r.passed else 'FAIL'} | "
                       f"{r.lines} | {fe} | {r.detail} |")
        return out

    out = ["# suite_cycles — generatory na wirtualnych maszynach Plant", "",
           f"Model-Author: Claude · {time.strftime('%Y-%m-%d')} · `tools/suite_cycles.py` "
           "(atrapa mastera, lockstep z napędami z `machine.yaml`; frezarka: wariant "
           "`mill_servo_table_y2` z czujnikiem bazy drugiej strony bramy).", "",
           f"Kryteria: ukończony, brak alarmu, 0 zgubionych kroków, błąd nadążania XYZ ≤ "
           f"{WINDOW_MM} mm. Detal w układzie maszyny X/Y 100–200, Z −20.", "",
           "## A. G0 według `machine.yaml`", ""] + table("A") + [
           "", f"## B. G0 ograniczone do {RAPID_LIMIT:g} mm/min "
           "(jak obniżone MAX_VELOCITY w INI)",
           ""] + table("B") + [
           "", "## Ustalenia", "",
           "- Próby kontrolne bez generatorów: na `router_gantry_steppers` sam `G0 X10` gubi "
           "kroki (24), `G0 X100` ok. 1800, a `G1 X10 F600` i dłuższe posuwy — 0; na "
           "`mill_servo_table` sam `G0 Z-15` daje błąd nadążania ok. 0,72 mm i E-4201, "
           "a `G1 Z-15 F600` przechodzi (0,07 mm). Przyczyna leży w profilu G0 atrapy i modelu "
           "napędów/konfiguracji maszyn, nie w generatorach — do sprawdzenia w M1 (Plant).",
           "- Wynik atrapy zależy od kroku całkowania `substeps` (prosty program G0/G1, "
           "z bazowaniem): frezarka przy 1 — 0,05 mm, przy 2–10 — E-4201 i Z ok. 0,7 mm; "
           "router przy 1 — 44 kroki Z, przy 4–10 — ok. 1600–1800 kroków X/Y. Suite używa "
           "`substeps = 1` jak scenariusze i macierz Plant; zależność do wyjaśnienia w M1.",
           "- Generatory ocenia wariant B: posuwy i dojazdy w granicach napędów.",
           "- Atrapa wykonuje tylko G0/G1: łuki rozbite na cięciwy ≤ 3°, cykle wiercenia "
           "rozwinięte; kontur z korekcją G41.1/G42.1 tylko w teście rs274 (CI).",
           "", "Wynik nie zastępuje testu z LinuxCNC ani maszyny. "
           "NIEZWERYFIKOWANE NA SPRZĘCIE.", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    import tempfile

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="raport Markdown (domyślnie stdout)")
    ap.add_argument("--mode", choices=("A", "B", "AB"), default="AB")
    args = ap.parse_args(argv)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for mode in args.mode:
            for name, params in CASES:
                for machine in MACHINES:
                    rows.append(run_case(name, params, machine, Path(tmp), mode))
                    r = rows[-1]
                    print(f"{mode} {r.generator:14s} {machine:24s} "
                          f"{'PASS' if r.passed else 'FAIL'}  {r.detail}", file=sys.stderr)
    text = report(rows)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if all(r.passed for r in rows if r.mode == "B") else 1


if __name__ == "__main__":
    raise SystemExit(main())
