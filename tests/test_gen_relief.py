"""Analytic contact and continuous-move checks for STL relief finishing.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""
import math
from dataclasses import replace

import numpy as np
import pytest
from linumert.generators.relief import (
    ReliefSettings,
    ball_tip_height,
    plan_relief,
    relief_from_stl,
)
from linumert.programs.stl_section import Mesh


def plane(a=0, b=0, c=0, size=4):
    p = [(x, y, a * x + b * y + c) for x, y in
         [(-size, -size), (size, -size), (size, size), (-size, size)]]
    return np.array([[p[0], p[1], p[2]], [p[0], p[2], p[3]]], dtype=float)


@pytest.mark.parametrize("a,b", [(0, 0), (0.25, 0), (-0.5, 0.25), (1, -2)])
def test_ball_contact_on_analytic_plane(a, b):
    radius = 0.5
    expected = 3 + radius * (math.sqrt(1 + a*a + b*b) - 1)
    assert ball_tip_height(plane(a, b, 3), 0, 0, radius) == pytest.approx(expected)


def test_edge_vertex_vertical_wall_and_disconnected_shell_contacts():
    wall = np.array([[(0, -2, 0), (0, 2, 0), (0, 0, 3)]], dtype=float)
    expected = 3 + math.sqrt(1 - 0.25) - 1
    assert ball_tip_height(wall, 0.5, 0, 1) == pytest.approx(expected)
    # Interior of a sloping edge, not its end vertices or a facet interior.
    edge = np.array([[(0, -2, -2), (0, 2, 2), (0, -2, -3)]], dtype=float)
    assert ball_tip_height(edge, 0.5, 0, 1) == pytest.approx(math.sqrt(1.5) - 1)
    both = np.concatenate([plane(c=-2), plane(c=1)])
    assert ball_tip_height(both, 0, 0, 0.5) == pytest.approx(1)
    assert ball_tip_height(both, 10, 10, 0.5) == -math.inf


def test_raster_is_deterministic_and_leaves_documented_plane_allowance():
    mesh = Mesh(plane(c=2, size=1))
    settings = ReliefSettings(sample_step=0.25, stepover=0.5, safe_z=4)
    path = plan_relief(mesh, settings)
    assert path == plan_relief(mesh, settings)
    assert len(path.rows) == 5
    assert all(z == pytest.approx(2.25) for row in path.rows for _, _, z in row)
    assert path.rows[0][0][0] == -1 and path.rows[1][0][0] == 1
    assert path.gcode().count('G0 Z4') == len(path.rows) + 1
    assert 'G43 H1' in path.gcode() and path.gcode().endswith('G0 Z4\nM5\nM2\n')


def test_continuous_segments_clear_narrow_unsampled_peak():
    # Vertex peak between grid samples: a point-height raster would miss it.
    bump = np.array([[(-0.12, -0.1, 0), (0.12, -0.1, 0), (0.123, 0.02, 2)],
                     [(0.12, -0.1, 0), (0.12, 0.1, 0), (0.123, 0.02, 2)],
                     [(0.12, 0.1, 0), (-0.12, 0.1, 0), (0.123, 0.02, 2)]])
    triangles = np.concatenate([plane(size=0.5), bump])
    settings = ReliefSettings(tool_diameter=0.1, sample_step=0.25,
                              stepover=0.1, safe_z=3)
    path = plan_relief(Mesh(triangles), settings)
    for row in path.rows:
        for start, end in zip(row, row[1:], strict=False):
            for fraction in np.linspace(0, 1, 31):
                x, y, z = np.array(start) + fraction * (np.array(end) - start)
                needed = ball_tip_height(triangles, x, y, settings.tool_diameter / 2)
                assert z >= needed - 1e-10, (x, y, z, needed)


@pytest.mark.parametrize('patch', [
    {'tool_diameter': 0}, {'sample_step': 0.00001}, {'stepover': 4},
    {'safe_z': 0}, {'feed': math.nan}, {'scale': math.inf}, {'tool': True},
    {'rpm': 0}, {'plunge': -1}, {'tool_diameter': 1e308},
    {'feed': 0.00001}, {'plunge': 0.00001}, {'tool_diameter': 0.000001},
])
def test_bad_parameters_are_rejected(patch):
    with pytest.raises(ValueError):
        plan_relief(Mesh(plane()), replace(ReliefSettings(), **patch))


def test_budget_bad_mesh_and_scale():
    with pytest.raises(ValueError, match='limit'):
        plan_relief(Mesh(plane(size=100)), ReliefSettings(sample_step=0.001))
    with pytest.raises(ValueError, match='STL'):
        plan_relief(Mesh(np.array([[[math.nan] * 3] * 3])))
    mesh = Mesh(plane(c=0.1, size=0.1))
    path = plan_relief(mesh, ReliefSettings(scale=25.4, sample_step=0.5))
    assert path.rows[0][0][0] == -2.54
    assert path.rows[-1][-1][1] == 2.54


def test_ascii_stl_to_gcode(tmp_path):
    path = tmp_path / 'relief.stl'
    path.write_text('solid relief\nfacet normal 0 0 1\nouter loop\n'
                    'vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 1\n'
                    'endloop\nendfacet\nendsolid relief\n')
    result = relief_from_stl(path, ReliefSettings(sample_step=0.25, stepover=0.5))
    assert result.rows and 'G21 G90 G17 G94' in result.gcode()
    assert 'nan' not in result.gcode().lower()


def test_cli_preserves_existing_output_on_invalid_input(tmp_path):
    from linumert.generators.relief import main

    source, output = tmp_path / 'bad.stl', tmp_path / 'part.ngc'
    source.write_text('not a mesh')
    output.write_text('previous program')
    with pytest.raises(SystemExit) as error:
        main([str(source), '-o', str(output)])
    assert error.value.code == 2
    assert output.read_text() == 'previous program'


def test_cli_writes_complete_program(tmp_path, capsys):
    from linumert.generators.relief import main

    source, output = tmp_path / 'plane.stl', tmp_path / 'part.ngc'
    source.write_text('solid plane\nfacet normal 0 0 1\nouter loop\n'
                      'vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n'
                      'endloop\nendfacet\nendsolid plane\n')
    assert main([str(source), '-o', str(output), '--tool', '3', '--rpm', '8000']) == 0
    assert 'T3 M6\nG43 H3\nG97 S8000 M3' in output.read_text()
    assert output.read_text().endswith('M2\n')
    assert 'Zapisano' in capsys.readouterr().out


def test_contact_matches_independent_dense_triangle_samples():
    rng = np.random.default_rng(291)
    triangles = rng.uniform(-1, 1, (12, 3, 3))
    weights = rng.dirichlet([1, 1, 1], 6000)
    samples = np.einsum('pi,tij->tpj', weights, triangles).reshape(-1, 3)
    for x, y in ((0, 0), (0.5, -0.4), (-0.3, 0.6)):
        distance2 = np.sum((samples[:, :2] - [x, y]) ** 2, axis=1)
        inside = distance2 <= 0.7**2
        brute = np.max(samples[inside, 2] + np.sqrt(0.7**2 - distance2[inside]) - 0.7)
        exact = ball_tip_height(triangles, x, y, 0.7)
        assert brute <= exact + 1e-10
        assert exact - brute < 0.06
        assert ball_tip_height(triangles[:, ::-1], x, y, 0.7) == pytest.approx(exact)


@pytest.mark.linuxcnc
def test_relief_program_in_linuxcnc_interpreter(tmp_path):
    from linumert.programs.linuxcnc_check import check_with_linuxcnc

    path = plan_relief(Mesh(plane(a=0.2, b=0.1, size=1)),
                       ReliefSettings(sample_step=0.25, stepover=0.5))
    program = tmp_path / 'relief.ngc'
    program.write_text(path.gcode())
    result = check_with_linuxcnc(program)
    assert result.ok, result


def test_exported_program_removes_near_net_stock_without_gouging_plane():
    import re

    from linumert_sim.cutter import make_cutter
    from linumert_sim.zmap import StockMap

    mesh = Mesh(plane(a=0.2, b=0.1, size=1))
    path = plan_relief(mesh, ReliefSettings(tool_diameter=0.4, sample_step=0.1,
                                          stepover=0.1, safe_z=2))
    stock = StockMap('BOX', -1, -1, 1, 1, -1, 1, cell=0.05)
    xx, yy = np.meshgrid(stock.xs, stock.ys)
    target = 0.2 * xx + 0.1 * yy
    stock.h[:] = target + 0.4  # Explicitly roughed, near-net stock.
    tool = make_cutter(1, 20, 0.4, 'ball', {'d': 0.4, 'l': 10, 'flute_length': 5})
    before = stock.volume()
    position = (0, 0, 2)
    for line in path.gcode().splitlines():
        if not line.startswith(('G0 ', 'G1 ')):
            continue
        words = {k: float(v) for k, v in re.findall(r'([XYZ])(-?[0-9.]+)', line)}
        end = tuple(words.get(axis, position[i]) for i, axis in enumerate('XYZ'))
        if line.startswith('G0 '):
            if end[:2] != position[:2]:
                assert end[2] == position[2] == 2, line
            assert stock.cut(tool, position, end).removed == 0, line
        else:
            assert not stock.cut(tool, position, end).parts, line
        position = end
    assert before - stock.volume() > 0.5
    assert np.all(stock.h >= target - 1e-6), 'cut below the STL surface'
    interior = (np.abs(xx) < 0.8) & (np.abs(yy) < 0.8)
    assert np.max(stock.h[interior] - target[interior]) < 0.13
