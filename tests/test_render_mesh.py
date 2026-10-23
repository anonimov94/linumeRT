"""SKIN-01 geometry and reproducible legacy defects. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import ast
import importlib
import math
from pathlib import Path

import numpy as np
import pytest
from linumert.programs.workpiece import Workpiece
from linumert_sim.render_mesh import crossing_triangles, prepare_mesh
from linumert_sim.stl import mesh as stock_mesh
from linumert_sim.zmap import StockMap


@pytest.mark.parametrize("shape", ["box", "cylinder", "tube", "casting"])
def test_closed_workpieces_have_outward_winding(shape):
    mesh = prepare_mesh(*Workpiece(shape=shape, position=(0, 0, 0)).mesh())
    triangles = mesh.vertices[mesh.faces]
    volume = np.einsum("ij,ij->i", triangles[:, 0],
                       np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6
    assert volume > 0
    assert mesh.removed_degenerate == 0
    np.testing.assert_allclose(np.linalg.norm(mesh.normals, axis=1), 1)
    # Each directed edge has exactly one oppositely oriented neighbour.
    edges = [(int(a), int(b)) for f in mesh.faces for a, b in zip(f, np.roll(f, -1), strict=True)]
    assert len(set(edges)) == len(edges)
    assert all((b, a) in set(edges) for a, b in edges)


def test_stl_stock_top_bottom_and_volume():
    stock = StockMap("BOX", 0, 0, 20, 16, -10, 0, cell=2)
    stock.h[2:5, 2:5] = -4
    triangles = stock_mesh(stock)
    mesh = prepare_mesh(triangles.reshape(-1, 3), np.arange(triangles.size // 3).reshape(-1, 3))
    assert mesh.removed_degenerate == 0
    volume = np.einsum("ij,ij->i", triangles[:, 0],
                       np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6
    assert volume == pytest.approx(20 * 16 * 10 - 9 * 4 * 4)
    top = np.all(triangles[:, :, 2] == 0, axis=1)
    bottom = np.all(triangles[:, :, 2] == -10, axis=1)
    assert np.all(mesh.normals[top, 2] == 1)
    assert np.all(mesh.normals[bottom, 2] == -1)


@pytest.mark.parametrize("vertices,faces", [
    ([[0, 0, np.nan]], [[0, 0, 0]]), ([[0, 0, 0]], [[0, 0, 1]]),
    ([[0, 0, 0]], [[-1, 0, 0]]), ([[0, 0, 0]], [[0., 0., 0.]]),
    ([[0, 0, 0]], [[0, 0, 0]]),
])
def test_invalid_geometry_is_explicit(vertices, faces):
    with pytest.raises(ValueError):
        prepare_mesh(vertices, faces)


def test_crossing_surfaces_need_per_pixel_depth():
    a, b = crossing_triangles()
    assert a.vertices[:, 2].mean() == b.vertices[:, 2].mean()
    assert a.vertices[0, 2] < b.vertices[0, 2]
    assert a.vertices[1, 2] > b.vertices[1, 2]


def test_legacy_revolve_contains_zero_area_caps(monkeypatch):
    # Execute the actual helper without importing QtVCP's singleton runtime.
    path = Path(__file__).parents[1] / "screens/linumert/linumert_sim_page.py"
    tree = ast.parse(path.read_text())
    helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == "_revolve")
    namespace = {"np": np, "math": math}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), str(path), "exec"), namespace)
    mesh = prepare_mesh(*namespace["_revolve"]([(10, 0), (10, 20)], segments=24))
    assert mesh.removed_degenerate == 48  # both caps duplicate the axis 24 times


def test_legacy_painter_hides_one_side_of_crossing(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PyQt5.QtWidgets")
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "screens/linumert"))
    legacy = importlib.import_module("linumert_workpiece_view")
    app = qt.QApplication.instance() or qt.QApplication([])
    colors = dict(bg="#0a0c0f", teal="#2dd4bf", fg3="#fbbf24", fg="#e8eef4", fg2="#9aa7b4")
    view = legacy.WorkpieceView(colors)
    a, b = crossing_triangles()
    # Legacy yaw=pitch=0 maps (x,y,z) to screen (x,-z), depth=y.
    def legacy_mesh(mesh):
        return mesh.vertices[:, [0, 2, 1]] * [1, 1, -1], mesh.faces
    class Spec:
        position, offset = (0, 0, 0), "G54"
        def mesh(self):
            return legacy_mesh(a)
    view.spec = Spec()
    view.bodies = [{}]
    view._body_mesh = lambda _: legacy_mesh(b)
    view.yaw = view.pitch = 0
    view.resize(640, 480)
    image = view.grab().toImage()
    image.save(str(tmp_path / "legacy-crossing.png"))
    # Both sides are amber, although the right side should be teal.
    left, right = (image.pixelColor(x, 170) for x in (220, 420))
    assert left == right
    assert right.red() > right.green() > right.blue()
    view.close()
    app.processEvents()
