# SPDX-License-Identifier: GPL-2.0-or-later
"""Interaktywny widok brył maszyny i przygotówki, bez zależności od OpenGL. Model-Author: Codex."""

import math

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from linumert.programs.workpiece import Workpiece


class WorkpieceView(QtWidgets.QWidget):
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.c = colors
        self.spec = Workpiece()
        self.yaw, self.pitch, self.zoom = -0.7, 0.55, 1.0
        self.focus_part = False
        self.drag = None
        self.nose = (0, 0, 0)
        self.bodies = [{"shape": "box", "size": [700, 500, 40],
                        "position": [300, 200, -200], "attached": "table"}]
        self.setMinimumSize(280, 240)
        self.setAccessibleName("Maszyna i przygotówka 3D")
        self.setMouseTracking(True)

    def set_workpiece(self, spec):
        self.spec = spec
        self.update()

    def set_machine(self, bodies):
        self.bodies = bodies
        self.update()

    def fit(self, part=False):
        self.focus_part, self.zoom = part, 1.0
        self.update()

    def _body_mesh(self, body):
        size, position = body["size"], list(body["position"])
        height = size[2] if body["shape"] == "box" else size[1]
        position[2] -= height / 2
        if body.get("attached") in ("head", "spindle"):
            position = [a + b for a, b in zip(position, self.nose, strict=True)]
        values = dict(position=tuple(position), anchor="bottom-center", height=height)
        if body["shape"] == "box":
            spec = Workpiece(x=size[0], y=size[1], **values)
        else:
            spec = Workpiece(shape="cylinder", diameter=size[0], **values)
        return spec.mesh(24)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(self.c["bg"]))
        objects = [(self.spec.mesh(), self.c["teal"])]
        for body in self.bodies:
            try:
                color = self.c["amber"] if body.get("attached") == "fixture" else self.c["fg3"]
                objects.append((self._body_mesh(body), color))
            except (KeyError, ValueError, TypeError):
                continue
        ca, sa, ce, se = math.cos(self.yaw), math.sin(self.yaw), math.cos(self.pitch), math.sin(self.pitch)
        rotation = np.array([[ca, -sa, 0], [sa * se, ca * se, -ce],
                             [sa * ce, ca * ce, se]])
        reference = objects[0][0][0] if self.focus_part else np.vstack([m[0] for m, _ in objects])
        projected = reference @ rotation.T
        center = (projected.min(axis=0) + projected.max(axis=0)) / 2
        extent = np.maximum(np.ptp(projected, axis=0), 1)
        scale = min((self.width() - 60) / extent[0], (self.height() - 60) / extent[1]) * self.zoom
        origin = np.array([self.width() / 2, self.height() / 2])
        triangles = []
        for (vertices, faces), color in objects:
            points = vertices @ rotation.T - center
            screen = points[:, :2] * scale + origin
            for face in faces:
                polygon = QtGui.QPolygonF([QtCore.QPointF(*p) for p in screen[face]])
                normal = np.cross(points[face[1]] - points[face[0]],
                                  points[face[2]] - points[face[0]])
                shade = 0.55 + 0.45 * abs(normal[2]) / max(np.linalg.norm(normal), 1e-9)
                tone = QtGui.QColor(color).darker(round(100 / shade))
                triangles.append((float(points[face, 2].mean()), polygon, tone))
        painter.setPen(QtCore.Qt.NoPen)
        for _depth, polygon, tone in sorted(triangles, key=lambda t: t[0]):
            painter.setBrush(tone)
            painter.drawPolygon(polygon)
        zero = (np.asarray(self.spec.position) @ rotation.T - center)[:2] * scale + origin
        painter.setPen(QtGui.QPen(QtGui.QColor(self.c["fg"]), 2))
        painter.drawEllipse(QtCore.QPointF(*zero), 5, 5)
        painter.drawText(QtCore.QPointF(*(zero + [8, -8])), self.spec.offset)
        painter.setPen(QtGui.QColor(self.c["fg2"]))
        painter.drawText(12, self.height() - 12, "Przeciągnij: obrót · kółko: powiększenie")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag = event.pos()

    def mouseMoveEvent(self, event):
        if self.drag is not None:
            delta, self.drag = event.pos() - self.drag, event.pos()
            self.yaw += delta.x() * 0.01
            self.pitch = min(1.45, max(-1.45, self.pitch + delta.y() * 0.01))
            self.update()

    def mouseReleaseEvent(self, _event):
        self.drag = None

    def wheelEvent(self, event):
        self.zoom = min(12, max(0.2, self.zoom * (1.15 if event.angleDelta().y() > 0 else 1 / 1.15)))
        self.update()
