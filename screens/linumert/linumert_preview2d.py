# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared geometry preview without cycle/compiler dependencies.

Model-Author: Claude (original Preview2D); Codex (extracted for D38, 2026-10-24).
"""
from PyQt5 import QtCore, QtGui, QtWidgets


class Preview2D(QtWidgets.QWidget):
    """Łamane XY generatora w skali okna (oś Y w górę)."""

    def __init__(self, colors):
        super().__init__()
        self.c = colors
        self.lines: list = []
        self.unit = "mm"
        self.zoom = 1.0
        self.pan = QtCore.QPointF()
        self._drag = None
        self.setMinimumHeight(180)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setToolTip("Kółko: powiększanie. Przeciągnij: przesuwanie. Podwójny klik: dopasuj.")

    def set_lines(self, lines) -> None:
        self.lines = [ln for ln in lines if len(ln) >= 2]
        self.zoom, self.pan = 1.0, QtCore.QPointF()
        self.update()

    def wheelEvent(self, event):  # noqa: N802
        if not self.lines or not event.angleDelta().y():
            return
        steps = max(-20, min(20, event.angleDelta().y() / 120))
        zoom = max(0.1, min(100, self.zoom * 1.2 ** steps))
        ratio = zoom / self.zoom
        centre = QtCore.QPointF(self.width() / 2, (self.height() - 24) / 2)
        point = QtCore.QPointF(event.pos())
        self.pan = point - centre - (point - centre - self.pan) * ratio
        self.zoom = zoom
        event.accept()
        self.update()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton:
            self._drag = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag is not None:
            self.pan += QtCore.QPointF(event.pos() - self._drag)
            self._drag = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag = None
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.zoom, self.pan = 1.0, QtCore.QPointF()
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - API Qt
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(self.c["bg2"]))
        pts = [pt for ln in self.lines for pt in ln]
        if not pts:
            p.setPen(QtGui.QColor(self.c["fg3"]))
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "brak podglądu 2D")
            return
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        w, h = max(max(xs) - min(xs), 1e-6), max(max(ys) - min(ys), 1e-6)
        k = min((self.width() - 20) / w, (self.height() - 44) / h) * self.zoom
        ox = (self.width() - w * k) / 2 - min(xs) * k + self.pan.x()
        oy = (self.height() - 24 + h * k) / 2 + min(ys) * k + self.pan.y()
        p.setPen(QtGui.QPen(QtGui.QColor(self.c["teal"]), 1.5))
        for ln in self.lines:
            poly = QtGui.QPolygonF([QtCore.QPointF(ox + x * k, oy - y * k) for x, y in ln])
            p.drawPolyline(poly)
        p.setPen(QtGui.QColor(self.c.get("fg2", self.c["fg3"])))
        caption = (f"X: {min(xs):.4f} … {max(xs):.4f}   Y: {min(ys):.4f} … {max(ys):.4f}"
                   f"   [{self.unit}]")
        p.drawText(self.rect().adjusted(8, self.height() - 24, -8, -4),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, caption)
        p.end()
