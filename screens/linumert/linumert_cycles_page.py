# SPDX-License-Identifier: GPL-2.0-or-later
"""Widok „Cykle”: generatory dialogowe (planowanie, otwory, nagłówek, narzędzie, koniec).

Model-Author: Claude · 2026-10-19 (pierwszy krok sesji 045, D36: funkcja widoczna od razu).

Formularz budowany z pól generatora (`Field`), walidacja z kodami P-xxxx, podgląd 2D i G-code
kroku. Kroki składają się w program; „Zapisz” zapisuje .ngc (koniec programu M2 dopisuje widok),
„Wczytaj” otwiera go w LinuxCNC — bez ruchu maszyny. Wersja częściowa: brak plików .lnx
i edycji kroków (sesje 045–047).
"""

from __future__ import annotations

import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Action

import linumert_shell_pages as pages
from linumert_sim_page import ROOT

for _p in (os.path.join(ROOT, "core"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from linumert.generators import basic, drilling  # noqa: E402

ACTION = Action()
GENERATORS = (basic.Header, basic.ToolChange, basic.FaceMill, drilling.DrillHoles,
              basic.ProgramEnd)


class Preview2D(QtWidgets.QWidget):
    """Łamane XY generatora w skali okna (oś Y w górę)."""

    def __init__(self, colors):
        super().__init__()
        self.c = colors
        self.lines: list = []
        self.setMinimumHeight(180)

    def set_lines(self, lines) -> None:
        self.lines = [ln for ln in lines if len(ln) >= 2]
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
        k = min((self.width() - 20) / w, (self.height() - 20) / h)
        ox = (self.width() - w * k) / 2 - min(xs) * k
        oy = (self.height() + h * k) / 2 + min(ys) * k
        p.setPen(QtGui.QPen(QtGui.QColor(self.c["teal"]), 1.5))
        for ln in self.lines:
            poly = QtGui.QPolygonF([QtCore.QPointF(ox + x * k, oy - y * k) for x, y in ln])
            p.drawPolyline(poly)
        p.end()


class CyclesPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.steps: list[list[str]] = []
        self.inputs: dict[str, QtWidgets.QWidget] = {}
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        frame, lay, self.lbl_step = pages.card("Cykl", "")
        self.cmb = QtWidgets.QComboBox()
        for cls in GENERATORS:
            self.cmb.addItem(cls.title, cls)
        self.cmb.currentIndexChanged.connect(self._build_form)
        lay.addWidget(self.cmb)
        self.form_box = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.form_box)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form_box)
        lay.addWidget(scroll, 1)
        self.lbl_issue = pages._label("", "lrtMuted")
        self.lbl_issue.setWordWrap(True)
        lay.addWidget(self.lbl_issue)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Podgląd", self.preview), ("Dodaj krok", self.add_step)):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        grid.addWidget(frame, 0, 0, 2, 1)
        frame, lay, _s = pages.card("Podgląd 2D", "XY [mm]")
        self.view2d = Preview2D(shell.c)
        lay.addWidget(self.view2d)
        grid.addWidget(frame, 0, 1)
        frame, lay, self.lbl_prog = pages.card("Program z kroków", "0 kroków")
        self.code = QtWidgets.QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        lay.addWidget(self.code, 1)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Usuń ostatni", self.pop_step), ("Zapisz .ngc…", self.save),
                           ("Wczytaj do LinuxCNC", self.load)):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        grid.addWidget(frame, 1, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        self.path: str | None = None
        self._build_form()

    # ---- formularz ------------------------------------------------------------------------
    def _gen(self):
        return self.cmb.currentData()()

    def _build_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self.inputs = {}
        for f in self.cmb.currentData().fields:
            if f.kind == "choice":
                w = QtWidgets.QComboBox()
                w.addItems(list(f.choices))
                if f.default is not None:
                    w.setCurrentText(str(f.default))
            elif f.kind == "bool":
                w = QtWidgets.QCheckBox()
                w.setChecked(bool(f.default))
            elif f.kind == "text":
                w = QtWidgets.QLineEdit("" if f.default is None else str(f.default))
            else:
                w = QtWidgets.QLineEdit("" if f.default is None else f"{f.default:g}")
                w.setPlaceholderText("wymagane" if f.required else "")
            label = f.label + (f" [{f.unit}]" if f.unit else "") + (" *" if f.required else "")
            self.form.addRow(label, w)
            self.inputs[f.name] = w
        self.lbl_issue.setText("")
        self.view2d.set_lines([])

    def params(self) -> dict:
        out = {}
        for f in self.cmb.currentData().fields:
            w = self.inputs[f.name]
            if isinstance(w, QtWidgets.QComboBox):
                out[f.name] = w.currentText()
            elif isinstance(w, QtWidgets.QCheckBox):
                out[f.name] = w.isChecked()
            else:
                text = w.text().strip()
                if f.kind == "text":
                    out[f.name] = text
                elif text:
                    try:
                        out[f.name] = int(text) if f.kind == "int" else float(text.replace(",", "."))
                    except ValueError:
                        out[f.name] = text  # walidacja zgłosi P-5015
        return out

    def _values(self):
        gen = self._gen()
        values, issues = gen.normalize(self.params())
        if not issues:
            issues = gen.check(values, 0)
        if issues:
            self.lbl_issue.setText("; ".join(i.message() for i in issues))
            return gen, None
        self.lbl_issue.setText("")
        return gen, values

    def preview(self) -> list[str] | None:
        gen, values = self._values()
        if values is None:
            return None
        lines = gen.generate(values)
        self.view2d.set_lines(gen.preview_2d(values))
        self.lbl_step.setText(f"{len(lines)} linii")
        return lines

    # ---- program --------------------------------------------------------------------------
    def add_step(self) -> None:
        lines = self.preview()
        if lines is not None:
            self.steps.append(lines)
            self._show()

    def pop_step(self) -> None:
        if self.steps:
            self.steps.pop()
            self._show()

    def text(self) -> str:
        body = [ln for step in self.steps for ln in step]
        return "\n".join(["( linumeRT · program z cykli )", *body, "M2", ""])

    def _show(self) -> None:
        self.code.setPlainText(self.text() if self.steps else "")
        self.lbl_prog.setText(f"{len(self.steps)} kroków")

    def save(self) -> str | None:
        if not self.steps:
            self.lbl_issue.setText("Brak kroków programu.")
            return None
        start = self.path or os.path.join(os.path.expanduser("~"), "linumert_cykle.ngc")
        path, _f = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz program", start,
                                                         "G-code (*.ngc)")
        if not path:
            return None
        if not path.endswith(".ngc"):
            path += ".ngc"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.text())
        except OSError as exc:
            self.lbl_issue.setText(f"Nie zapisano: {exc}")
            return None
        self.path = path
        self.lbl_issue.setText(f"Zapisano {path}")
        return path

    def load(self) -> None:
        if self.shell.s.running:
            self.lbl_issue.setText("Najpierw zatrzymaj program.")
            return
        path = self.path
        if path:  # zapis bieżących kroków pod tą samą nazwą
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(self.text())
            except OSError as exc:
                self.lbl_issue.setText(f"Nie zapisano: {exc}")
                return
        else:
            path = self.save()
        if path:
            ACTION.OPEN_PROGRAM(path)

    def refresh(self) -> None:
        pass
