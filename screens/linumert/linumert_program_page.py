# SPDX-License-Identifier: GPL-2.0-or-later
"""Wybór i podgląd programu bez uruchamiania ruchu. Model-Author: Codex."""

import os
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Action, Info

from linumert.programs.lexer import check
from linumert_shell_pages import _label, card

ACTION, INFO = Action(), Info()
MAX_BYTES = 8 * 1024 * 1024
PREVIEW_LINES = 2000
CHECK_BYTES = 64 * 1024
MAX_ISSUES = 100


class ProgramPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.path = None
        self.text = ""
        self._preview_start = 0
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
        self.issues = QtWidgets.QListWidget()
        self.issues.setObjectName("lrtLog")
        self.issues.setAccessibleName("Błędy składni G-code")
        self.issues.setMaximumHeight(140)
        self.issues.itemClicked.connect(self.show_issue)
        self.issues.itemActivated.connect(self.show_issue)
        self.issues.hide()
        body.addWidget(self.issues)
        self.message = _label("Sam wybór pliku nie wczytuje go do LinuxCNC.", "lrtMuted")
        self.message.setWordWrap(True)
        body.addWidget(self.message)
        buttons = QtWidgets.QHBoxLayout()
        self.choose = QtWidgets.QPushButton("Wybierz plik…")
        self.choose.clicked.connect(self.choose_file)
        self.load = QtWidgets.QPushButton("Wczytaj do LinuxCNC")
        self.load.clicked.connect(self.load_program)
        self.check_button = QtWidgets.QPushButton("Sprawdź składnię")
        self.check_button.clicked.connect(self.check_program)
        for button in (self.choose, self.check_button, self.load):
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
        self.issues.clear()
        self.issues.hide()
        self._preview_start = 0
        lines = text.splitlines()
        self.preview.setPlainText("\n".join(lines[:PREVIEW_LINES]))
        self.filename.setText(f"{path}\n{len(lines)} linii · {len(data)} bajtów")
        note = f"Podgląd pierwszych {PREVIEW_LINES} linii. " if len(lines) > PREVIEW_LINES else ""
        if path.with_suffix(".lnx").is_file():
            note += "Program wygenerowany z .lnx — zmiany wprowadzaj w źródle. "
        self.message.setText(note + "Wczytanie wymaga przycisku „Wczytaj do LinuxCNC”.")
        self.refresh()
        return True

    def check_program(self):
        # Re-read the file: a previous result must not describe an older disk version.
        if self.path is None or not self.show_file(self.path):
            return
        if len(self.text.encode("utf-8")) > CHECK_BYTES:
            self.message.setText("Kontrola w tym widoku: do 64 KiB. Plik nie został sprawdzony.")
            return
        try:
            issues = check(self.text)
        except (ValueError, RecursionError) as exc:
            self.message.setText(f"Nie ukończono kontroli składni: {exc}")
            return
        for issue in issues[:MAX_ISSUES]:
            item = QtWidgets.QListWidgetItem(
                f"{issue.line}:{issue.col} · {issue.code} · {issue.message()}")
            item.setData(QtCore.Qt.UserRole, (issue.line, issue.col))
            self.issues.addItem(item)
        self.issues.setVisible(bool(issues))
        result = f"Błędy składni: {len(issues)}." if issues else "Nie wykryto błędów składni."
        if len(issues) > MAX_ISSUES:
            result += f" Lista pokazuje pierwsze {MAX_ISSUES}."
        self.message.setText(result + " Kontrola składni nie sprawdza ruchu ani semantyki LinuxCNC.")

    def show_issue(self, item):
        line, col = item.data(QtCore.Qt.UserRole)
        lines = self.text.splitlines()
        self._preview_start = max(0, line - PREVIEW_LINES // 2)
        end = min(len(lines), self._preview_start + PREVIEW_LINES)
        self.preview.setPlainText("\n".join(lines[self._preview_start:end]))
        block = self.preview.document().findBlockByNumber(line - 1 - self._preview_start)
        cursor = QtGui.QTextCursor(block)
        # Lexer columns count Unicode codepoints; QTextCursor positions count UTF-16 units.
        prefix = lines[line - 1][:col - 1]
        cursor.setPosition(block.position() + len(prefix.encode("utf-16-le")) // 2)
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        self.preview.setTextCursor(cursor)
        self.preview.centerCursor()
        self.filename.setText(
            f"{self.path}\nPodgląd linii {self._preview_start + 1}–{end}; błąd {line}:{col}")

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
        self.check_button.setEnabled(self.path is not None and not running)
        self.load.setToolTip("Najpierw zatrzymaj program" if running else "Nie uruchamia cyklu")
        self.active.setText(f"aktywny: {Path(self.shell.s.file).name}" if self.shell.s.file else
                            "brak aktywnego programu")
