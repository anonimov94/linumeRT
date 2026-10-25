# SPDX-License-Identifier: GPL-2.0-or-later
"""Family-specific navigation, retaining native Qt button behavior. Model-Author: Codex."""

from PyQt5 import QtCore, QtGui, QtWidgets

from linumert_skin_controls import housing


class FamilyNavigationButton(QtWidgets.QToolButton):
    """Only paints an existing area button; never owns machine commands."""

    def __init__(self, family, colors):
        super().__init__()
        self.family, self.colors = family, colors
        self.setMinimumHeight(72)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def paintEvent(self, event):  # noqa: N802 - Qt virtual method
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        c, family = self.colors, self.family
        box = QtCore.QRectF(self.rect()).adjusted(2, 2, -2, -2)
        active = self.isChecked()
        highlighted = active or self.underMouse() or self.hasFocus()
        border = QtGui.QColor(c["teal"] if highlighted else c["line2"])
        face = QtGui.QColor(c["tealbg"] if active else c["panel"])
        path = housing(box, family)
        if family == "industrial-pro":
            gradient = QtGui.QLinearGradient(box.topLeft(), box.bottomLeft())
            gradient.setColorAt(0, QtGui.QColor(c["raise"]))
            gradient.setColorAt(1, face)
            painter.fillPath(path, QtGui.QBrush(gradient))
        else:
            painter.fillPath(path, face)
        painter.setPen(QtGui.QPen(border, 2 if highlighted else 1))
        painter.drawPath(path)
        if family == "classic-digital":
            painter.drawLine(box.bottomLeft()+QtCore.QPointF(5, -4),
                             box.bottomRight()+QtCore.QPointF(-5, -4))
        elif family == "industrial-pro":
            painter.setBrush(QtGui.QColor(c["teal"] if active else c["fg3"]))
            painter.drawEllipse(QtCore.QPointF(box.right()-7, box.top()+8), 2, 2)
        elif family == "cyberdeck":
            painter.drawLine(box.topLeft()+QtCore.QPointF(14, 4),
                             box.topRight()+QtCore.QPointF(-14, 4))
        else:
            painter.setPen(QtGui.QPen(border, 3))
            painter.drawArc(box.adjusted(5, 5, -5, -5), 40*16, 70*16)
        mode = QtGui.QIcon.Normal if self.isEnabled() else QtGui.QIcon.Disabled
        state = QtGui.QIcon.On if active else QtGui.QIcon.Off
        self.icon().paint(painter, QtCore.QRect((self.width()-24)//2, 10, 24, 24),
                          QtCore.Qt.AlignCenter, mode, state)
        font = QtGui.QFont("DejaVu Sans Mono" if family in (
            "classic-digital", "cyberdeck") else "DejaVu Sans")
        font.setPixelSize(11 if family == "cyberdeck" else 12)
        font.setBold(active or family == "industrial-pro")
        painter.setFont(font)
        painter.setPen(QtGui.QColor(c["fg"] if self.isEnabled() else c["fg3"]))
        caption = self.text().upper() if family == "cyberdeck" else self.text()
        painter.drawText(QtCore.QRectF(6, 36, self.width()-12, self.height()-42),
                         QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, caption)
        if self.hasFocus():
            painter.setPen(QtGui.QPen(border, 1, QtCore.Qt.DotLine))
            painter.drawPath(housing(box.adjusted(4, 4, -4, -4), family))


def frame_qss(family, colors):
    """Decorate the permanent host bars while preserving safety-specific selectors."""
    if family == "shell":
        return ""
    c = colors
    radius = {"classic-digital": 0, "industrial-pro": 4, "cyberdeck": 2,
              "organic-vector": 20}[family]
    line = "2px" if family == "industrial-pro" else "1px"
    return f"""
        #lrtRoot QFrame#lrtTopBar {{ background: {c['panel']};
            border-bottom: {line} solid {c['teal']}; }}
        #lrtRoot QFrame#lrtBottomBar {{ background: {c['bg2']};
            border-top: {line} solid {c['line2']}; }}
        #lrtRoot QPushButton#lrtModeBtn {{ border-radius: {radius}px; }}
    """
