"""Generatory a baza narzędzi (sesja 040 p.2): typ, średnica, długość ostrza, obroty, kierunek.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import pytest

from linumert.generators import basic, drilling
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import CompileError, compile_program
from linumert.programs.lnx import parse_lnx
from linumert.tools.db import Tool, ToolDB

TOOLS = {
    1: Tool(1, 1, "flat", params={"d": 10.0, "l": 40.0, "flute_length": 20.0,
                                  "max_rpm": 12000.0, "hand": 1.0}),
    2: Tool(2, 2, "drill_118", params={"d": 6.8, "l": 60.0, "flute_length": 30.0}),
    3: Tool(3, 3, "tap", params={"d": 8.0, "l": 50.0, "pitch": 1.25}),
    4: Tool(4, 4, "face_mill", params={"d": 50.0, "h": 4.0}),
    5: Tool(5, 5, None, diameter=12.0),  # import z tool.tbl, bez typu
}

REGISTRY = GeneratorRegistry()
basic.register(REGISTRY)
drilling.register(REGISTRY)

FACE = {"x1": 100, "y1": 50, "depth": 2, "tool_d": 10, "step_down": 1}
DRILL = {"pattern": "single", "depth": 10, "cycle": "G81"}


def _program(*steps, units="mm"):
    return parse_lnx({"name": "t", "units": units, "steps": [
        {"generator": g, "version": 1, "params": p} for g, p in steps]})


def _codes(*steps, units="mm"):
    try:
        compile_program(_program(*steps, units=units), REGISTRY, tools=TOOLS.get)
    except CompileError as exc:
        return [(i.code, i.params.get("step")) for i in exc.issues]
    return []


def test_matching_tools_compile():
    assert _codes(("tool_change", {"tool": 1, "rpm": 8000}), ("face_mill", FACE),
                  ("tool_change", {"tool": 2}), ("drill_holes", DRILL)) == []


def test_without_lookup_nothing_is_checked():
    program = _program(("tool_change", {"tool": 99}), ("face_mill", {**FACE, "tool_d": 3}))
    assert "T99 M6" in compile_program(program, REGISTRY)


def test_unknown_tool():
    assert _codes(("tool_change", {"tool": 99}), ("face_mill", FACE)) == [("P-5206", None)]


def test_wrong_type_for_operation():
    assert _codes(("tool_change", {"tool": 2}), ("face_mill", {**FACE, "tool_d": 6.8})) == \
        [("P-5207", 2)]
    assert _codes(("tool_change", {"tool": 1}), ("drill_holes", DRILL)) == [("P-5207", 2)]


def test_diameter_and_cutting_length():
    codes = _codes(("tool_change", {"tool": 1}),
                   ("face_mill", {**FACE, "tool_d": 12, "depth": 30, "step_down": 25}))
    assert codes == [("P-5208", 2), ("P-5209", 2)]
    # głowica: wysokość H ogranicza przejście
    assert _codes(("tool_change", {"tool": 4}),
                  ("face_mill", {**FACE, "tool_d": 50, "step_down": 5, "depth": 5})) == \
        [("P-5209", 2)]
    assert _codes(("tool_change", {"tool": 2}), ("drill_holes", {**DRILL, "depth": 35})) == \
        [("P-5209", 2)]


def test_tapping_needs_tap_with_same_pitch():
    tap = {**DRILL, "cycle": "G33.1", "spindle_sync": True, "pitch": 1.25}
    assert _codes(("tool_change", {"tool": 3}), ("drill_holes", tap)) == []
    assert _codes(("tool_change", {"tool": 3}), ("drill_holes", {**tap, "pitch": 1.0})) == \
        [("P-5208", 2)]
    assert _codes(("tool_change", {"tool": 2}), ("drill_holes", tap)) == [("P-5207", 2)]


def test_spindle_limits_and_direction():
    assert _codes(("tool_change", {"tool": 1, "rpm": 15000})) == [("P-5210", 1)]
    assert _codes(("tool_change", {"tool": 1, "rpm": 5000, "direction": "M4"})) == \
        [("P-5211", 1)]


def test_untyped_tool_is_not_rejected():
    assert _codes(("tool_change", {"tool": 5}), ("face_mill", {**FACE, "tool_d": 12})) == []
    assert _codes(("tool_change", {"tool": 5}), ("face_mill", FACE)) == [("P-5208", 2)]


def test_inch_program_converted_to_mm():
    face = {**FACE, "x1": 4, "y1": 2, "depth": 0.08, "step_down": 0.04, "tool_d": 10 / 25.4}
    assert _codes(("tool_change", {"tool": 1}), ("face_mill", face), units="inch") == []
    assert _codes(("tool_change", {"tool": 1}), ("face_mill", {**face, "step_down": 1}),
                  units="inch")[-1] == ("P-5209", 2)


def test_messages_from_catalog():
    with pytest.raises(CompileError) as info:
        compile_program(_program(("tool_change", {"tool": 2}), ("face_mill", FACE)),
                        REGISTRY, tools=TOOLS.get)
    text = str(info.value)
    assert "T2" in text and "drill_118" in text and "{" not in text


def test_lookup_from_tool_db(tmp_path):
    db = ToolDB(tmp_path / "tools.sqlite")
    db.add(TOOLS[1])
    program = _program(("tool_change", {"tool": 1}), ("face_mill", FACE))
    assert "G43 H1" in compile_program(program, REGISTRY, tools=db.get)
