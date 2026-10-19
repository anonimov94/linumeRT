# SPDX-License-Identifier: GPL-2.0-or-later
"""Wybór i podgląd programu bez uruchamiania ruchu. Model-Author: Codex."""

import os
from pathlib import Path

from PyQt5 import QtWidgets
from qtvcp.core import Action, Info

from linumert_shell_pages import _label, card

ACTION, INFO = Action(), Info()
MAX_BYTES = 8 * 1024 * 1024
PREVIEW_LINES = 2000


class ProgramPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.path = None
        self.text = ""
        self._seen_active = ""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        frame, body, self.active = card("Program", "")
        self.filename = _label("Wybierz program do podglądu", "lrtMuted")
        self.filename.setWordWrap(True)
        body.addWidget(self.filename)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.preview.setAccessibleName("Podgląd G-code")
        body.addWidget(self.preview, 1)
        self.message = _label("Sam wybór pliku nie wczytuje go do LinuxCNC.", "lrtMuted")
        self.message.setWordWrap(True)
        body.addWidget(self.message)
        buttons = QtWidgets.QHBoxLayout()
        self.choose = QtWidgets.QPushButton("Wybierz plik…")
        self.choose.clicked.connect(self.choose_file)
        self.load = QtWidgets.QPushButton("Wczytaj do LinuxCNC")
        self.load.clicked.connect(self.load_program)
        for button in (self.choose, self.load):
            button.setMinimumHeight(44)
            buttons.addWidget(button)
        body.addLayout(buttons)
        layout.addWidget(frame, 1)
        self.refresh()

    def choose_file(self):
        root = str(self.path.parent) if self.path else os.path.expanduser(INFO.PROGRAM_PREFIX)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Program G-code", root, "Programy (*.ngc *.nc *.tap *.gcode);;Wszystkie (*)")
        if path:
            self.show_file(path)

    def show_file(self, filename):
        try:
            path = Path(filename).resolve()
            with path.open("rb") as source:
                data = source.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Program przekracza limit podglądu 8 MiB.")
            text = data.decode("utf-8-sig", errors="replace")
        except (OSError, ValueError) as exc:
            self.message.setText(f"Nie można odczytać programu: {exc}")
            return False
        self.path, self.text = path, text
        lines = text.splitlines()
        self.preview.setPlainText("\n".join(lines[:PREVIEW_LINES]))
        self.filename.setText(f"{path}\n{len(lines)} linii · {len(data)} bajtów")
        note = f"Podgląd pierwszych {PREVIEW_LINES} linii. " if len(lines) > PREVIEW_LINES else ""
        if path.with_suffix(".lnx").is_file():
            note += "Program wygenerowany z .lnx — zmiany wprowadzaj w źródle. "
        self.message.setText(note + "Wczytanie wymaga przycisku „Wczytaj do LinuxCNC”.")
        self.refresh()
        return True

    def load_program(self):
        if self.path is not None and not self.shell.s.running:
            ACTION.OPEN_PROGRAM(str(self.path))

    def refresh(self):
        if self.shell.s.file != self._seen_active:
            self._seen_active = self.shell.s.file
            if self.path is None and self._seen_active:
                self.show_file(self._seen_active)
        running = self.shell.s.running
        self.load.setEnabled(self.path is not None and not running)
        self.load.setToolTip("Najpierw zatrzymaj program" if running else "Nie uruchamia cyklu")
        self.active.setText(f"aktywny: {Path(self.shell.s.file).name}" if self.shell.s.file else
                            "brak aktywnego programu")
