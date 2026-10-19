"""Generatory podstawowe (sesja 040): nagłówek, koniec, wymiana narzędzia, planowanie.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

from linumert.generators.basic import FaceMill, Header, ProgramEnd, ToolChange, register
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.lexer import check

STOCK = ';@STOCK BOX X150 Y100 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 MAT="aluminium"'


def _gen(g, **p):
    values, issues = g.normalize(p)
    assert not issues and not g.check(values, 0), issues
    return g.generate(values)


def _ok(lines):
    assert check("\n".join(lines) + "\nM2\n") == []
    assert not any(w in " ".join(lines) for w in ("M98", "M99", "M30", "M2 "))


def test_header_and_end():
    lines = _gen(Header(), title="Wspornik", stock=STOCK, offset="G55")
    assert lines[:2] == ["( Wspornik )", STOCK] and "G55" in lines[2] and "G21" in lines[2]
    _ok(lines)
    assert [i.code for i in Header().validate({"stock": "BOX X1"})] == ["P-5015"]
    assert _gen(ProgramEnd()) == ["M5", "M9", "G53 G0 Z0"]
    assert _gen(ProgramEnd(), retract="z_home_xy", park_x=300)[-1] == "G53 G0 X300 Y0"


def test_tool_change():
    lines = _gen(ToolChange(), tool=3, rpm=8000, direction="M4", coolant="M8")
    assert lines == ["M5", "G53 G0 Z0", "T3 M6", "G43 H3", "S8000 M4", "M8", "G0 Z10"]
    _ok(lines)
    assert [i.code for i in ToolChange().validate({})] == ["P-5014"]


def test_face_mill_zigzag_and_layers():
    p = dict(x0=0, y0=0, x1=100, y1=50, depth=1.5, step_down=1, tool_d=50, stepover=60)
    lines = _gen(FaceMill(), **p)
    _ok(lines)
    plunges = [ln for ln in lines if ln.startswith("G1 Z")]
    assert [ln.split()[1] for ln in plunges] == ["Z-1", "Z-1.5"]
    passes = FaceMill()._passes(FaceMill().normalize(p)[0])
    assert passes[0][2] > passes[0][1] and passes[1][2] < passes[1][1]  # zygzak
    assert passes[-1][0] == 50 and passes[0][1] == -27  # wybieg 2 + promień 25
    one = _gen(FaceMill(), mode="one_way", **p)
    assert one.count("G1 Z-1 F200") == len(passes)


def test_face_mill_validation():
    codes = [i.code for i in FaceMill().validate(dict(x0=10, y0=0, x1=5, y1=50, depth=1,
                                                      tool_d=10, safe_z=-1))]
    assert codes == ["P-5003", "P-5003"]


def test_register_all():
    reg = GeneratorRegistry()
    register(reg)
    register(reg)
    assert {"header", "program_end", "tool_change", "face_mill"} <= set(reg.names())


def test_fmt_integer_keeps_zeros():
    from linumert.generators.base import fmt

    assert fmt(8000, 0) == "8000" and fmt(-0.0, 0) == "0" and fmt(1.2500) == "1.25"
