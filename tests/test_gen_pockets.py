"""Testy prototypów kieszeni M3 (sesja 041).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-20
"""

import pytest
from linumert.generators.pockets import PocketCircle, PocketRect


@pytest.mark.parametrize("generator,dimensions", [
    (PocketRect, {"width": 40.0, "height": 30.0}),
    (PocketCircle, {"diameter": 40.0}),
])
def test_pocket_generates_and_retracts(generator, dimensions):
    obj = generator()
    params = {"depth": 2.0, "tool_d": 8.0, **dimensions}
    values, issues = obj.normalize(params)
    assert not issues
    assert not obj.check(values, 1)
    lines = obj.generate(values)
    assert lines[-1] == "G0 Z5"
    assert "G1 Z-2 F100" in lines
    assert obj.generate(values) == lines
    assert obj.preview_2d(values)


@pytest.mark.parametrize("generator,dimensions", [
    (PocketRect, {"width": 8.0, "height": 30.0}),
    (PocketCircle, {"diameter": 8.0}),
])
def test_pocket_rejects_tool_that_does_not_fit(generator, dimensions):
    params = {"depth": 2.0, "tool_d": 8.0, **dimensions}
    assert any(issue.field == "tool_d" for issue in generator().validate(params))


def test_circle_emits_linuxcnc_center_arc():
    obj = PocketCircle()
    values, issues = obj.normalize({"diameter": 30.0, "tool_d": 10.0, "depth": 1.0})
    assert not issues
    assert any(line.startswith("G3 ") and " I-" in line and " J0 " in line
               for line in obj.generate(values))


def test_rect_stays_within_tool_center_bounds():
    obj = PocketRect()
    values, issues = obj.normalize({"width": 40.0, "height": 20.0,
                                    "tool_d": 10.0, "depth": 1.0})
    assert not issues
    assert all(abs(x) <= 15.0 and abs(y) <= 5.0
               for path in obj.preview_2d(values) for x, y in path)


def test_pocket_rejects_unsafe_z():
    assert any(issue.field == "safe_z" for issue in PocketCircle().validate(
        {"diameter": 30.0, "tool_d": 10.0, "depth": 1.0, "safe_z": 0.0}))
