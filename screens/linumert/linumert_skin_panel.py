# SPDX-License-Identifier: GPL-2.0-or-later
"""Original code-drawn panel housings guided by owner mockups. Model-Author: Codex."""

from PyQt5 import QtCore, QtGui, QtWidgets


def organic_path(rect):
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    r = min(36, h*.3, w*.2)
    path = QtGui.QPainterPath(QtCore.QPointF(x+r*1.4, y+1))
    path.cubicTo(x+w*.35, y-1, x+w*.7, y+6, x+w-r, y+2)
    path.quadTo(x+w, y+3, x+w-1, y+r)
    path.cubicTo(x+w-r*.25, y+h*.4, x+w+1, y+h*.76, x+w-r*.4, y+h-r*.3)
    path.quadTo(x+w-r*.6, y+h, x+w-r*1.6, y+h-1)
    path.cubicTo(x+w*.62, y+h-7, x+w*.25, y+h+1, x+r, y+h-2)
    path.quadTo(x, y+h-1, x+1, y+h-r)
    path.cubicTo(x+r*.3, y+h*.63, x-1, y+h*.3, x+r*.45, y+r*.3)
    path.quadTo(x+r*.65, y, x+r*1.4, y+1)
    path.closeSubpath()
    return path


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
        elif self.family == "organic-vector":
            path = organic_path(rect)
        else:
            radius = 5
            path.addRoundedRect(rect, radius, radius)
        rim = QtGui.QLinearGradient(0, 0, self.width(), self.height())
        for stop, color in ((0, c.muted), (.13, c.panel), (.48, c.muted),
                            (.55, c.text), (.62, c.panel), (1, c.muted)):
            rim.setColorAt(stop, QtGui.QColor(color))
        p.fillPath(path, QtGui.QBrush(
            QtGui.QColor(c.raised) if self.family == "cyberdeck" else rim))
        p.setPen(QtGui.QPen(QtGui.QColor(
            c.accent if self.family == "cyberdeck" else c.muted), 1))
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
        if self.family == "organic-vector":
            p.drawPath(organic_path(inner))
        else:
            p.drawRoundedRect(inner, 3, 3)
        if self.family in ("classic-digital", "industrial-pro"):
            title = QtCore.QRectF(inner.x()+2, inner.y()+2, inner.width()-4, 25)
            bar = QtGui.QLinearGradient(title.topLeft(), title.bottomLeft())
            bar.setColorAt(0, QtGui.QColor(c.raised))
            bar.setColorAt(1, QtGui.QColor(c.background))
            p.fillRect(title, bar)
            p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
            p.drawLine(title.bottomLeft(), title.bottomRight())
        p.setPen(QtGui.QPen(QtGui.QColor(c.accent), 2))
        if self.family == "cyberdeck":
            neon = QtGui.QColor(c.accent)
            neon.setAlpha(50)
            p.setPen(QtGui.QPen(neon, 6))
            p.drawPath(path)
            p.setPen(QtGui.QPen(QtGui.QColor(c.accent), 2))
            p.drawLine(8, 28, 8, min(100, self.height()-28))
            p.drawLine(self.width()-70, self.height()-8, self.width()-24, self.height()-8)
        elif self.family == "organic-vector":
            p.drawArc(QtCore.QRectF(rect.right()-58, rect.bottom()-58, 54, 54),
                      270*16, 85*16)
        else:
            for x in (9, self.width()-10):
                for y in (9, self.height()-10):
                    p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
                    p.setBrush(QtGui.QColor(c.background))
                    p.drawEllipse(QtCore.QPointF(x, y), 2.5, 2.5)
        p.restore()


class UnknownGauge(QtWidgets.QWidget):
    """Read-only instrument with no invented telemetry or command binding."""
    def __init__(self, label, family, palette):
        super().__init__()
        self.label, self.family, self.palette = label, family, palette
        self.setMinimumSize(70, 80)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setAccessibleName(label + " —")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        diameter = min(self.width()-12, self.height()-24, 110)
        rect = QtCore.QRectF((self.width()-diameter)/2, 20, diameter, diameter)
        p.setPen(QtGui.QColor(c.text))
        p.drawText(QtCore.QRectF(0, 0, self.width(), 18), QtCore.Qt.AlignCenter, self.label)
        p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 4))
        p.drawArc(rect.adjusted(3, 3, -3, -3), -45*16, 270*16)
        face = rect.adjusted(10, 10, -10, -10)
        metal = QtGui.QConicalGradient(face.center(), 40)
        for stop, color in ((0, c.panel), (.25, c.muted), (.5, c.background),
                            (.75, c.muted), (1, c.panel)):
            metal.setColorAt(stop, QtGui.QColor(color))
        if self.family == "classic-digital":
            p.setBrush(metal)
            p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
            p.drawEllipse(face)
        else:
            p.setBrush(QtGui.QColor(c.background))
            p.setPen(QtGui.QPen(QtGui.QColor(c.accent), 1))
            if self.family == "cyberdeck":
                p.drawRoundedRect(face, 3, 3)
            else:
                p.drawEllipse(face)
        p.setPen(QtGui.QColor(c.text))
        p.drawText(rect, QtCore.Qt.AlignCenter, "— %")
