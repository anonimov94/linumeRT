#!/usr/bin/env python3
"""Offline SKIN-01 scene viewer (PyQt5, pyqtgraph, PyOpenGL). Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
import sys
from pathlib import Path

# X11/Xwayland is the common host/Debian test path. Match PyOpenGL to Qt,
# even when the desktop also exports WAYLAND_DISPLAY (PyOpenGL otherwise picks EGL).
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    if os.environ["QT_QPA_PLATFORM"] == "xcb":
        os.environ.setdefault("PYOPENGL_PLATFORM", "glx")

import yaml
from PyQt5 import QtWidgets

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "simulation")]
from linumert_sim.render_scene import scene  # noqa: E402
from linumert_sim.render_view import RenderView  # noqa: E402


def main():
    app = QtWidgets.QApplication(sys.argv)
    colors = yaml.safe_load((ROOT / "docs/design/tokens.yaml").read_text())["kolory"]
    window = QtWidgets.QWidget()
    window.setWindowTitle("linumeRT · SKIN-01 · offline 3D")
    layout = QtWidgets.QVBoxLayout(window)
    layout.addWidget(QtWidgets.QLabel("Prototyp offline · XYZ w mm · modele poglądowe"))
    row = QtWidgets.QHBoxLayout()
    layout.addLayout(row)
    scenes, cameras = QtWidgets.QComboBox(), QtWidgets.QComboBox()
    scenes.addItems(["solids", "crossing", "winding"])
    cameras.addItems(["iso", "top", "bottom"])
    edges, cull, shade = (QtWidgets.QCheckBox(s) for s in ("Wireframe", "Culling", "Normals/light"))
    shade.setChecked(True)
    for control in (scenes, cameras, edges, cull, shade):
        control.setMinimumHeight(44)
        row.addWidget(control)
    view = RenderView(colors)
    layout.addWidget(view, 1)
    status = QtWidgets.QLabel("Przeciągnij: obrót · kółko: zoom · bez połączenia z CNC")
    layout.addWidget(status)
    scenes.currentTextChanged.connect(lambda name: view.set_scene(*scene(name)))
    cameras.currentTextChanged.connect(view.camera)
    for control in (edges, cull, shade):
        control.toggled.connect(lambda _: view.set_debug(edges.isChecked(), cull.isChecked(),
                                                         shade.isChecked()))
    view.set_scene(*scene("solids"))
    view.camera("iso")
    window.resize(1000, 760)
    window.show()
    app.processEvents()
    try:
        info = view.context_report()
        status.setText(f"{info['renderer']} · depth {info['depth_bits']} · offline, XYZ/mm")
    except RuntimeError as error:
        status.setText(str(error))
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
