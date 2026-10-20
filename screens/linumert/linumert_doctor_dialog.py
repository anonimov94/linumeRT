# SPDX-License-Identifier: GPL-2.0-or-later
"""Environment report in Diagnostics. Model-Author: Codex."""

import sys
from pathlib import Path

from PyQt5 import QtWidgets


class DoctorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raport środowiska")
        self.resize(900, 600)
        layout = QtWidgets.QVBoxLayout(self)
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setAccessibleName("Raport środowiska bez uruchamiania CNC")
        layout.addWidget(self.output)
        buttons = QtWidgets.QHBoxLayout()
        refresh = QtWidgets.QPushButton("Odśwież raport")
        refresh.clicked.connect(self.refresh_report)
        close = QtWidgets.QPushButton("Zamknij")
        close.clicked.connect(self.accept)
        for button in (refresh, close):
            button.setMinimumHeight(44)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh_report()

    def refresh_report(self):
        core = str(Path(__file__).resolve().parents[2] / "core")
        if core not in sys.path:
            sys.path.insert(0, core)
        try:
            from linumert.diag.doctor import format_report, inspect_environment
        except ImportError as exc:
            self.output.setPlainText(f"Raport niedostępny: {exc}")
            return
        self.output.setPlainText(format_report(inspect_environment()))
