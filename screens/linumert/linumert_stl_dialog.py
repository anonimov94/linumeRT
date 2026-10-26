# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline STL inspection and closed-section capture. Model-Author: Codex."""
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from linumert.generators.path_geometry import decode_paths
from linumert.programs.stl_section import read_stl, section_xy

from linumert_preview2d import Preview2D
from linumert_shell_model import load_tokens, shell_qss


class MeshPreview(QtWidgets.QWidget):
    def __init__(self, colors):
        super().__init__()
        self.colors, self.mesh = colors, None
        self.mode = "iso"
        self.setMinimumSize(320, 240)

    def paintEvent(self, event):  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(self.colors["bg2"]))
        if self.mesh is None:
            return
        sample = self.mesh.triangles[::max(1, math.ceil(len(self.mesh.triangles) / 2000))]
        if self.mode == "iso":
            points = np.stack((sample[:, :, 0] - sample[:, :, 1],
                               (sample[:, :, 0] + sample[:, :, 1]) / 2 - sample[:, :, 2]), axis=2)
        else:
            i, j = {"XY": (0, 1), "XZ": (0, 2), "YZ": (1, 2)}[self.mode]
            points = np.stack((sample[:, :, i], -sample[:, :, j]), axis=2)
        low, high = points.min(axis=(0, 1)), points.max(axis=(0, 1))
        size = np.maximum(high - low, 1e-9)
        scale = min((self.width() - 24) / size[0], (self.height() - 24) / size[1])
        points = (points - (low + high) / 2) * scale + [self.width() / 2, self.height() / 2]
        painter.setPen(QtGui.QPen(QtGui.QColor(self.colors["teal"]), 0.6))
        for triangle in points:
            painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(float(x), float(y))
                                                for x, y in triangle]))


