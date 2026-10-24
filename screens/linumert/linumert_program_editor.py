# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline G-code editor: save a new copy, never command CNC. Model-Author: Codex."""

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

CHECK_BYTES = 64 * 1024
MAX_ISSUES = 100


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
        self.issues = QtWidgets.QListWidget()
        self.issues.setAccessibleName("Błędy edytowanej kopii G-code")
        self.issues.setMaximumHeight(140)
        self.issues.itemActivated.connect(self.show_issue)
        self.issues.itemClicked.connect(self.show_issue)
        self.issues.hide()
        layout.addWidget(self.issues)
        self.validation = QtWidgets.QLabel("Bieżąca treść nie została sprawdzona.")
        self.validation.setWordWrap(True)
        layout.addWidget(self.validation)
        self.editor.textChanged.connect(self.invalidate_check)
        row = QtWidgets.QHBoxLayout()
        self.check_button = QtWidgets.QPushButton("Sprawdź bieżącą treść")
        self.check_button.clicked.connect(self.check_text)
        save = QtWidgets.QPushButton("Zapisz nową kopię…")
        save.clicked.connect(self.choose_destination)
        close = QtWidgets.QPushButton("Zamknij")
        close.clicked.connect(self.reject)
        for button in (self.check_button, save, close):
            button.setMinimumHeight(44)
            row.addWidget(button)
        layout.addLayout(row)

    def invalidate_check(self):
        self.issues.clear()
        self.issues.hide()
        self.editor.setExtraSelections([])
        self.validation.setText("Bieżąca treść nie została sprawdzona.")

    def check_text(self):
        self.invalidate_check()
        text = self.editor.toPlainText()
        if len(text.encode("utf-8")) > CHECK_BYTES:
            self.validation.setText("Kontrola do 64 KiB. Treść nie została sprawdzona.")
            return
        try:
            from linumert.programs.lexer import check

            issues = check(text)
            for issue in issues[:MAX_ISSUES]:
                item = QtWidgets.QListWidgetItem(
                    f"{issue.line}:{issue.col} · {issue.code} · {issue.message()}")
                item.setData(QtCore.Qt.UserRole, (issue.line, issue.col))
                self.issues.addItem(item)
        except (ImportError, OSError, ValueError, RecursionError) as exc:
            self.issues.clear()
            self.validation.setText(f"Nie ukończono kontroli składni: {exc}")
            return
        self.issues.setVisible(bool(issues))
        result = f"Błędy składni: {len(issues)}." if issues else "Nie wykryto błędów składni."
        if len(issues) > MAX_ISSUES:
            result += f" Lista pokazuje pierwsze {MAX_ISSUES}."
        self.validation.setText(result + " Kontrola nie sprawdza ruchu ani semantyki LinuxCNC.")
        if issues:
            self.show_issue(self.issues.item(0))

    def show_issue(self, item):
        line, col = item.data(QtCore.Qt.UserRole)
        block = self.editor.document().findBlockByNumber(line - 1)
        cursor = QtGui.QTextCursor(block)
        prefix = block.text()[:col - 1]
        cursor.setPosition(block.position() + len(prefix.encode("utf-16-le")) // 2)
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()
        mark = QtWidgets.QTextEdit.ExtraSelection()
        mark.cursor = cursor
        mark.format.setBackground(self.palette().alternateBase())
        mark.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        self.editor.setExtraSelections([mark])
        self.editor.setFocus()

    def choose_destination(self):
        proposed = self.path.with_name(self.path.stem + "_edited.ngc")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Nowa kopia G-code", str(proposed), "G-code (*.ngc);;Wszystkie (*)",
            options=QtWidgets.QFileDialog.DontConfirmOverwrite)
        if filename:
            self.save_to(Path(filename))

    def save_to(self, path):
        try:
            from linumert.programs.files import save_new_program

            save_new_program(path, self.editor.toPlainText())
        except FileExistsError:
            self.note.setText(
                "Plik już istnieje. Wybierz nową nazwę — oryginał pozostaje bez zmian.")
            return False
        except (OSError, ValueError, ImportError) as exc:
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
