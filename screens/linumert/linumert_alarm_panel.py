# SPDX-License-Identifier: GPL-2.0-or-later
"""Trzy ostatnie alarmy i pojedynczy/podwójny Reset. Model-Author: Codex."""
from linumert_i18n import translate
from PyQt5 import QtCore, QtWidgets


class AlarmPanel(QtWidgets.QFrame):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.entries = []
        self.active = set()
        self.setObjectName("lrtAlarm")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 8, 4)
        rows = QtWidgets.QVBoxLayout()
        rows.setSpacing(0)
        self.rows = [QtWidgets.QLabel("—") for _ in range(3)]
        for row in self.rows:
            row.setTextFormat(QtCore.Qt.PlainText)
            row.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
            rows.addWidget(row)
        layout.addLayout(rows, 1)
        self.reset = QtWidgets.QPushButton(translate("AlarmPanel", "Reset"))
        self.reset.setToolTip(translate(
            "AlarmPanel", "Once: clear resolved alarms. Twice: also acknowledge E-STOP."))
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: shell.reset_alarms(False))
        self.reset.clicked.connect(self.clicked)
        layout.addWidget(self.reset)
        self.render()

    def clicked(self):
        if self.timer.isActive():
            self.timer.stop()
            self.shell.reset_alarms(True)
        else:
            self.timer.start(QtWidgets.QApplication.doubleClickInterval())

    def add(self, level, text, source=""):
        self.entries = [e for e in self.entries if e[1:] != (text, source)]
        self.entries.insert(0, (level, text, source))
        self.entries = self.entries[:200]
        self.render()

    def acknowledge(self):
        self.entries = [e for e in self.entries if e[2] in self.active]
        self.render()

    def render(self):
        for row, entry in zip(self.rows, self.entries[:3] + [None] * 3):
            row.setText(entry[1] if entry else "—")
            row.setToolTip(entry[1] if entry else "")
        level = self.entries[0][0] if self.entries else "info"
        self.setProperty("level", level)
        self.style().unpolish(self)
        self.style().polish(self)
