"""Independent opaque depth-buffer renderer, SKIN-01 prototype. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
No ACTION/STATUS, HAL, simulation worker or skin dependency. PyQt5/pyqtgraph only.
"""

import time

import numpy as np
import pyqtgraph.opengl as gl
from OpenGL import GL
from PyQt5 import QtCore, QtGui


class RenderView(gl.GLViewWidget):
    """CCW, flat normals, opaque depth writes; optional back-face and edge diagnostics."""

    FRAME_MS = 34  # ceil(1000/30), also coalesces mouse/resize/content updates

    def __init__(self, colors, parent=None):
        super().__init__(parent=parent)
        fmt = self.format()
        fmt.setDepthBufferSize(24)
        fmt.setSamples(0)
        self.setFormat(fmt)
        self.colors = colors
        self.setBackgroundColor(QtGui.QColor(colors["bg"]))
        self._refresh = QtCore.QTimer(self)
        self._refresh.setSingleShot(True)
        self._refresh.setTimerType(QtCore.Qt.PreciseTimer)
        self._refresh.timeout.connect(super().update)
        self.paint_times = []
        self.mesh_items = []
        self.wireframe = self.culling = False
        self.shaded = True
        self.setMinimumSize(480, 360)

    def update(self, *args):
        if not hasattr(self, "_refresh"):
            return super().update(*args)
        if not self._refresh.isActive():
            self._refresh.start(self.FRAME_MS)

    def paintGL(self, *args, **kwargs):
        self.paint_times = self.paint_times[-119:] + [time.monotonic()]
        return super().paintGL(*args, **kwargs)

    def rgba(self, key):
        color = QtGui.QColor(self.colors[key])
        return color.redF(), color.greenF(), color.blueF(), 1.0

    def set_scene(self, objects, path=None):
        items = []
        for _label, mesh, color in objects:
            item = gl.GLMeshItem(vertexes=mesh.vertices, faces=mesh.faces,
                                 color=self.rgba(color), smooth=False,
                                 shader="shaded" if self.shaded else None)
            items.append(item)
        for old in list(self.items):
            self.removeItem(old)
        self.mesh_items = items
        for item in items:
            self.addItem(item)
        if path is not None:
            self.addItem(gl.GLLinePlotItem(pos=np.asarray(path), color=self.rgba("teal2"),
                                          width=1, mode="line_strip", glOptions="opaque"))
        self.set_debug(self.wireframe, self.culling, self.shaded)

    def set_debug(self, wireframe=False, culling=False, shaded=True):
        self.wireframe, self.culling, self.shaded = wireframe, culling, shaded
        for item in self.mesh_items:
            item.setGLOptions({GL.GL_DEPTH_TEST: True, GL.GL_BLEND: False,
                               GL.GL_CULL_FACE: culling, "glDepthMask": (True,),
                               "glFrontFace": (GL.GL_CCW,), "glCullFace": (GL.GL_BACK,)})
            item.setMeshData(meshdata=item.opts["meshdata"], drawEdges=wireframe,
                             edgeColor=self.rgba("fg"))
            item.setShader("shaded" if shaded else None)
        self.update()

    def camera(self, name):
        elevation, azimuth = {"top": (90, -90), "iso": (30, -60),
                              "bottom": (-60, -60)}[name]
        self.opts["center"] = QtGui.QVector3D(0, 0, 0)
        self.setCameraPosition(distance=650, elevation=elevation, azimuth=azimuth)

    def context_report(self):
        if not self.isValid():
            raise RuntimeError("OpenGL context unavailable; 3D test has not passed")
        self.makeCurrent()
        try:
            report = {name: GL.glGetString(value).decode("utf-8", "replace")
                      for name, value in (("vendor", GL.GL_VENDOR),
                                          ("renderer", GL.GL_RENDERER),
                                          ("version", GL.GL_VERSION))}
            report["depth_bits"] = int(GL.glGetIntegerv(GL.GL_DEPTH_BITS))
            return report
        finally:
            self.doneCurrent()
