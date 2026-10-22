# SPDX-License-Identifier: GPL-2.0-or-later
"""Search and export diagnostic messages. Model-Author: Codex."""

import hashlib
import os
import sys
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

_CORE = str(Path(__file__).resolve().parents[2] / "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)
from linumert.diag.journal import Journal  # noqa: E402


def journal_path():
    profile = str(Path(os.environ.get("INI_FILE_NAME", "offline")).resolve())
    key = hashlib.sha256(profile.encode("utf-8")).hexdigest()[:16]
    root = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.GenericDataLocation)
    return Path(root) / "linumert" / f"diagnostic-{key}.sqlite3"


class LogView(QtWidgets.QWidget):
    def __init__(self, colors, parent=None, path=None):
        super().__init__(parent)
        self.colors = colors
        self.path = Path(path) if path is not None else journal_path()
        self.journal = Journal(self.path)
        self.destroyed.connect(lambda: self.journal.close())
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        filters = QtWidgets.QHBoxLayout()
        self.level = QtWidgets.QComboBox()
        for title, value in (("Wszystkie poziomy", ""), ("Błędy", "err"),
                             ("Ostrzeżenia", "warn"), ("Informacje", "info")):
            self.level.addItem(title, value)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Szukaj komunikatu, kodu lub daty…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Szukaj w historii komunikatów")
        self.export = QtWidgets.QPushButton("Eksport CSV…")
        for widget in (self.level, self.search, self.export):
            widget.setMinimumHeight(44)
            filters.addWidget(widget, 1 if widget is self.search else 0)
        layout.addLayout(filters)
        self.list = QtWidgets.QListWidget()
        self.list.setObjectName("lrtLog")
        layout.addWidget(self.list)
        self.summary = QtWidgets.QLabel()
        self.summary.setObjectName("lrtMuted")
        self.summary.setTextFormat(QtCore.Qt.PlainText)
        self.summary.setWordWrap(True)
        self.summary.setToolTip(str(self.path))
        layout.addWidget(self.summary)
        self.level.currentIndexChanged.connect(self.refresh)
        self.search.textChanged.connect(self.refresh)
        self.export.clicked.connect(self.export_csv)
        self.refresh()

    def add(self, level, message):
        self.journal.add(level, message)
        self.refresh()

    def refresh(self):
        rows = self.journal.matching(self.level.currentData(), self.search.text())
        self.list.clear()
        for stamp, level, message in rows[:200]:
            item = QtWidgets.QListWidgetItem(f"{stamp}  {message}")
            item.setToolTip(message)
            color = {"err": "err", "warn": "amber"}.get(level, "fg2")
            item.setForeground(QtGui.QColor(self.colors[color]))
            self.list.addItem(item)
        self.summary.setText(
            f"Widoczne: {min(200, len(rows))} z {len(rows)} pasujących. "
            "Historia: ostatnie 1000 wpisów; CSV obejmuje wszystkie pasujące. "
            + (self.journal.warning or "Zapis między uruchomieniami włączony."))

    def export_csv(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Eksport historii komunikatów", "komunikaty.csv", "CSV (*.csv)")
        if not filename:
            return
        data = self.journal.csv(self.level.currentData(), self.search.text()).encode("utf-8-sig")
        target = QtCore.QSaveFile(filename)
        if (not target.open(QtCore.QIODevice.WriteOnly) or target.write(data) != len(data)
                or not target.commit()):
            target.cancelWriting()
            QtWidgets.QMessageBox.warning(self, "Eksport nieudany", target.errorString())
