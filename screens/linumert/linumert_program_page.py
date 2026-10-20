# SPDX-License-Identifier: GPL-2.0-or-later
"""Wybór, podgląd, sprawdzenie i edycja programu bez uruchamiania ruchu.

Model-Author: Codex; sprawdzanie składni i edycja: Claude (2026-10-19).
"""

import os
import sys
from pathlib import Path

from PyQt5 import QtGui, QtWidgets
from qtvcp.core import Action, Info

from linumert_shell_pages import _label, card

ACTION, INFO = Action(), Info()
MAX_BYTES = 8 * 1024 * 1024
PREVIEW_LINES = 2000
_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))


def _checker():
    """Lekser G-code z rdzenia (pyyaml); None, gdy rdzeń niedostępny w tym interpreterze."""
    core = os.path.join(_ROOT, "core")
    if core not in sys.path:
        sys.path.insert(0, core)
    try:
        from linumert.programs.lexer import check
    except Exception:  # noqa: BLE001 - przycisk zostaje wyłączony z wyjaśnieniem
        return None
    return check


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
        self.check = QtWidgets.QPushButton("Sprawdź")
        self.check.setToolTip("Składnia G-code (bez LinuxCNC, bez ruchu)")
        self.check.clicked.connect(self.check_program)
        self.edit = QtWidgets.QPushButton("Edytuj")
        self.edit.setCheckable(True)
        self.edit.toggled.connect(self.toggle_edit)
        for button in (self.choose, self.check, self.edit, self.load):
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

    def check_program(self):
        """Sprawdzenie składni całego programu; kursor na pierwszym błędzie."""
        check = _checker()
        if check is None:
            self.message.setText("Sprawdzanie niedostępne: brak rdzenia linumert (pyyaml).")
            return []
        text = self.preview.toPlainText() if self.edit.isChecked() else self.text
        issues = check(text)
        if not issues:
            self.message.setText(f"Składnia poprawna ({len(text.splitlines())} linii).")
            return []
        lines = "; ".join(i.message() for i in issues[:3])
        more = f" (+{len(issues) - 3})" if len(issues) > 3 else ""
        self.message.setText(f"Błędy: {len(issues)} — {lines}{more}")
        block = self.preview.document().findBlockByNumber(issues[0].line - 1)
        if block.isValid():
            cursor = QtGui.QTextCursor(block)
            self.preview.setTextCursor(cursor)
            self.preview.centerCursor()
        return issues

    def toggle_edit(self, on):
        """Edycja w podglądzie; ponowne kliknięcie zapisuje plik (nie w trakcie programu)."""
        if on:
            if self.path is None or len(self.text.splitlines()) > PREVIEW_LINES:
                self.message.setText("Edycja tylko dla wybranego programu do "
                                     f"{PREVIEW_LINES} linii.")
                self.edit.setChecked(False)
                return
            self.preview.setReadOnly(False)
            self.edit.setText("Zapisz")
            self.message.setText("Edycja: kliknij „Zapisz”, aby zapisać plik.")
            self.refresh()
            return
        self.preview.setReadOnly(True)
        self.edit.setText("Edytuj")
        self.refresh()
        if self.path is None:
            return
        text = self.preview.toPlainText()
        if text.rstrip("\n") == self.text.rstrip("\n"):
            self.message.setText("Bez zmian.")
            return
        if self.shell.s.running and str(self.path) == self.shell.s.file:
            self.message.setText("Nie zapisano: program jest w toku.")
            self.preview.setPlainText(self.text)
            return
        tmp = self.path.with_name(f".{self.path.name}.tmp")
        try:
            tmp.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            self.message.setText(f"Nie zapisano: {exc}")
            return
        self.text = text.rstrip("\n") + "\n"
        active = str(self.path) == self.shell.s.file
        self.message.setText("Zapisano." + (" Wczytaj ponownie do LinuxCNC, aby użyć zmian."
                                            if active else ""))

    def load_program(self):
        if self.path is not None and not self.shell.s.running:
            ACTION.OPEN_PROGRAM(str(self.path))

    def refresh(self):
        if self.shell.s.file != self._seen_active:
            self._seen_active = self.shell.s.file
            if self.path is None and self._seen_active:
                self.show_file(self._seen_active)
        running = self.shell.s.running
        self.load.setEnabled(self.path is not None and not running and not self.edit.isChecked())
        self.check.setEnabled(self.path is not None)
        self.load.setToolTip("Najpierw zatrzymaj program" if running else "Nie uruchamia cyklu")
        self.active.setText(f"aktywny: {Path(self.shell.s.file).name}" if self.shell.s.file else
                            "brak aktywnego programu")
