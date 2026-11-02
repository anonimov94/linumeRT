"""Regresje generatora planowania — przygotowanie kamienia M3.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-20
"""

import pytest

from linumert.generators.basic import FaceMill


@pytest.fixture
def params():
    return {
        "x0": 0.0, "y0": 0.0, "x1": 40.0, "y1": 20.0,
        "z_top": 0.0, "depth": 2.0, "step_down": 1.0,
        "tool_d": 10.0, "stepover": 50.0,
        "feed": 800.0, "plunge": 200.0, "safe_z": 5.0,
    }


def test_face_mill_deterministic(params):
    generator = FaceMill()
    values, errors = generator.normalize(params)
    assert not errors
    assert generator.generate(values) == generator.generate(values)


def test_face_mill_rejects_inverted_window(params):
    params["x1"] = params["x0"]
    assert any(issue.field == "x1" for issue in FaceMill().validate(params))


def test_face_mill_rejects_unsafe_clearance(params):
    params["safe_z"] = params["z_top"]
    assert any(issue.field == "safe_z" for issue in FaceMill().validate(params))


def test_face_mill_rejects_zero_tool_diameter(params):
    params["tool_d"] = 0.0
    assert any(issue.field == "tool_d" for issue in FaceMill().validate(params))


def test_face_mill_ends_with_retract(params):
    generator = FaceMill()
    values, errors = generator.normalize(params)
    assert not errors
    assert generator.generate(values)[-1] == "G0 Z5"


def test_face_mill_preview_has_finite_coordinates(params):
    import math

    generator = FaceMill()
    values, errors = generator.normalize(params)
    assert not errors
    preview = generator.preview_2d(values)
    assert preview
    assert all(math.isfinite(c) for path in preview for point in path for c in point)
