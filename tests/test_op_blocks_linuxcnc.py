# SPDX-License-Identifier: GPL-2.0-or-later
"""Bloki O operacji (`oN if [1]`) z kompilatora `.lnx` na LinuxCNC 2.9 + Plant.

Model-Author: Claude · 2026-11-05. Każda operacja ma własny numer O (polecenie właściciela).
Sprawdzamy, że task LinuxCNC wykonuje taki program w AUTO w całości oraz od linii wewnątrz
bloku operacji (start od linii w WebHMI: `cmd.auto(AUTO_RUN, linia)`): wtedy wierci tylko
otwór operacji 3, bez błędu „endif bez if”. Wymaga LinuxCNC RIP. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from linumert.generators import basic, drilling
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import compile_program
from linumert.programs.lnx import LnxProgram, Step
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
pytestmark = pytest.mark.linuxcnc
HOLES = {2: (10, 10), 3: (30, 10)}  # krok -> otwór (X, Y) w G54

DRIVER = r"""
import tempfile
from pathlib import Path
out = {"on": on, "homed": homed}
mdi("G21 G90 G94 G49 G54 G10 L2 P1 X300 Y400 Z-20 R0")  # G54 nad wolnym obszarem stołu
mdi("G53 G0 Z-5")
ngc = Path(tempfile.mkdtemp()) / "operacje.ngc"
ngc.write_text(@TEXT@, encoding="utf-8")
errors = linuxcnc.error_channel()
def drain():
    found = []
    while True:
        item = errors.poll()
        if not item:
            return found
        found.append(item[1])
def run(line):
    drain()
    c.mode(linuxcnc.MODE_AUTO); c.wait_complete()
    c.program_open(str(ngc)); c.wait_complete()
    c.auto(linuxcnc.AUTO_RUN, line)
    started = wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 30)
    low = set()
    def finished():
        p = s.actual_position
        if p[2] < -20.5:  # poniżej G54 Z-0,5: wiercenie
            low.add((round(p[0] - 300), round(p[1] - 400)))
        return s.interp_state == linuxcnc.INTERP_IDLE
    done = wait(finished, 180)
    return {"started": started, "done": done, "holes": sorted(low), "errors": drain(),
            "task": s.task_state}
out["full"] = run(0)
out["from_op3"] = run(@LINE@)
print("RESULT " + json.dumps(out), flush=True)
"""


def _program() -> str:
    registry = GeneratorRegistry()
    basic.register(registry)
    drilling.register(registry)
    steps = [Step(generator="header", version=1, params={})]
    steps += [Step(generator="drill_holes", version=1,
                   params={"x": x, "y": y, "depth": 2, "feed": 300}) for x, y in HOLES.values()]
    steps.append(Step(generator="program_end", version=1, params={}))
    return compile_program(LnxProgram(name="operacje", steps=steps), registry, safe_z=-5.0)


def test_program_text_has_unique_operation_blocks():  # REQ-QA-03
    lines = _program().splitlines()
    opened = [line for line in lines if line.endswith(" if [1]")]
    assert opened == ["o100 if [1]", "o200 if [1]", "o300 if [1]", "o400 if [1]"]
    assert all(lines.count(o.replace(" if [1]", " endif")) == 1 for o in opened)


def test_operation_blocks_run_in_auto_and_from_line_inside_block(tmp_path):  # REQ-QA-02
    text = _program()
    lines = text.splitlines()
    start = lines.index("o300 if [1]") + 2  # pierwsza linia wewnątrz bloku operacji 3 (od 1)
    driver = DRIVER.replace("@TEXT@", json.dumps(text)).replace("@LINE@", str(start))
    result, log, _ = run_generated_plant(tmp_path, MILL, driver, port=47857, timeout=420)
    assert result["on"] and result["homed"], result
    full, part = result["full"], result["from_op3"]
    assert full["started"] and full["done"] and full["errors"] == [], (full, log[-2000:])
    assert full["holes"] == sorted([list(h) for h in HOLES.values()]), full
    assert part["started"] and part["done"] and part["errors"] == [], (part, log[-2000:])
    assert part["holes"] == [list(HOLES[3])], part  # tylko operacja 3
    assert full["task"] == part["task"] == 4, result  # STATE_ON
