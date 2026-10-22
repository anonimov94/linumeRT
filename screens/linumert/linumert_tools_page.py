# SPDX-License-Identifier: GPL-2.0-or-later
"""Widok „Narzędzia” nakładki linumeRT: baza narzędzi z typem i geometrią (NARZEDZIA_I_KOLIZJE §1).

Model-Author: Claude · 2026-10-19.

Źródłem jest baza narzędzi (`core/linumert/tools/db.py`, ścieżka `[LINUMERT]TOOL_DB`); zapis
eksportuje tool.tbl (Z = długość, D = średnica + korekcja) i każe LinuxCNC wczytać tabelę
ponownie, a proces symulacji przeładowuje bryły narzędzi. Edycja bez ruchu maszyny; blokada
podczas pracy programu (zmiana tabeli w trakcie obróbki).
"""

from __future__ import annotations

import os
import sys

import linuxcnc
from PyQt5 import QtCore, QtGui, QtWidgets

import linumert_shell_pages as pages
from linumert_sim_page import ROOT

for _p in (os.path.join(ROOT, "core"), os.path.join(ROOT, "simulation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from linumert.tools.db import Tool, ToolDBError  # noqa: E402
from linumert.tools.types import COMMON, PARAMS, TYPES  # noqa: E402
from linumert_sim.tooldata import open_db, save_tool  # noqa: E402

COLUMNS = ["T", "P", "Typ", "Opis", "D", "Korekcja D", "Długość Z", "Ostrza", "Maks. obr",
           "Kierunek"]


def _fmt(value, digits=3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


class ToolsPage(QtWidgets.QWidget):
    def __init__(self, shell, ini: str):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.ini = ini
        self.db = None
        self.tbl = None
        self.fields: dict[str, QtWidgets.QWidget] = {}
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        frame, lay, self.lbl_count = pages.card("Tabela narzędzi", "")
        # Model-Author: Codex. Read-only filters; never select or load another tool.
        filters = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Szukaj: T12, P3, opis, średnica…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Szukaj narzędzia")
        self.filter_type = QtWidgets.QComboBox()
        self.filter_type.addItem("Wszystkie typy", "")
        self.filter_type.addItem("Bez typu", None)
        for tid, definition in TYPES.items():
            self.filter_type.addItem(definition.label, tid)
        for widget in (self.search, self.filter_type):
            widget.setMinimumHeight(44)
            palette = widget.palette()
            for role, key in ((QtGui.QPalette.Base, "bg2"), (QtGui.QPalette.Text, "fg"),
                              (QtGui.QPalette.Button, "raise"),
                              (QtGui.QPalette.ButtonText, "fg")):
                if key in shell.c:
                    palette.setColor(role, QtGui.QColor(shell.c[key]))
            widget.setPalette(palette)
            filters.addWidget(widget, 1 if widget is self.search else 0)
        self.search.textChanged.connect(self._filter)
        self.filter_type.currentIndexChanged.connect(self._filter)
        lay.addLayout(filters)
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("lrtTable")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selected)
        lay.addWidget(self.table, 1)
        self.export = QtWidgets.QPushButton("Eksport całej bazy CSV…")
        self.export.setMinimumHeight(44)
        self.export.setToolTip("Zapisuje wszystkie narzędzia z bazy, niezależnie od filtrów. "
                               "Nie obejmuje niezapisanych zmian w edytorze.")
        self.export.clicked.connect(self.export_csv)
        lay.addWidget(self.export)
        grid.addWidget(frame, 0, 0)
        grid.addWidget(self._editor(), 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

    # ---- edytor -------------------------------------------------------------------------
    def _editor(self):
        frame, lay, self.lbl_edit = pages.card("Narzędzie", "")
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        self.spin_t = QtWidgets.QSpinBox()
        self.spin_t.setRange(1, 99999)
        self.spin_p = QtWidgets.QSpinBox()
        self.spin_p.setRange(0, 99999)
        self.cmb_type = QtWidgets.QComboBox()
        self.cmb_type.addItem("bez typu (walec zastępczy)", None)
        for tid, t in TYPES.items():
            self.cmb_type.addItem(t.label, tid)
        self.cmb_type.currentIndexChanged.connect(self._type_changed)
        self.txt_desc = QtWidgets.QLineEdit()
        self.spin_z = self._spin(0, 1000, " mm")
        self.cmb_hand = QtWidgets.QComboBox()
        self.cmb_hand.addItem("prawe (M3)", 1)
        self.cmb_hand.addItem("lewe (M4)", -1)
        form.addRow("Numer T", self.spin_t)
        form.addRow("Gniazdo P", self.spin_p)
        form.addRow("Typ", self.cmb_type)
        form.addRow("Opis", self.txt_desc)
        form.addRow("Długość Z (do nosa)", self.spin_z)
        form.addRow("Kierunek skrawania", self.cmb_hand)
        self.rows: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QDoubleSpinBox]] = {}
        for name, p in PARAMS.items():
            if name == "hand":
                continue
            low = p.minimum  # zero = niewypełnione; wymagane >0 sprawdza model
            spin = self._spin(low, p.maximum, f" {p.unit}" if p.unit else "")
            if name in ("flutes",):
                spin.setDecimals(0)
            if name == "d_wear":
                spin.setSpecialValueText("")
                spin.setSingleStep(0.01)
            label = QtWidgets.QLabel(p.label)
            form.addRow(label, spin)
            self.rows[name] = (label, spin)
        lay.addLayout(form)
        self.lbl_issue = pages._label("", "lrtMuted")
        self.lbl_issue.setWordWrap(True)
        lay.addWidget(self.lbl_issue)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Nowe", self.new_tool), ("Zapisz", self.save),
                           ("Usuń", self.remove)):
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        lay.addStretch(1)
        self._type_changed()
        return frame

    @staticmethod
    def _spin(low, high, suffix):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(4)
        spin.setKeyboardTracking(False)
        spin.setSuffix(suffix)
        spin.setSpecialValueText("—")  # wartość minimalna = pole puste
        return spin

    def _allowed(self) -> set[str]:
        tid = self.cmb_type.currentData()
        if tid is None:
            return {"d", "l"} | set(COMMON)
        t = TYPES[tid]
        return set(t.required) | set(t.optional) | set(COMMON)

    def _type_changed(self) -> None:
        allowed = self._allowed()
        tid = self.cmb_type.currentData()
        required = set(TYPES[tid].required) if tid else set()
        for name, (label, spin) in self.rows.items():
            show = name in allowed
            label.setVisible(show)
            spin.setVisible(show)
            label.setText(PARAMS[name].label + (" *" if name in required else ""))

    # ---- dane ---------------------------------------------------------------------------
    def export_csv(self) -> None:
        """Model-Author: Codex. Read-only backup; no tool.tbl or CNC commands."""
        if not self._open():
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Eksport całej bazy narzędzi", "narzedzia.csv", "CSV (*.csv)")
        if not filename:
            return
        try:
            data = self.db.export_csv().encode("utf-8")
        except Exception as exc:  # noqa: BLE001 - report database errors in the HMI
            QtWidgets.QMessageBox.warning(self, "Eksport nieudany", str(exc))
            return
        target = QtCore.QSaveFile(filename)
        if (not target.open(QtCore.QIODevice.WriteOnly) or target.write(data) != len(data)
                or not target.commit()):
            target.cancelWriting()
            QtWidgets.QMessageBox.warning(self, "Eksport nieudany", target.errorString())

    def _open(self) -> bool:
        if self.db is not None:
            return True
        try:
            self.db, self.tbl = open_db(self.ini)
        except Exception as exc:  # noqa: BLE001 - komunikat w ekranie, reszta HMI działa
            self.lbl_issue.setText(f"Baza narzędzi niedostępna: {exc}")
            return False
        return True

    def refresh(self) -> None:
        if not self._open():
            return
        tools = self.db.tools()
        if tools == getattr(self, "_shown", None):
            return  # odświeżanie co 0,5 s: tabela bez zmian, zaznaczenie zostaje
        selected = self.table.selectionModel().selectedRows()
        number = selected[0].data(QtCore.Qt.UserRole) if selected else None
        column = self.table.currentColumn()
        self._shown = tools
        # Model-Author: Codex. Repainting data must not load a different tool into the editor.
        with QtCore.QSignalBlocker(self.table):
            self.table.setRowCount(len(tools))
            for row, t in enumerate(tools):
                p = t.params
                values = [str(t.number), str(t.pocket), TYPES[t.type].label if t.type in TYPES
                          else "bez typu", t.description, _fmt(p.get("d", t.diameter)),
                          _fmt(p.get("d_wear", 0.0)), _fmt(t.offsets.get("Z")),
                          _fmt(p.get("flutes"), 0), _fmt(p.get("max_rpm"), 0),
                          "lewe M4" if p.get("hand", 1) < 0 else "prawe M3"]
                for col, value in enumerate(values):
                    item = self.table.item(row, col)
                    if item is None:
                        item = QtWidgets.QTableWidgetItem()
                        self.table.setItem(row, col, item)
                    item.setText(value)
                    item.setData(QtCore.Qt.UserRole, t.number)
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
            for row, tool in enumerate(tools):
                if tool.number == number:
                    self.table.setCurrentCell(row, max(column, 0))
                    break
            self._filter()

    def _filter(self) -> None:
        query = self.search.text().strip().casefold()
        kind = self.filter_type.currentData()
        visible = 0
        for row, tool in enumerate(getattr(self, "_shown", [])):
            words = [f"T{tool.number}", f"P{tool.pocket}"] + [
                self.table.item(row, col).text() for col in range(self.table.columnCount())]
            match = (kind == "" or tool.type == kind) and query in " ".join(words).casefold()
            self.table.setRowHidden(row, not match)
            visible += int(match)
        self.lbl_count.setText(f"{visible} z {self.table.rowCount()} narzędzi · {self.tbl or ''}")

    def _selected(self) -> None:
        items = self.table.selectedItems()
        if not items or not self._open():
            return
        tool = self.db.get(items[0].data(QtCore.Qt.UserRole))
        if tool is not None:
            self.load(tool)

    def load(self, t: Tool) -> None:
        self.spin_t.setValue(t.number)
        self.spin_p.setValue(t.pocket)
        self.cmb_type.setCurrentIndex(max(self.cmb_type.findData(t.type), 0))
        self.txt_desc.setText(t.description)
        self.spin_z.setValue(t.offsets.get("Z", 0.0))
        self.cmb_hand.setCurrentIndex(1 if t.params.get("hand", 1) < 0 else 0)
        for name, (_label, spin) in self.rows.items():
            value = t.params.get(name)
            if name == "d" and value is None:
                value = t.diameter
            if value is None:
                value = 0.0 if name == "d_wear" else spin.minimum()
            spin.setValue(value)
        self.lbl_edit.setText(f"T{t.number}")
        self.lbl_issue.setText("")

    def new_tool(self) -> None:
        if not self._open():
            return
        used = {t.number for t in self.db.tools()}
        pockets = {t.pocket for t in self.db.tools()}
        n = next(i for i in range(1, 100000) if i not in used)
        p = next(i for i in range(1, 100000) if i not in pockets)
        self.load(Tool(number=n, pocket=p, type="flat", params={"d": 6, "l": 30,
                                                               "flute_length": 15}))

    def current(self) -> Tool:
        allowed = self._allowed()
        params = {}
        for name, (_label, spin) in self.rows.items():
            if name not in allowed:
                continue
            if name == "d_wear":  # korekcja zawsze ma wartość (-1…+1 mm, 0 = brak)
                params[name] = round(spin.value(), 4)
            elif spin.value() != spin.minimum():
                params[name] = round(spin.value(), 4)
        params["hand"] = float(self.cmb_hand.currentData())
        return Tool(number=self.spin_t.value(), pocket=self.spin_p.value(),
                    type=self.cmb_type.currentData(), description=self.txt_desc.text().strip(),
                    params=params, offsets={"Z": self.spin_z.value()},
                    diameter=params.get("d"))

    def _busy(self) -> bool:
        s = linuxcnc.stat()
        try:
            s.poll()
        except linuxcnc.error:
            return False
        return s.interp_state != linuxcnc.INTERP_IDLE

    def save(self) -> None:
        if not self._open():
            return
        if self._busy():
            self.shell.show_alarm("warn", "Tabela narzędzi: zapis niedostępny w trakcie programu")
            return
        tool = self.current()
        try:
            save_tool(self.db, tool, self.tbl)
        except ToolDBError as exc:
            self.lbl_issue.setText(str(exc))
            return
        self._reload_linuxcnc()
        self.lbl_issue.setText(f"T{tool.number} zapisane w bazie i w {os.path.basename(self.tbl)}")
        self.refresh()

    def remove(self) -> None:
        if not self._open() or self._busy():
            return
        n = self.spin_t.value()
        if self.db.get(n) is None:
            return
        if QtWidgets.QMessageBox.question(self, "Narzędzia", f"Usunąć T{n} z tabeli?") != \
                QtWidgets.QMessageBox.Yes:
            return
        self.db.remove(n)
        self.db.export_tbl(self.tbl)
        self._reload_linuxcnc()
        self.refresh()

    def _reload_linuxcnc(self) -> None:
        try:
            linuxcnc.command().load_tool_table()
        except Exception as exc:  # noqa: BLE001
            self.shell.show_alarm("warn", f"LinuxCNC nie wczytał tabeli narzędzi: {exc}")
        sim = getattr(self.shell, "sim", None)
        if sim is not None:
            QtCore.QTimer.singleShot(500, lambda: sim.client.send(cmd="tools"))

