#!/usr/bin/env python3
"""Real OpenGL evidence, run under X11/GPU or Xvfb/Mesa. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
Fails on missing depth/context, wrong occlusion or ignored diagnostic controls.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PyQt5")

# X11/Xwayland is the common host/Debian test path. Match PyOpenGL to Qt,
# even when the desktop also exports WAYLAND_DISPLAY (PyOpenGL otherwise picks EGL).
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    if os.environ["QT_QPA_PLATFORM"] == "xcb":
        os.environ.setdefault("PYOPENGL_PLATFORM", "glx")

import numpy as np
import pyqtgraph
import yaml
from OpenGL import GL
from PyQt5 import QtCore, QtGui, QtTest, QtWidgets

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "simulation")]
from linumert_sim.render_scene import scene  # noqa: E402
from linumert_sim.render_view import RenderView  # noqa: E402


def pixels(image):
    image = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
    data = image.bits()
    data.setsize(image.byteCount())
    return np.frombuffer(data, np.uint8).reshape(image.height(), image.width(), 4).copy()


def check(output):
    output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    colors = yaml.safe_load((ROOT / "docs/design/tokens.yaml").read_text())["kolory"]
    view = RenderView(colors)
    view.resize(800, 600)
    view.show()
    QtTest.QTest.qWait(200)
    report = view.context_report()
    report.update(pyqtgraph=pyqtgraph.__version__, qt=QtCore.QT_VERSION_STR)
    assert report["depth_bits"] >= 16, report

    def capture(name):
        QtTest.QTest.qWait(90)
        image = view.grabFramebuffer()
        assert not image.isNull()
        assert image.save(str(output / f"{name}.png"))
        view.makeCurrent()
        assert GL.glGetError() == GL.GL_NO_ERROR
        view.doneCurrent()
        return image, pixels(image)

    objects, _ = scene("crossing")
    view.set_debug(shaded=False)
    view.camera("top")
    view.set_scene(objects)
    image, first = capture("crossing-forward")
    region = (0, 0, view.width(), view.height())
    try:  # pyqtgraph 0.14 takes an explicit viewport; Debian 0.13 uses getViewport.
        projection = view.projectionMatrix(region, region)
    except TypeError:
        projection = view.projectionMatrix(region)
    matrix = projection * view.viewMatrix()
    for x, key in ((-30, "amber"), (30, "teal")):
        point = matrix.map(QtGui.QVector3D(x, -20, 15))
        px, py = round((point.x() + 1) * image.width() / 2), round(
            (1 - point.y()) * image.height() / 2)
        assert image.pixelColor(px, py).name() == colors[key], (px, py, key)
    view.set_scene(objects[::-1])
    _, second = capture("crossing-reverse")
    report["order_difference_fraction"] = float(np.any(first != second, axis=2).mean())
    assert report["order_difference_fraction"] < .005  # equal-depth intersection edge only

    view.set_scene(*scene("winding"))
    _, both = capture("winding-two-sided")
    view.set_debug(culling=True, shaded=False)
    _, culled = capture("winding-backface")
    amber = np.array([251, 191, 36])
    assert np.all(both[:, :, :3] == amber, axis=2).sum() > 500
    assert np.all(culled[:, :, :3] == amber, axis=2).sum() == 0
    assert np.all(culled[:, :, :3] == [45, 212, 191], axis=2).sum() > 500

    view.set_debug(shaded=True)
    view.set_scene(*scene("solids"))
    for camera in ("iso", "top", "bottom"):
        view.camera(camera)
        _, frame = capture(f"solids-{camera}")
        assert np.any(frame[:, :, :3] != [10, 12, 15], axis=2).sum() > 5000
    view.camera("iso")
    _, normal = capture("solids-lit")
    view.set_debug(wireframe=True)
    _, wire = capture("solids-wire")
    assert np.any(normal != wire, axis=2).sum() > 100
    # Actual Qt mouse events exercise the inherited interactive orbit control.
    before = view.opts["azimuth"]
    QtTest.QTest.mousePress(view, QtCore.Qt.LeftButton, pos=QtCore.QPoint(300, 250))
    event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(350, 270),
                             QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    app.sendEvent(view, event)
    QtTest.QTest.mouseRelease(view, QtCore.Qt.LeftButton, pos=QtCore.QPoint(350, 270))
    assert view.opts["azimuth"] != before
    capture("solids-orbit")
    QtTest.QTest.qWait(100)
    count = len(view.paint_times)
    QtTest.QTest.qWait(150)
    assert len(view.paint_times) == count, "static scene keeps rendering"
    start = time.monotonic()
    while time.monotonic() - start < .35:
        view.update()
        QtTest.QTest.qWait(1)
    report["scheduled_frames_350ms"] = len(view.paint_times) - count
    assert 1 <= report["scheduled_frames_350ms"] <= 11
    report["passed"] = True
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    view.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    check(parser.parse_args().output)
