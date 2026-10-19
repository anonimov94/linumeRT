# SPDX-License-Identifier: GPL-2.0-or-later
"""Jedna strona profilu odlewu: Z wzdłuż osi, R od osi. Model-Author: Codex."""

from math import isfinite

from PyQt5 import QtCore, QtGui, QtWidgets


class ProfilePlot(QtWidgets.QWidget):
    def __init__(self, colors):
        super().__init__()
        self.c, self.points = colors, []
        self.setMinimumHeight(120)

    def paintEvent(self, _event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(self.c["bg"]))
        p.setPen(QtGui.QColor(self.c["fg2"]))
        p.drawText(8, 16, "Profil jednej strony · obrót wokół Z o 360°")
        if len(self.points) < 2:
            return
        z0 = min(z for z, _r in self.points)
        dz = max(max(z for z, _r in self.points) - z0, 1)
        radius = max(max(r for _z, r in self.points), 1)
        base = self.height() - 24
        points = [QtCore.QPointF(24 + (z - z0) / dz * (self.width() - 64),
                                base - r / radius * (self.height() - 56))
                  for z, r in self.points]
        p.drawLine(16, base, self.width() - 16, base)
        p.drawText(self.width() - 36, self.height() - 5, "Z →")
        p.drawText(2, 38, "R")
        p.setPen(QtGui.QPen(QtGui.QColor(self.c["teal"]), 2))
        p.drawPolyline(QtGui.QPolygonF(points))
        p.setBrush(QtGui.QColor(self.c["teal"]))
        for point in points:
            p.drawEllipse(point, 4, 4)


class ProfileEditor(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, colors):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = ProfilePlot(colors)
        layout.addWidget(self.plot)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Z wzdłuż osi [mm]", "R od osi [mm]"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(125)
        self.table.setMaximumHeight(200)
        self.table.setAccessibleName("Punkty konturu odlewu Z i R")
        layout.addWidget(self.table)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Dodaj punkt", self.add_point), ("Usuń punkt", self.remove_point)):
            button = QtWidgets.QPushButton(text)
            button.setMinimumHeight(44)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        self.table.itemChanged.connect(self._update)

    def set_points(self, points):
        self.table.blockSignals(True)
        self.table.setRowCount(len(points))
        for row, pair in enumerate(points):
            for col, value in enumerate(pair):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(f"{value:g}"))
        self.table.blockSignals(False)
        self._update()

    def points(self):
        try:
            points = tuple(tuple(float(self.table.item(row, col).text().replace(",", "."))
                                 for col in range(2)) for row in range(self.table.rowCount()))
            if not all(isfinite(v) for pair in points for v in pair):
                raise ValueError
            return points
        except (AttributeError, ValueError):
            raise ValueError("Każdy punkt odlewu wymaga liczbowych Z i R") from None

    def add_point(self):
        try:
            points = self.points()
        except ValueError:
            return
        if len(points) < 32:
            self.set_points((*points, (points[-1][0] + 10, points[-1][1])) if points else
                            ((0, 25), (10, 25)))

    def remove_point(self):
        if self.table.rowCount() > 2:
            row = self.table.currentRow()
            self.table.removeRow(row if row >= 0 else self.table.rowCount() - 1)
            self._update()

    def _update(self, *_args):
        try:
            self.plot.points = self.points()
            self.plot.update()
        except ValueError:
            pass  # walidacja formularza pokazuje błąd, zachowujemy poprzedni rysunek
        self.changed.emit()