class StlDialog(QtWidgets.QDialog):
    def __init__(self, parent, program_units, colors):
        super().__init__(parent)
        self.setObjectName("lrtRoot")
        self.setWindowTitle("STL — model i przekrój XY")
        self.resize(1200, 720)
        tokens = load_tokens()
        tokens["kolory"] = {**tokens["kolory"], **colors}
        self.colors = tokens["kolory"]
        self.setStyleSheet(shell_qss(tokens))
        self.program_units = program_units
        self.mesh, self.paths_json, self.source = None, None, ""
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._job, self._revision = None, 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll)
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel("Model STL → przekrój XY → kontur do grawerowania. "
                                "STL nie zawiera jednostek; wybierz je przed przeliczeniem.")
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QtWidgets.QHBoxLayout()
        self.choose = QtWidgets.QPushButton("Otwórz STL…")
        self.choose.clicked.connect(self.choose_file)
        controls.addWidget(self.choose)
        self.units = QtWidgets.QComboBox()
        self.units.addItems(["mm", "cal"])
        self.scale = QtWidgets.QDoubleSpinBox()
        self.scale.setRange(0.001, 1000)
        self.scale.setDecimals(4)
        self.scale.setValue(1)
        self.z = QtWidgets.QDoubleSpinBox()
        self.z.setRange(-1000000, 1000000)
        self.z.setDecimals(4)
        self.center = QtWidgets.QCheckBox("Wycentruj XY")
        self.center.setChecked(True)
        for label, widget in (("Jednostki STL", self.units), ("Skala", self.scale),
                              (f"Przekrój Z [{'cal' if program_units == 'inch' else 'mm'}]", self.z)):
            controls.addWidget(QtWidgets.QLabel(label))
            controls.addWidget(widget)
            signal = widget.currentIndexChanged if widget is self.units else widget.valueChanged
            signal.connect(self._changed)
        controls.addWidget(self.center)
        self.center.toggled.connect(self._changed)
        layout.addLayout(controls)
        self.tabs = QtWidgets.QTabWidget()
        self.model_view = MeshPreview(self.colors)
        self.section_view = Preview2D(self.colors)
        self.tabs.addTab(self.model_view, "Model · siatka poglądowa do 2000 trójkątów")
        self.tabs.addTab(self.section_view, "Przekrój XY · pełna siatka")
        layout.addWidget(self.tabs, 1)
        row = QtWidgets.QHBoxLayout()
        self.view = QtWidgets.QComboBox()
        self.view.addItems(["iso", "XY", "XZ", "YZ"])
        self.view.currentTextChanged.connect(self.set_view)
        row.addWidget(self.view)
        self.calculate = QtWidgets.QPushButton("Przelicz przekrój")
        self.calculate.setEnabled(False)
        self.calculate.clicked.connect(self.calculate_section)
        row.addWidget(self.calculate)
        layout.addLayout(row)
        self.message = QtWidgets.QLabel("Wybierz plik STL ASCII lub binary, do 8 MiB / 100000 trójkątów.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok
                                                  | QtWidgets.QDialogButtonBox.Cancel)
        self.apply = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
        self.apply.setText("Użyj przekroju")
        self.apply.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def set_view(self, mode):
        self.model_view.mode = mode
        self.model_view.update()

    def factor(self):
        return self.scale.value() * (25.4 if self.units.currentText() == "cal" else 1) / (
            25.4 if self.program_units == "inch" else 1)

    def _changed(self):
        self._revision += 1
        self.paths_json = None
        self.apply.setEnabled(False)
        self.section_view.set_lines([])
        self.message.setText("Parametry zmienione — przelicz przekrój.")

    def choose_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Model STL", "", "STL (*.stl *.STL)")
        if path:
            self.load_path(path)

    def load_path(self, path):
        if self._job is not None:
            return
        self._changed()
        self.source = str(path)
        self.mesh = None
        self.model_view.mesh = None
        self.model_view.update()
        self.choose.setEnabled(False)
        self.calculate.setEnabled(False)
        self._job = (self._pool.submit(read_stl, path), self._revision, "load")
        self.message.setText("Odczyt STL…")
        self._timer.start()

    def calculate_section(self):
        if self.mesh is None or self._job is not None:
            return
        self._changed()
        self.calculate.setEnabled(False)
        self.choose.setEnabled(False)
        self._job = (self._pool.submit(section_xy, self.mesh, self.z.value(),
                                       self.factor(), self.center.isChecked()), self._revision, "slice")
        self.message.setText("Obliczanie przekroju…")
        self._timer.start()

    def _poll(self):
        if self._job is None or not self._job[0].done():
            return
        future, revision, action = self._job
        self._job = None
        self._timer.stop()
        self.choose.setEnabled(True)
        self.calculate.setEnabled(self.mesh is not None)
        try:
            result = future.result()
        except (ValueError, OSError) as exc:
            self.message.setText(str(exc))
            return
        if action == "load":
            self.mesh = self.model_view.mesh = result
            self.model_view.update()
            low, high = result.bounds
            self.z.setValue(float((low[2] + high[2]) / 2 * self.factor()))
            self.calculate.setEnabled(True)
            self.calculate_section()
        elif revision == self._revision:
            encoded = json.dumps(result, separators=(",", ":"), allow_nan=False)
            try:
                decode_paths(encoded)
            except ValueError as exc:
                self.message.setText(str(exc))
                return
            self.paths_json = encoded
            self.section_view.set_lines(result)
            self.apply.setEnabled(True)
            low, high = self.mesh.bounds
            extent = (high - low) * self.factor()
            self.message.setText(f"{len(self.mesh.triangles)} trójkątów, {len(result)} zamkniętych "
                                 f"konturów. Rozmiar XYZ: {extent[0]:g} × {extent[1]:g} × "
                                 f"{extent[2]:g} [{'cal' if self.program_units == 'inch' else 'mm'}]. "
                                 f"Przekrój Z={self.z.value():g}.")
        else:
            self.message.setText("Parametry zmienione podczas obliczeń — przelicz ponownie.")

    def description(self):
        return (f"{Path(self.source).name} | Z={self.z.value():g} | "
                f"{self.units.currentText()} | skala={self.scale.value():g}").replace(
                    "(", "[").replace(")", "]").replace("\n", " ")

    def accept(self):
        if self.paths_json is not None and self._job is None:
            super().accept()

    def done(self, result):
        self._timer.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)
        super().done(result)
