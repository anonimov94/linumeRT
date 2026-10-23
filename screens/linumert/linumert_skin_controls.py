# SPDX-License-Identifier: GPL-2.0-or-later
"""Original physical control shapes; command wiring belongs to the host. Model-Author: Codex."""

from PyQt5 import QtCore, QtGui, QtWidgets


def housing(rect, family):
    path = QtGui.QPainterPath()
    if family == "cyberdeck":
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        cut = min(11, h / 4)
        path.addPolygon(QtGui.QPolygonF([QtCore.QPointF(*v) for v in (
            (x+cut, y), (x+w-cut, y), (x+w, y+cut), (x+w, y+h-cut),
            (x+w-cut, y+h), (x+cut, y+h), (x, y+h-cut), (x, y+cut))]))
        path.closeSubpath()
    else:
        radius = rect.height()/2 if family == "organic-vector" else 4
        path.addRoundedRect(rect, radius, radius)
    return path


class SkinButton(QtWidgets.QPushButton):
    """Native focus/click semantics with family-specific painted bezels and caps."""
    def __init__(self, label, family, palette, symbol="", signal=None, parent=None):
        super().__init__(label, parent)
        self.family, self.palette, self.symbol = family, palette, symbol
        self.signal = signal or palette.accent
        self.setMinimumSize(44, 44)
        self.setAccessibleName(label)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def sizeHint(self):
        return QtCore.QSize(100, 56)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        rect = QtCore.QRectF(self.rect()).adjusted(2, 2, -2, -2)
        circular = self.family == "organic-vector" and bool(self.symbol)
        if circular:
            size = min(rect.width(), rect.height()-14)
            rect = QtCore.QRectF((self.width()-size)/2, 2, size, size)
        shape = housing(rect, self.family)
        metal = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        for stop, value in ((0, c.text), (.15, c.muted), (.45, c.background),
                             (.8, c.raised), (1, c.muted)):
            metal.setColorAt(stop, QtGui.QColor(value))
        p.fillPath(shape, QtGui.QBrush(QtGui.QColor(c.raised)
                                     if self.family == "cyberdeck" else metal))
        p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
        p.drawPath(shape)
        inset = 5 if self.family in ("classic-digital", "industrial-pro") else 3
        cap = rect.adjusted(inset, inset, -inset, -inset)
        face = housing(cap, self.family)
        glass = QtGui.QLinearGradient(cap.topLeft(), cap.bottomLeft())
        glass.setColorAt(0, QtGui.QColor(c.raised))
        glass.setColorAt(.5, QtGui.QColor(c.panel))
        glass.setColorAt(1, QtGui.QColor(c.background))
        p.fillPath(face, QtGui.QBrush(glass))
        color = QtGui.QColor(self.signal)
        p.setPen(QtGui.QPen(color, 2 if self.symbol else 1))
        p.drawPath(face)
        if self.family == "cyberdeck":
            glow = QtGui.QColor(self.signal)
            glow.setAlpha(40)
            p.setPen(QtGui.QPen(glow, 5))
            p.drawPath(face)
        if self.isDown() or self.isChecked():
            tint = QtGui.QColor(self.signal)
            tint.setAlpha(65)
            p.fillPath(face, tint)
        if self.hasFocus():
            p.setPen(QtGui.QPen(QtGui.QColor(c.text), 1, QtCore.Qt.DotLine))
            p.drawPath(housing(cap.adjusted(3, 3, -3, -3), self.family))
        if self.symbol:
            box = QtCore.QRectF(cap.x()+6, cap.y()+5, cap.width()-12, cap.height()*.52)
            self._symbol(p, box, color)
            caption = QtCore.QRectF(cap.x()+4, cap.y()+cap.height()*.62,
                                    cap.width()-8, cap.height()*.3)
        else:
            caption = cap.adjusted(3, 0, -3, 0)
        if circular:
            caption = QtCore.QRectF(1, self.height()-18, self.width()-2, 17)
        p.setPen(QtGui.QColor(c.text if self.isEnabled() else c.muted))
        font = QtGui.QFont("DejaVu Sans", 8)
        font.setBold(True)
        p.setFont(font)
        p.drawText(caption, QtCore.Qt.AlignCenter, self.text().upper())

    def _symbol(self, painter, box, color):
        painter.setBrush(color)
        painter.setPen(QtGui.QPen(color, 2))
        size = min(box.width(), box.height())*.7
        cx, cy = box.center().x(), box.center().y()
        if self.symbol == "start":
            painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(cx-size/3, cy-size/2),
                QtCore.QPointF(cx-size/3, cy+size/2), QtCore.QPointF(cx+size/2, cy)]))
        elif self.symbol == "feed_hold":
            for x in (cx-size/3, cx+size/6):
                painter.drawRect(QtCore.QRectF(x, cy-size/2, size/6, size))
        else:
            painter.drawRoundedRect(QtCore.QRectF(cx-size/2, cy-size/2, size, size), 2, 2)


