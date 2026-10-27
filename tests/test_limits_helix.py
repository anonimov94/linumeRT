"""Independent sampled bounds for transformed helices, review #173.

Model-Author: Codex.
"""

import math

import numpy as np
import pytest
from linumert.programs.limits import _arc_candidates, check_canon
from test_limits_frames import canon


def test_rotated_xz_helix_reports_extremum_between_quadrants():
    got = check_canon(canon(
        'SET_XY_ROTATION(45)', 'SELECT_PLANE(CANON_PLANE_XZ)',
        'STRAIGHT_TRAVERSE(10, 0, 0)', 'ARC_FEED(0, -10, 0, 0, 1, 10)',
    ), {'Y': (-20, 7.2)})
    assert [(v.axis, v.side) for v in got] == [('Y', 'max')]
    assert got[0].value == pytest.approx(7.43241328)


@pytest.mark.parametrize('plane', [(0, 1, 2), (1, 2, 0), (2, 0, 1)])
@pytest.mark.parametrize('direction', [-1, 1])
@pytest.mark.parametrize('turns', [1, 3])
@pytest.mark.parametrize('rotation', [45, -73])
def test_analytic_bounds_contain_dense_reference(plane, direction, turns, rotation):
    first, second, spiral = plane
    sweep = 1.7 + (turns - 1) * math.tau
    start_angle = 0.3
    start = np.zeros(3)
    start[first], start[second] = 10 * math.cos(start_angle), 10 * math.sin(start_angle)
    theta = start_angle + direction * sweep
    vals = [10 * math.cos(theta), 10 * math.sin(theta), 0, 0, direction * turns, 17]
    candidates = np.array([tuple(start), *_arc_candidates(tuple(start), vals, plane, rotation)])
    t = np.linspace(0, sweep, 20001)
    sampled = np.zeros((len(t), 3))
    sampled[:, first] = 10 * np.cos(start_angle + direction * t)
    sampled[:, second] = 10 * np.sin(start_angle + direction * t)
    sampled[:, spiral] = 17 * t / sweep
    a = math.radians(rotation)
    transform = np.array([[math.cos(a), -math.sin(a), 0],
                          [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    expected, actual = sampled @ transform.T, candidates @ transform.T
    np.testing.assert_allclose(actual.min(axis=0), expected.min(axis=0), atol=2e-5)
    np.testing.assert_allclose(actual.max(axis=0), expected.max(axis=0), atol=2e-5)


def test_rotation_change_preserves_machine_arc_start():
    got = check_canon(canon(
        'STRAIGHT_TRAVERSE(10, 0, 0)', 'SET_XY_ROTATION(90)',
        'ARC_FEED(0, 10, 0, 0, 1, 0)',
    ), {'X': (-20, 20), 'Y': (-5, 5)})
    assert any(v.axis == 'Y' and v.side == 'max' for v in got)


@pytest.mark.linuxcnc
def test_real_interpreter_rotated_xz_helix(tmp_path):
    from linumert.programs.linuxcnc_check import run_interpreter

    p = tmp_path / 'helix.ngc'
    p.write_text('G21 G90 G18\nG10 L2 P1 R45\nG0 X10 Y0 Z0\n'
                 'G3 X-10 Y10 Z0 I-10 K0 F100\nM2\n')
    run = run_interpreter(p)
    assert run.returncode == 0 and 'PROGRAM_END()' in run.stdout, run.stderr
    got = check_canon(run.stdout, {'Y': (-20, 7.2)})
    assert [(v.axis, v.side) for v in got] == [('Y', 'max')]
    assert got[0].value == pytest.approx(7.43241328)
