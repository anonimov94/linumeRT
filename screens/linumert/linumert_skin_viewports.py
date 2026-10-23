# SPDX-License-Identifier: GPL-2.0-or-later
"""Interactive illustrative scenes, never machine telemetry. Model-Author: Codex."""

from linumert.programs.workpiece import Workpiece
from linumert_sim.render_mesh import prepare_mesh
import numpy as np
from linumert_sim.stl import mesh as stock_mesh
from linumert_sim.zmap import StockMap
from linumert_sim.render_view import RenderView
from PyQt5 import QtGui


def preview_scene(role):
    stock = StockMap("BOX", -75, -55, 75, 55, 0, 24, cell=2)
    # Original illustrative pocketed plate, computed geometry rather than a bitmap.
    yy, xx = np.meshgrid(stock.ys, stock.xs, indexing="ij")
    stock.h[(xx / 34)**2 + (yy / 28)**2 < 1] = 5
    for x in (-56, 56):
        for y in (-37, 37):
            stock.h[(xx-x)**2 + (yy-y)**2 < 8**2] = 1
    triangles = stock_mesh(stock)
    part = ("plate", prepare_mesh(triangles.reshape(-1, 3),
                                 np.arange(triangles.size // 3).reshape(-1, 3)), "fg2")
    objects = [part]
    def solid(label, size, position, color="fg3", shape="box"):
        block = Workpiece(x=size[0], y=size[1], diameter=size[0], height=size[2],
                          position=position, shape=shape, anchor="bottom-center")
        objects.append((label, prepare_mesh(*block.mesh()), color))
    solid("cutter", (8, 8, 44), (35, 18, 28), "amber", "cylinder")
    solid("holder", (22, 22, 35), (35, 18, 72), "fg3", "cylinder")
    if role == "workpiece":
        return [part], None
    if role == "toolpath":
        path = []
        for offset in np.linspace(0, 14, 12):
            # Rounded rectangular contours with a small tool-radius corner.
            for cx, cy, start in ((55-offset,35-offset,0),
                                   (-55+offset,35-offset,90),
                                   (-55+offset,-35+offset,180),
                                   (55-offset,-35+offset,270)):
                for angle in np.linspace(start, start+90, 18):
                    rad = np.radians(angle)
                    path.append((cx+8*np.cos(rad), cy+8*np.sin(rad), 25))
            path.append(path[-72])
        return objects, np.asarray(path)
    if role != "machine":
        raise ValueError(f"unknown viewport: {role}")
    # Original schematic mill in mm. This is not a Plant collision model.
    for label, size, position in (
        ("base", (360, 260, 60), (0, 0, -115)),
        ("table", (300, 180, 25), (0, 0, -30)),
        ("left column", (38, 60, 255), (-145, 75, -55)),
        ("right column", (38, 60, 255), (145, 75, -55)),
        ("bridge", (330, 55, 45), (0, 75, 200)),
        ("head", (68, 70, 95), (35, 40, 108)),
    ):
        solid(label, size, position)
    for x in (-135, 135):
        solid("vertical rail", (9, 9, 235), (x, 40, -40), "fg2")
    for y in (-64, -32, 0, 32, 64):
        solid("table groove", (285, 3, 2), (0, y, -4), "bg")
    for x in (-90, 90):
        solid("clamp", (25, 45, 20), (x, 0, -5), "teal")
    return objects, None


def create_viewport(role, palette):
    colors = {"bg": palette.background, "fg": palette.text, "fg2": palette.text,
              "fg3": palette.muted, "teal": palette.accent, "teal2": palette.accent,
              "amber": palette.warning}
    view = RenderView(colors)
    # Embedded panels must shrink to fit the 1280x800 compositions.
    view.setMinimumSize(80, 60)
    view.set_scene(*preview_scene(role))
    view.camera("iso")
    center, distance = {"machine": ((0, 0, 65), 700),
                        "toolpath": ((0, 0, 20), 380),
                        "workpiece": ((0, 0, 15), 280)}[role]
    view.opts["center"] = QtGui.QVector3D(*center)
    view.setCameraPosition(distance=distance)
    return view
