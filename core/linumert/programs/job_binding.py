"""Read-only comparison of frozen job assumptions with a LinuxCNC observation.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex. No controller commands or motion authorization.
"""

import math
from pathlib import Path

from linumert.tools.tbl import OFFSET_AXES, parse_tbl

from .job import OFFSETS

EPS = 1e-6
SETTLED_MM = .001


def _close(a, b, tolerance=EPS):
    return (not isinstance(a, bool) and isinstance(a, (int, float)) and math.isfinite(a)
            and abs(a - b) <= tolerance)


def _vector(a, b):
    return (isinstance(a, (list, tuple)) and len(a) == len(b)
            and all(_close(x, y) for x, y in zip(a, b, strict=True)))


def _path(actual, expected):
    return isinstance(actual, str) and bool(actual) and Path(actual).resolve() == expected.resolve()


def same_context(a, b):
    """Compare a paused receipt without rounding its coordinates for display."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(b) and _close(a, b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_context(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same_context(x, y) for x, y in zip(a, b, strict=True))
    return type(a) is type(b) and a == b


def _tools(text, actual):
    if not isinstance(actual, list):
        return False
    expected = {e.number: {"offsets": [e.values.get(a, 0) for a in OFFSET_AXES],
                "diameter": e.values.get("D", 0), "frontangle": e.values.get("I", 0),
                "backangle": e.values.get("J", 0), "orientation": e.orientation or 0}
                for e in parse_tbl(text) if e.number > 0}
    found = set()
    for row in actual:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            return False
        number = row["id"]
        if number <= 0:
            continue
        wanted = expected.get(number)
        if wanted is None or not _vector(row.get("offsets"), wanted["offsets"]):
            return False
        if any(not _close(row.get(key), wanted[key])
               for key in ("diameter", "frontangle", "backangle", "orientation")):
            return False
        found.add(number)
    return found == set(expected)


def inspect(snapshot, live, *, ini, program, table, setup, start):
    """Pose fields use snapshot's NML poll; tooldata/HAL reads are subsequent.

    Actual positioning must be strictly below0.001mm. Commanded geometry and setup
    retain the calculation tolerance1e-6mm. Missing observations never pass.
    Static file identity and controller ownership are separate mandatory checks.
    """
    live = live or {}
    checks = {}

    def add(key, condition, reason, *, missing=False):
        checks[key] = {"status": "unavailable" if missing else "passed" if condition else "failed",
                       "reason": reason}

    add("controller", _path(live.get("ini"), Path(ini)), "Wymagana konfiguracja tej instancji",
        missing=live.get("ini") is None)
    add("program", _path(snapshot.program_file, Path(program)), "Wczytaj program tego zadania")
    add("units", _close(live.get("linear_units"), 1), "Jednostki maszyny muszą być milimetrami",
        missing=live.get("linear_units") is None)
    add("tool_table", _tools(table, live.get("tool_table")),
        "Załadowana tabela narzędzi musi odpowiadać zadaniu",
        missing=live.get("tool_table") is None)
    ready = (snapshot.task_state.value == "on" and snapshot.mode.value == "auto"
             and snapshot.interp_state.value == "idle" and snapshot.all_homed
             and not snapshot.errors and not any(a.limit_hit for a in snapshot.axes)
             and live.get("inpos") is True and _close(live.get("current_vel"), 0, 1e-4))
    add("machine_ready", ready, "Wymagane ON, AUTO, bazowanie i zatrzymany ruch")
    axes = {a.name: a for a in snapshot.axes}
    positioned = len(snapshot.axes) == 3 and set(axes) == set("XYZ") and all(
        _close(axes[a].commanded, wanted)
        and not isinstance(axes[a].position, bool)
        and isinstance(axes[a].position, (int, float)) and math.isfinite(axes[a].position)
        and abs(axes[a].position - wanted) < SETTLED_MM
        for a, wanted in zip("XYZ", start, strict=True))
    add("start_position", positioned,
        "Ustaw początkowe położenie nosa wrzeciona zgodne z weryfikacją [mm]: "
        + ", ".join(f"{a} {v:.4f}" for a, v in zip("XYZ", start, strict=True)))
    add("initial_tool", snapshot.tool_number == 0 and _vector(live.get("tool_offset"), [0] * 9),
        "Początek wymaga T0 i zerowej korekcji narzędzia",
        missing=live.get("tool_offset") is None)
    offset = [*setup["origin_mm"], *([0] * 6)]
    setup_ok = (live.get("g5x_index") == OFFSETS.index(setup["offset"]) + 1
                and _vector(live.get("g5x_offset"), offset)
                and _vector(live.get("g92_offset"), [0] * 9)
                and _close(live.get("rotation_xy"), 0))
    add("work_setup", setup_ok, "Wymagany układ detalu zadania, G92=0 i obrót XY=0",
        missing=any(live.get(k) is None for k in
                    ("g5x_index", "g5x_offset", "g92_offset", "rotation_xy")))
    return checks
