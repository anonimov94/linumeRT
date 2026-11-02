# SPDX-License-Identifier: GPL-2.0-or-later
"""Facing coverage and version stability. Model-Author: Codex."""
import math

import pytest

from linumert.generators import basic, surfacing
from linumert.generators.registry import GeneratorRegistry


def distance_to_segment(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


@pytest.mark.parametrize("axis", ["X", "Y"])
@pytest.mark.parametrize("mode", ["zigzag", "one_way", "crosshatch", "concentric"])
def test_facing_strategies_are_bounded_and_retract(axis, mode):
    gen = surfacing.FaceMillStrategies()
    v, issues = gen.normalize({"x1": 40, "y1": 20, "tool_d": 8, "depth": 2,
                               "step_down": 0.7, "axis": axis, "mode": mode})
    assert not issues and not gen.check(v, 0)
    paths = gen.preview_2d(v)
    assert all(math.isfinite(n) for path in paths for p in path for n in p)
    lines = gen.generate(v)
    assert "G1 Z-2 F200" in lines and lines[-1] == "G0 Z5"
    for i, line in enumerate(lines):
        if line.startswith("G0 X"):
            assert lines[i - 1] == "G0 Z5"
    if mode == "crosshatch":
        assert len(paths) == 2
    elif mode == "concentric":
        assert paths[0][0] == paths[0][-1]
    elif mode == "one_way":
        assert len(paths) > 1
    segments = [(a, b) for path in paths for a, b in zip(path[:-1], path[1:], strict=True)]
    for x in range(0, 41, 2):
        for y in range(0, 21, 2):
            assert min(distance_to_segment(x, y, a, b) for a, b in segments) <= \
                v["tool_d"] / 2 + 1e-9


def test_concentric_exact_square_leaves_no_central_island():
    gen = surfacing.FaceMillStrategies()
    v, issues = gen.normalize({"x1": 40, "y1": 40, "tool_d": 8, "depth": 1,
                               "mode": "concentric", "stepover": 75, "overrun": 0})
    assert not issues and not gen.check(v, 0)
    segments = [(a, b) for path in gen.paths(v)
                for a, b in zip(path[:-1], path[1:], strict=True)]
    for x, y in ((20, 20), (19, 21), (21, 19), (20, 22)):
        assert min(distance_to_segment(x, y, a, b) for a, b in segments) <= 4


def test_v1_is_preserved_and_small_step_is_refused_before_allocation():
    registry = GeneratorRegistry()
    basic.register(registry)
    old = registry.get("face_mill", 1)
    v, _ = old.normalize({"x1": 40, "y1": 20, "tool_d": 8, "depth": 1})
    expected = old.generate(v)
    surfacing.register(registry)
    assert registry.get("face_mill", 1).generate(v) == expected
    assert registry.latest("face_mill").version == 2
    assert registry.latest("face_mill").validate(
        {"x1": 10000, "y1": 10000, "tool_d": 0.0001, "depth": 1})
    assert registry.latest("face_mill").validate(
        {"x1": 10, "y1": 10, "tool_d": 2, "depth": 1e-10})
