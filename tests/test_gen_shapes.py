# SPDX-License-Identifier: GPL-2.0-or-later
"""Parametric engraving and safe disconnected strokes. Model-Author: Codex."""
import json
import math

import pytest
from linumert.generators import shapes
from linumert.generators.path_geometry import PathTrace, decode_paths
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import compile_program
from linumert.programs.lnx import LnxProgram, Step, load_lnx, save_lnx


@pytest.mark.parametrize("shape", ["rectangle", "ellipse", "polygon", "star"])
@pytest.mark.parametrize("strategy", ["outline", "hatch", "crosshatch", "outline_hatch"])
def test_shape_strategies_are_finite_and_retract_between_paths(shape, strategy):
    gen = shapes.ShapeEngrave()
    v, issues = gen.normalize({"shape": shape, "strategy": strategy, "angle": 37,
                               "depth": 0.5, "step_down": 0.2})
    assert not issues and not gen.check(v, 0)
    assert all(math.isfinite(c) for path in gen.paths(v) for point in path for c in point)
    lines = gen.generate(v)
    for i, line in enumerate(lines):
        if line.startswith("G0 X"):
            assert lines[i - 1] == "G0 Z5"
            assert lines[i + 1].startswith("G1 Z")
    assert "G1 Z-0.5 F80" in lines and lines[-1] == "G0 Z5"


def test_hatch_does_not_connect_across_concave_voids():
    polygon = [(0, 0), (4, 0), (4, 4), (3, 4), (3, 1), (1, 1), (1, 4), (0, 4)]
    paths = shapes.hatch(polygon, 1)
    top = [p for p in paths if p[0][1] > 1]
    assert top and all(abs(p[0][0] - p[1][0]) == 1 for p in top)


@pytest.mark.parametrize("text", ["null", "[[[0,0],[NaN,1]]]", "[[[0,0],[0,0]]]",
                                 "[[[true,0],[1,1]]]", "[[[0,0],[1e100,1]]]"])
def test_imported_paths_reject_invalid_geometry(text):
    with pytest.raises(ValueError):
        decode_paths(text)


def test_shape_budget_and_roundtrip(tmp_path):
    gen = shapes.ShapeEngrave()
    assert gen.validate({"strategy": "hatch", "spacing": 0.001})
    assert gen.validate({"depth": 100, "step_down": 0.0001})
    registry = GeneratorRegistry()
    shapes.register(registry)
    paths = json.dumps([[[0, 0], [10, 0], [10, 10]]])
    program = LnxProgram(name="Ścieżki", steps=[Step(generator=PathTrace.name, version=1,
                                                    params={"paths": paths})])
    expected = compile_program(program, registry)
    save_lnx(program, tmp_path / "shape.lnx")
    assert compile_program(load_lnx(tmp_path / "shape.lnx"), registry) == expected
