# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only tool history, with parameter changes. Model-Author: Codex."""

import json
from datetime import datetime, timezone

from PyQt5 import QtWidgets

from linumert.tools.types import PARAMS, TYPES


def _fields(snapshot):
    if snapshot is None:
        return {}
    names = {"number": "Numer T", "pocket": "Gniazdo P", "description": "Opis",
             "holder": "Oprawka", "stl": "Model STL", "diameter": "D w tabeli [mm]",
             "life_min": "Trwałość [min]", "used_min": "Zużycie [min]"}
    values = {label: snapshot.get(key) for key, label in names.items()}
    kind = snapshot.get("type")
    values["Typ"] = TYPES[kind].label if kind in TYPES else kind
    for key, value in json.loads(snapshot.get("params") or "{}").items():
        spec = PARAMS.get(key)
        label = f"{spec.label} [{spec.unit}]" if spec and spec.unit else spec.label if spec else key
        values[label] = value
    for axis, value in json.loads(snapshot.get("offsets") or "{}").items():
        values[f"Korekcja {axis} [{'°' if axis in 'ABC' else 'mm'}]"] = value
    for key, value in json.loads(snapshot.get("lathe") or "{}").items():
        values[f"Tokarka {key}"] = value
    return values


class ToolHistoryDialog(QtWidgets.QDialog):
    def __init__(self, parent, number, records):
        super().__init__(parent)
        self.setObjectName("lrtRoot")
        self.setWindowTitle(f"Historia narzędzia T{number}")
        self.resize(1000, 600)
        self.records = list(reversed(records))
        self.changes = [(_fields(record["before"]), _fields(record["after"]))
                        for record in self.records]
        layout = QtWidgets.QVBoxLayout(self)
        caption = QtWidgets.QLabel(
            f"T{number}: ostatnie {len(records)} wpisów (maks. 100), najnowsze na górze. "
            "Historia bazy — tylko podgląd. Nie potwierdza wczytania tabeli przez CNC.")
        caption.setWordWrap(True)
        layout.addWidget(caption)
        row = QtWidgets.QHBoxLayout()
        self.events = QtWidgets.QListWidget()
        self.events.setObjectName("lrtLog")
        self.events.setAccessibleName("Zmiany narzędzia")
        self.details = QtWidgets.QTableWidget(0, 3)
        self.details.setObjectName("lrtTable")
        self.details.setHorizontalHeaderLabels(["Pole", "Przed", "Po"])
        self.details.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.details.verticalHeader().hide()
        self.details.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.details.horizontalHeader().setStretchLastSection(True)
        row.addWidget(self.events, 2)
        row.addWidget(self.details, 3)
        layout.addLayout(row, 1)
        actions = {"add": "Dodanie", "update": "Zmiana", "remove": "Usunięcie", "import": "Import"}
        for record in self.records:
            stamp = datetime.fromtimestamp(record["time"], timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC")
            action = actions.get(record["action"], record["action"])
            self.events.addItem(f"{stamp}\n{action} · {record['source']}")
        self.events.currentRowChanged.connect(self._selected)
        if records:
            self.events.setCurrentRow(0)
        else:
            self.events.addItem("Brak wpisów dla tego numeru T")
        close = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        close.button(QtWidgets.QDialogButtonBox.Close).setText("Zamknij")
        layout.addWidget(close)

    def _selected(self, index):
        if not 0 <= index < len(self.records):
            return
        before, after = self.changes[index]
        keys = [key for key in dict.fromkeys((*before, *after))
                if before.get(key) != after.get(key)]
        self.details.setRowCount(len(keys))
        for row, key in enumerate(keys):
            for col, value in enumerate((key, before.get(key), after.get(key))):
                text = "—" if value is None or value == "" else str(value)
                self.details.setItem(row, col, QtWidgets.QTableWidgetItem(text))
