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
import sqlite3
import sys
from dataclasses import replace

import linuxcnc
from PyQt5 import QtCore, QtGui, QtWidgets

import linumert_shell_pages as pages
from linumert_sim_page import ROOT

for _p in (os.path.join(ROOT, "core"), os.path.join(ROOT, "simulation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from linumert.tools.db import Tool, ToolDBError  # noqa: E402
from linumert.tools.types import COMMON, PARAMS, TYPES  # noqa: E402
from linumert_sim.tooldata import open_db, save_tool, table_units  # noqa: E402

COLUMNS = ["T", "P", "Typ", "Opis", "D", "Korekcja D", "Długość Z", "Ostrza", "Maks. obr",
           "Kierunek"]


def _fmt(value, digits=3) -> str:
    if value is None:
        return "—"
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


class ToolsPage(QtWidgets.QWidget):
    def __init__(self, shell, ini: str):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.ini = ini
        self.db = None
        self.tbl = None
        self.tbl_units = "mm"
        self._loading = False
        self._last_success = False
        self._dirty = False
        self._loaded_number = None
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
        self.history_button = QtWidgets.QPushButton("Historia T…")
        self.history_button.setMinimumHeight(44)
        self.history_button.clicked.connect(self.show_history)
        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.history_button)
        actions.addWidget(self.export, 1)
        lay.addLayout(actions)
        grid.addWidget(frame, 0, 0)
        self.editor_scroll = QtWidgets.QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.editor_scroll.setWidget(self._editor())
        grid.addWidget(self.editor_scroll, 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        for widget in (self.spin_t, self.spin_p, self.spin_z, self.spin_life, self.spin_used,
                       *(spin for _label, spin in self.rows.values())):
            widget.valueChanged.connect(self._edited)
            widget.lineEdit().textEdited.connect(self._edited)
        for widget in (self.cmb_type, self.cmb_hand):
            widget.currentIndexChanged.connect(self._edited)
        for widget in (self.txt_desc, self.txt_holder, self.txt_stl):
            widget.textChanged.connect(self._edited)

    def _edit_state(self, dirty):
        self._dirty = dirty
        self.lbl_edit.setText(f"T{self.spin_t.value()}" + (" · niezapisane" if dirty else ""))
        pages._restyle(self.lbl_edit, dirty=dirty)

    def _edited(self):
        if self._loading:
            return
        self._edit_state(True)
        if self._last_success:
            self.lbl_issue.clear()
            self._last_success = False

    def _discard_edits(self):
        if not self._dirty:
            return True
        box = QtWidgets.QMessageBox(self)
        box.setObjectName("lrtRoot")
        box.setWindowTitle("Niezapisane zmiany")
        box.setText(f"Odrzucić niezapisane zmiany\nformularza T{self.spin_t.value()}?")
        box.setInformativeText("Dotyczy tylko pól formularza. "
                               "Nie cofa danych już zapisanych w bazie.")
        discard = box.addButton("Odrzuć zmiany", QtWidgets.QMessageBox.DestructiveRole)
        stay = box.addButton("Zostań", QtWidgets.QMessageBox.RejectRole)
        stay.setStyleSheet("font-weight: 700;")
        box.setDefaultButton(stay)
        box.setEscapeButton(stay)
        box.exec_()
        result = box.clickedButton() is discard
        box.deleteLater()
        return result

    def _restore_selection(self):
        column = max(self.table.currentColumn(), 0)
        with QtCore.QSignalBlocker(self.table):
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).data(QtCore.Qt.UserRole) == self._loaded_number:
                    self.table.setCurrentCell(row, column)
                    break

    # ---- edytor -------------------------------------------------------------------------
    def _editor(self):
        frame, lay, self.lbl_edit = pages.card("Narzędzie", "")
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
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
        self.txt_holder = QtWidgets.QLineEdit()
        self.spin_life = self._spin(0, 1e9, " min")
        self.spin_used = self._spin(0, 1e9, " min")
        self.spin_used.setSpecialValueText("")  # Zero is a value, not an unset usage counter.
        self.spin_z = self._spin(0, 1000, " mm")
        self.cmb_hand = QtWidgets.QComboBox()
        self.cmb_hand.addItem("prawe (M3)", 1)
        self.cmb_hand.addItem("lewe (M4)", -1)
        form.addRow("Numer T", self.spin_t)
        form.addRow("Gniazdo P", self.spin_p)
        form.addRow("Typ", self.cmb_type)
        form.addRow("Opis", self.txt_desc)
        form.addRow("Oprawka (nazwa/typ)", self.txt_holder)
        form.addRow("Trwałość planowana", self.spin_life)
        form.addRow("Zużycie (ręcznie)", self.spin_used)
        self.lbl_stl = QtWidgets.QLabel("Model STL *")
        self.stl_row = QtWidgets.QWidget()
        stl_layout = QtWidgets.QVBoxLayout(self.stl_row)
        stl_layout.setContentsMargins(0, 0, 0, 0)
        stl_layout.setSpacing(8)
        stl_picker = QtWidgets.QHBoxLayout()
        self.txt_stl = QtWidgets.QLineEdit()
        self.txt_stl.setMinimumWidth(180)
        self.txt_stl.setAccessibleName("Ścieżka modelu STL narzędzia")
        self.btn_stl = QtWidgets.QPushButton("Wybierz…")
        for widget in (self.txt_stl, self.btn_stl):
            widget.setMinimumHeight(44)
            stl_picker.addWidget(widget)
        self.btn_stl.clicked.connect(self._choose_stl)
        stl_layout.addLayout(stl_picker)
        hint = pages._label("Oś Z, czoło w 0. Symulacja używa walca zastępczego.", "lrtMuted")
        hint.setWordWrap(True)
        hint.setMinimumHeight(36)
        stl_layout.addWidget(hint)
        form.addRow(self.lbl_stl, self.stl_row)
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
        self.lbl_stl.setVisible(tid == "special_stl")
        self.stl_row.setVisible(tid == "special_stl")
        required = set(TYPES[tid].required) if tid else set()
        for name, (label, spin) in self.rows.items():
            show = name in allowed
            label.setVisible(show)
            spin.setVisible(show)
            label.setText(PARAMS[name].label + (" *" if name in required else ""))

    def _choose_stl(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Model narzędzia STL", self.txt_stl.text(), "STL (*.stl *.STL)")
        if filename:
            self.txt_stl.setText(filename)

    # ---- dane ---------------------------------------------------------------------------
    def show_history(self) -> None:
        if not self._open():
            return
        try:
            from linumert_tool_history import ToolHistoryDialog

            number = self.spin_t.value()
            records = self.db.history(number, limit=100)
            dialog = ToolHistoryDialog(self, number, records)
            try:
                dialog.exec_()
            finally:
                dialog.deleteLater()
        except Exception as exc:  # noqa: BLE001 - database/record errors stay within this dialog
            QtWidgets.QMessageBox.warning(self, "Historia niedostępna", str(exc))

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
            self.tbl_units = table_units(self.ini)
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
        self.lbl_count.setToolTip(f"Pola długości w mm. Tabela LinuxCNC: {self.tbl_units}.")

    def _selected(self) -> None:
        items = self.table.selectedItems()
        if not items or not self._open():
            return
        number = items[0].data(QtCore.Qt.UserRole)
        if number == self._loaded_number:
            return
        if not self._discard_edits():
            self._restore_selection()
            return
        try:
            tool = self.db.get(number)
        except (sqlite3.Error, ValueError) as exc:
            self._restore_selection()
            self.lbl_issue.setText(f"Nie można wczytać T{number}: {exc}")
            return
        if tool is not None:
            self.load(tool)
        else:
            self._restore_selection()
            self.lbl_issue.setText(f"T{number} nie jest już w bazie; formularz pozostaje bez zmian")

    def load(self, t: Tool) -> None:
        self._loading = True
        self._last_success = False
        try:
            self._load_fields(t)
        finally:
            self._loading = False
        self._edit_state(False)
        self._loaded_number = t.number

    def _load_fields(self, t: Tool) -> None:
        self.spin_t.setValue(t.number)
        self.spin_p.setValue(t.pocket)
        self.cmb_type.setCurrentIndex(max(self.cmb_type.findData(t.type), 0))
        self.txt_desc.setText(t.description)
        self.txt_holder.setText(t.holder)
        self.spin_life.setValue(t.life_min or 0)
        self.spin_used.setValue(t.used_min)
        self.txt_stl.setText(t.stl or "")
        self.spin_z.setValue(t.offsets.get("Z", 0.0))
        self.cmb_hand.setCurrentIndex(1 if t.params.get("hand", 1) < 0 else 0)
        for name, (_label, spin) in self.rows.items():
            value = t.params.get(name)
            if name == "d" and value is None:
                value = t.diameter
            if value is None:
                value = 0.0 if name == "d_wear" else spin.minimum()
            spin.setValue(value)
        self.lbl_issue.setText("")

    def new_tool(self) -> None:
        if not self._open():
            return
        if not self._discard_edits():
            return
        used = {t.number for t in self.db.tools()}
        pockets = {t.pocket for t in self.db.tools()}
        n = next(i for i in range(1, 100000) if i not in used)
        p = next(i for i in range(1, 100000) if i not in pockets)
        self.load(Tool(number=n, pocket=p, type="flat", params={"d": 6, "l": 30,
                                                               "flute_length": 15}))
        self._edit_state(True)
        self._loaded_number = None
        self._restore_selection()

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
        number = self.spin_t.value()
        original = self.db.get(number) if self.db is not None else None
        original = original or Tool(number=number, pocket=self.spin_p.value())
        # Model-Author: Codex. Keep metadata and axes absent from this editor.
        return replace(original, pocket=self.spin_p.value(), type=self.cmb_type.currentData(),
                       description=self.txt_desc.text().strip(), params=params,
                       holder=self.txt_holder.text().strip(),
                       life_min=self.spin_life.value() or None, used_min=self.spin_used.value(),
                       stl=self.txt_stl.text().strip() or None,
                       offsets={**original.offsets, "Z": self.spin_z.value()},
                       diameter=params.get("d"))

    def _busy(self) -> bool:
        try:
            s = linuxcnc.stat()
            s.poll()
        except linuxcnc.error as exc:
            message = f"Status LinuxCNC niedostępny: {exc}. Zmiana tabeli zablokowana."
        else:
            if s.interp_state == linuxcnc.INTERP_IDLE:
                return False
            message = "Tabela narzędzi: zmiana niedostępna w trakcie programu"
        self.lbl_issue.setText(message)
        self._last_success = False
        self.shell.show_alarm("warn", message)
        return True

    def _write_failed(self, exc) -> None:
        message = (f"Zapis tabeli nie powiódł się: {exc}. Baza mogła się zmienić; "
                   "sprawdź bazę i tool.tbl przed pracą.")
        self.lbl_issue.setText(message)
        self._last_success = False
        self.shell.show_alarm("err", message)

    def save(self) -> None:
        if not self._open():
            return
        if self._busy():
            return
        try:
            tool = self.current()
            save_tool(self.db, tool, self.tbl, units=self.tbl_units)
        except (ToolDBError, OSError, sqlite3.Error) as exc:
            self._write_failed(exc)
            return
        self._reload_linuxcnc()
        self.lbl_issue.setText(f"T{tool.number} zapisane w bazie i w {os.path.basename(self.tbl)}")
        self._last_success = True
        self._edit_state(False)
        self._loaded_number = tool.number
        self.refresh()
        self._restore_selection()

    def remove(self) -> None:
        if not self._open() or self._busy():
            return
        n = self.spin_t.value()
        try:
            if self.db.get(n) is None:
                return
            if QtWidgets.QMessageBox.question(self, "Narzędzia", f"Usunąć T{n} z tabeli?") != \
                    QtWidgets.QMessageBox.Yes:
                return
            self.db.remove(n)
            self.db.export_tbl(self.tbl, units=self.tbl_units)
        except (ToolDBError, OSError, sqlite3.Error) as exc:
            self._write_failed(exc)
            return
        self._reload_linuxcnc()
        self.lbl_issue.setText(f"T{n} usunięte z bazy i z {os.path.basename(self.tbl)}")
        self._last_success = True
        self._edit_state(False)
        self.lbl_edit.setText(f"T{n} · usunięte")
        self._loaded_number = None
        self.refresh()

    def _reload_linuxcnc(self) -> None:
        try:
            linuxcnc.command().load_tool_table()
        except Exception as exc:  # noqa: BLE001
            self.shell.show_alarm("warn", f"LinuxCNC nie wczytał tabeli narzędzi: {exc}")
        sim = getattr(self.shell, "sim", None)
        if sim is not None:
            QtCore.QTimer.singleShot(500, lambda: sim.client.send(cmd="tools"))

