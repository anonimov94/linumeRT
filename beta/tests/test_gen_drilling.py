"""Generator otworów (sesja 042): wzory pozycji, cykle, walidacja, składnia G-code.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import math

import pytest

from linumert.generators.drilling import DrillHoles, parse_points, pattern_points
from linumert.programs.lexer import check

G = DrillHoles()


def _v(**p):
    values, issues = G.normalize({"depth": 10, **p})
    assert not issues, issues
    return values


def test_patterns():
    assert pattern_points(_v(x=5, y=6)) == [(5, 6)]
    assert pattern_points(_v(pattern="list", points="1,2; 3.5,-4")) == [(1, 2), (3.5, -4)]
    assert pattern_points(_v(pattern="row", count=3, dx=10)) == [(0, 0), (10, 0), (20, 0)]
    grid = pattern_points(_v(pattern="grid", count=3, rows=2, dx=5, dy=7))
    assert len(grid) == 6 and grid[-1] == (10, 7)
    circ = pattern_points(_v(pattern="circle", count=4, radius=10))
    assert [tuple(round(c, 6) for c in p) for p in circ] == [(10, 0), (0, 10), (-10, 0),
                                                              (0, -10)]
    arc = pattern_points(_v(pattern="arc", count=3, radius=10, angle=0, sweep=90))
    assert arc[-1][0] == pytest.approx(0, abs=1e-9) and arc[-1][1] == pytest.approx(10)
    assert math.dist(arc[0], arc[1]) == pytest.approx(math.dist(arc[1], arc[2]))


def test_parse_points_errors():
    with pytest.raises(ValueError, match="pozycja 2"):
        parse_points("1,2; x,3")


@pytest.mark.parametrize("cycle,word", [("G81", None), ("G82", "P"), ("G83", "Q"), ("G73", "Q")])
def test_cycles(cycle, word):
    lines = G.generate(_v(pattern="row", count=3, dx=10, cycle=cycle, z_top=0, depth=12))
    call = next(line for line in lines if line.startswith(("G98", "G99")))
    assert call.startswith("G98 " + cycle) and "Z-12" in call and "R2" in call
    if word:
        assert f" {word}" in call
    assert lines[-1] == "G80" and lines[-3:-1] == ["X10 Y0", "X20 Y0"]
    assert check("\n".join(lines) + "\nM2\n") == []  # składnia


def test_rigid_tap_requires_sync():
    issues = G.validate({"depth": 10, "cycle": "G33.1"})
    assert [i.code for i in issues] == ["P-5007"]
    lines = G.generate(_v(cycle="G33.1", spindle_sync=True, pitch=1.25, depth=8))
    assert "G33.1 Z-8 K1.25" in lines


def test_validation_rules():
    codes = lambda **p: [i.code for i in G.validate({"depth": 5, **p})]  # noqa: E731
    assert codes(pattern="list", points="") == ["P-5014"]
    assert codes(pattern="list", points="1;2") == ["P-5015"]
    assert codes(pattern="circle", count=1) == ["P-5003"]
    assert codes(cycle="G83", peck=6) == ["P-5003"]
    assert codes(depth=0) == ["P-5003"]


def test_preview_crosses():
    assert len(G.preview_2d(_v(pattern="grid", count=2, rows=2))) == 8


def test_compiles_as_program():
    from linumert.generators import drilling
    from linumert.generators.registry import GeneratorRegistry

    reg = GeneratorRegistry()
    drilling.register(reg)
    drilling.register(reg)  # bez dublowania
    text = G.generate_ngc({"depth": 5, "pattern": "grid", "count": 2, "rows": 2}, "otwory")
    assert "G98 G81" in text and check(text) == []
