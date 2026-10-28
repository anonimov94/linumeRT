"""Offline SKIN-01 scenes in machine XYZ/mm. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
All models are illustrative fixtures, not a machine collision model.
"""

import numpy as np

from linumert.programs.workpiece import Workpiece

from .render_mesh import crossing_triangles, prepare_mesh
from .stl import mesh as stock_mesh
from .zmap import StockMap


def scene(name):
    """Return (label, validated mesh, semantic color) items and optional toolpath."""
    if name == "crossing":
        a, b = crossing_triangles()
        return [("A", a, "teal"), ("B", b, "amber")], None
    if name == "winding":
        a = crossing_triangles()[0]
        vertices = a.vertices.copy()
        vertices[:, 2] = 0
        front = prepare_mesh(vertices + [-90, 0, 0], a.faces)
        back = prepare_mesh(vertices + [90, 0, 0], a.faces[:, ::-1])
        return [("CCW", front, "teal"), ("CW", back, "amber")], None
    if name != "solids":
        raise ValueError(f"unknown scene: {name}")
    items = []
    for index, shape in enumerate(("box", "cylinder", "tube", "casting")):
        part = Workpiece(shape=shape, x=65, y=65, diameter=60, bore=30,
                         position=(-135 + index * 90, 45, 0), anchor="bottom-center")
        items.append((shape, prepare_mesh(*part.mesh()), "teal"))
    table = Workpiece(x=380, y=220, height=15, position=(0, 0, 0))
    tool = Workpiece(shape="cylinder", diameter=12, height=55,
                     position=(0, -55, 55), anchor="bottom-center")
    items.extend([("table", prepare_mesh(*table.mesh()), "fg3"),
                  ("tool", prepare_mesh(*tool.mesh()), "amber")])
    stock = StockMap("BOX", -70, -85, 70, -20, 0, 25, cell=5)
    stock.h[3:10, 4:23] = 8
    triangles = stock_mesh(stock)
    material = prepare_mesh(triangles.reshape(-1, 3),
                            np.arange(triangles.size // 3).reshape(-1, 3))
    items.append(("cut material", material, "fg2"))
    path = np.array([[-50, -60, 40], [-50, -60, 28], [50, -60, 28],
                     [50, -35, 28], [-50, -35, 28]], dtype=float)
    return items, path