class Lever(QtWidgets.QWidget):
    """Unknown read-only switch position; never an actuator."""
    def __init__(self, label, family, palette):
        super().__init__()
        self.label, self.family, self.palette = label, family, palette
        self.setMinimumSize(56, 68)
        self.setAccessibleName(label + " —")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        p.setPen(QtGui.QColor(c.muted))
        p.drawText(QtCore.QRectF(0, 0, self.width(), 20), QtCore.Qt.AlignCenter, self.label)
        center = QtCore.QPointF(self.width()/2, self.height()/2+8)
        p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 2))
        p.setBrush(QtGui.QColor(c.background))
        p.drawEllipse(center, 15, 15)
        chrome = QtGui.QLinearGradient(center.x()-5, 0, center.x()+5, 0)
        for stop, value in ((0, c.background), (.45, c.text), (.6, c.muted), (1, c.panel)):
            chrome.setColorAt(stop, QtGui.QColor(value))
        p.setBrush(chrome)
        p.drawRoundedRect(QtCore.QRectF(center.x()-5, center.y()-18, 10, 36), 4, 4)
        p.setPen(QtGui.QColor(c.text))
        p.drawText(QtCore.QRectF(self.width()-17, 27, 15, 20), QtCore.Qt.AlignCenter, "—")


class EmergencyReadout(QtWidgets.QWidget):
    """Non-interactive mushroom housing, explicitly unknown E-STOP state."""
    def __init__(self, palette):
        super().__init__()
        self.palette = palette
        self.setFixedSize(85, 80)
        self.setAccessibleName("E-STOP —")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        p.setBrush(QtGui.QColor(c.warning))
        p.setPen(QtGui.QPen(QtGui.QColor(c.background), 2))
        p.drawRoundedRect(QtCore.QRectF(6, 3, 73, 73), 5, 5)
        p.setBrush(QtGui.QColor(c.background))
        p.drawEllipse(QtCore.QPointF(42, 38), 29, 29)
        red = QtGui.QRadialGradient(35, 25, 48)
        red.setColorAt(0, QtGui.QColor(c.error))
        red.setColorAt(1, QtGui.QColor(c.background))
        p.setBrush(red)
        p.setPen(QtGui.QPen(QtGui.QColor(c.error), 2))
        p.drawEllipse(QtCore.QPointF(42, 36), 23, 23)
        p.setFont(QtGui.QFont("DejaVu Sans", 8, QtGui.QFont.Bold))
        p.setPen(QtGui.QColor(c.text))
        p.drawText(QtCore.QRectF(15, 24, 54, 22), QtCore.Qt.AlignCenter, "—")
        p.setPen(QtGui.QColor(c.background))
        p.drawText(QtCore.QRectF(8, 62, 69, 14), QtCore.Qt.AlignCenter, "E-STOP")
