# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline G-code editor: save a new copy, never command CNC. Model-Author: Codex."""

from pathlib import Path

from PyQt5 import QtWidgets

from linumert.programs.files import save_new_program


class ProgramEditor(QtWidgets.QDialog):
    def __init__(self, path, text, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.saved_path = None
        self.setWindowTitle("Edytuj G-code — zapisz kopię")
        self.resize(900, 650)
        layout = QtWidgets.QVBoxLayout(self)
        self.note = QtWidgets.QLabel(
            "Edycja do 256 KiB. Zapis tworzy nowy plik; nie wczytuje go do LinuxCNC.")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        if self.path.with_suffix(".lnx").is_file():
            warning = QtWidgets.QLabel(
                "Ten program ma źródło .lnx. Zmiany kopii G-code nie aktualizują źródła.")
            warning.setWordWrap(True)
            layout.addWidget(warning)
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setAccessibleName("Edytor kopii G-code")
        self.editor.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        layout.addWidget(self.editor, 1)
        row = QtWidgets.QHBoxLayout()
        save = QtWidgets.QPushButton("Zapisz nową kopię…")
        save.clicked.connect(self.choose_destination)
        close = QtWidgets.QPushButton("Zamknij")
        close.clicked.connect(self.reject)
        for button in (save, close):
            button.setMinimumHeight(44)
            row.addWidget(button)
        layout.addLayout(row)

    def choose_destination(self):
        proposed = self.path.with_name(self.path.stem + "_edited.ngc")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Nowa kopia G-code", str(proposed), "G-code (*.ngc);;Wszystkie (*)",
            options=QtWidgets.QFileDialog.DontConfirmOverwrite)
        if filename:
            self.save_to(Path(filename))

    def save_to(self, path):
        try:
            save_new_program(path, self.editor.toPlainText())
        except FileExistsError:
            self.note.setText(
                "Plik już istnieje. Wybierz nową nazwę — oryginał pozostaje bez zmian.")
            return False
        except (OSError, ValueError) as exc:
            self.note.setText(f"Nie zapisano kopii: {exc}")
            return False
        self.saved_path = path
        self.editor.document().setModified(False)
        self.accept()
        return True

    def reject(self):
        if self.editor.document().isModified():
            answer = QtWidgets.QMessageBox.question(
                self, "Niezapisane zmiany", "Zamknąć i odrzucić zmiany?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        super().reject()
