# SPDX-License-Identifier: GPL-2.0-or-later
"""Original code-drawn panel housings guided by owner mockups. Model-Author: Codex."""

from PyQt5 import QtCore, QtGui, QtWidgets


class SkinPanel(QtWidgets.QFrame):
    def __init__(self, family, palette):
        super().__init__()
        self.family, self.palette = family, palette
        self.setProperty("card", True)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QtGui.QPainterPath()
        if self.family == "cyberdeck":
            cut = 14
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
            points = [(x+cut,y), (x+w-cut,y), (x+w,y+cut), (x+w,y+h-cut),
                      (x+w-cut,y+h), (x+cut,y+h), (x,y+h-cut), (x,y+cut)]
            path.addPolygon(QtGui.QPolygonF([QtCore.QPointF(*point) for point in points]))
            path.closeSubpath()
        else:
            radius = 38 if self.family == "organic-vector" else 5
            path.addRoundedRect(rect, radius, radius)
        rim = QtGui.QLinearGradient(0, 0, self.width(), self.height())
        for stop, color in ((0, c.muted), (.13, c.panel), (.48, c.muted),
                            (.55, c.text), (.62, c.panel), (1, c.muted)):
            rim.setColorAt(stop, QtGui.QColor(color))
        p.fillPath(path, QtGui.QBrush(rim))
        p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        inset = 6 if self.family == "organic-vector" else 4
        inner = rect.adjusted(inset, inset, -inset, -inset)
        fill = QtGui.QLinearGradient(inner.topLeft(), inner.bottomLeft())
        fill.setColorAt(0, QtGui.QColor(c.panel))
        fill.setColorAt(1, QtGui.QColor(c.background))
        p.setBrush(fill)
        p.setPen(QtGui.QPen(QtGui.QColor(c.background), 2))
        p.drawRoundedRect(inner, 32 if self.family == "organic-vector" else 3,
                          32 if self.family == "organic-vector" else 3)
        p.setPen(QtGui.QPen(QtGui.QColor(c.accent), 2))
        if self.family == "cyberdeck":
            p.drawLine(8, 28, 8, min(100, self.height()-28))
            p.drawLine(self.width()-70, self.height()-8, self.width()-24, self.height()-8)
        elif self.family == "organic-vector":
            p.drawArc(inner.adjusted(4, 4, -4, -4), 115*16, 48*16)
        else:
            for x in (9, self.width()-10):
                for y in (9, self.height()-10):
                    p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
                    p.setBrush(QtGui.QColor(c.background))
                    p.drawEllipse(QtCore.QPointF(x, y), 2.5, 2.5)
        p.restore()
