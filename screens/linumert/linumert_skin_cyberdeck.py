# SPDX-License-Identifier: GPL-2.0-or-later
"""Cyberdeck: two live rectangular scenes under angular instrument housings.

Model-Author: Codex. Shared Neon scene/loader; no additional CNC command channel.
The machine scene is an illustrative XYZ model, not the Plant collision model.
"""
from linumert_skin_classic import ClassicDigitalScreen
from PyQt5 import QtCore, QtGui, QtWidgets


class SceneOverlay(QtWidgets.QWidget):
    """Original corner marks above the rectangular renderer, without taking input."""

    def __init__(self, view, palette):
        super().__init__()
        self.palette = palette
        self.setMinimumSize(160, 120)
        stack = QtWidgets.QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        stack.addWidget(view)
        self.rim = QtWidgets.QWidget()
        self.rim.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.rim.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.rim.installEventFilter(self)
        stack.addWidget(self.rim)
        stack.setCurrentWidget(self.rim)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt virtual method
        if watched is self.rim and event.type() == QtCore.QEvent.Paint:
            painter = QtGui.QPainter(self.rim)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtGui.QPen(QtGui.QColor(self.palette.accent), 2))
            rect = self.rim.rect().adjusted(5, 5, -6, -6)
            for x, dx in ((rect.left(), 1), (rect.right(), -1)):
                for y, dy in ((rect.top(), 1), (rect.bottom(), -1)):
                    painter.drawPolyline(QtGui.QPolygon([
                        QtCore.QPoint(x, y + 22 * dy), QtCore.QPoint(x, y),
                        QtCore.QPoint(x + 30 * dx, y)]))
            painter.end()
            return True
        return super().eventFilter(watched, event)


class CyberdeckScreen(ClassicDigitalScreen):
    AXES = "XYZ"
    STATUS_LOCATION = "footer"
    LAYOUT = (("toolpath", 0, 0, 8, 7), ("machine", 0, 7, 8, 5),
              ("dro", 8, 0, 4, 3), ("program", 8, 3, 4, 4),
              ("feed", 8, 7, 4, 3), ("tools", 8, 10, 4, 2))

    def body(self, role):
        view = super().body(role)
        if role in self.NEON_ROLES and role in self.viewports:
            return SceneOverlay(view, self.palette)
        return view

    def build(self):
        self.mount()
        self.cards["machine"].setToolTip(
            "Model poglądowy XYZ · pozycja z LinuxCNC · nie jest modelem kolizji Plant")
        self.console_widget = self.console(("mode", "cycle", "space", "power", "estop"))
