# SPDX-License-Identifier: GPL-2.0-or-later
"""Interactive illustrative scenes, never machine telemetry. Model-Author: Codex."""

from linumert.programs.workpiece import Workpiece
from linumert_sim.render_mesh import prepare_mesh
from linumert_sim.render_scene import scene
from linumert_sim.render_view import RenderView
from PyQt5 import QtGui


def preview_scene(role):
    objects, path = scene("solids")
    if role == "workpiece":
        return [obj for obj in objects if obj[0] in ("cut material", "tool")], None
    if role == "toolpath":
        return [obj for obj in objects if obj[0] in ("table", "cut material", "tool")], path
    if role != "machine":
        raise ValueError(f"unknown viewport: {role}")
    objects = [obj for obj in objects if obj[0] in ("table", "cut material", "tool")]
    # Original schematic gantry in millimetres, not a Plant collision model.
    for label, size, position in (
        ("bed", (420, 260, 35), (0, 0, -35)),
        ("left column", (40, 65, 210), (-180, 65, 10)),
        ("right column", (40, 65, 210), (180, 65, 10)),
        ("bridge", (400, 60, 45), (0, 65, 220)),
        ("head", (65, 90, 80), (0, 15, 140)),
    ):
        part = Workpiece(x=size[0], y=size[1], height=size[2], position=position,
                         anchor="bottom-center")
        objects.append((label, prepare_mesh(*part.mesh()), "fg3"))
    return objects, None


def create_viewport(role, palette):
    colors = {"bg": palette.background, "fg": palette.text, "fg2": palette.muted,
              "fg3": palette.panel, "teal": palette.accent, "teal2": palette.accent,
              "amber": palette.warning}
    view = RenderView(colors)
    # Embedded panels must shrink to fit the 1280x800 compositions.
    view.setMinimumSize(80, 60)
    view.set_scene(*preview_scene(role))
    view.camera("iso")
    center, distance = {"machine": ((0, 0, 80), 800),
                        "toolpath": ((0, -25, 20), 500),
                        "workpiece": ((0, -50, 25), 240)}[role]
    view.opts["center"] = QtGui.QVector3D(*center)
    view.setCameraPosition(distance=distance)
    return view
