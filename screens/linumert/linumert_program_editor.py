# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline G-code editor: save a new copy, never command CNC. Model-Author: Codex."""

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
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
        search = QtWidgets.QHBoxLayout()
        self.find_text = QtWidgets.QLineEdit()
        self.find_text.setPlaceholderText("Znajdź (rozróżnia wielkość liter)")
        self.find_text.setAccessibleName("Szukany tekst")
        self.replace_text = QtWidgets.QLineEdit()
        self.replace_text.setPlaceholderText("Zamień na")
        self.replace_text.setAccessibleName("Tekst zamienny")
        self.find_next = QtWidgets.QPushButton("Znajdź następny")
        self.replace_one = QtWidgets.QPushButton("Zamień")
        self.replace_all = QtWidgets.QPushButton("Zamień wszystkie")
        self.find_next.clicked.connect(self.find_match)
        self.find_text.returnPressed.connect(self.find_match)
        self.replace_one.clicked.connect(self.replace_match)
        self.replace_all.clicked.connect(self.replace_matches)
        for widget in (self.find_text, self.replace_text, self.find_next,
                       self.replace_one, self.replace_all):
            widget.setMinimumHeight(44)
            search.addWidget(widget)
        layout.addLayout(search)
        self.search_result = QtWidgets.QLabel("Wyszukiwanie dosłowne w całej kopii programu.")
        layout.addWidget(self.search_result)
        self.find_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence.Find, self)
        self.find_shortcut.activated.connect(self.focus_search)
        # Enter in the search field must not trigger the dialog's save/check buttons.
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
        self.limit_pool = ThreadPoolExecutor(max_workers=1)
        self.limit_job = None
        self.limit_revision = 0
        self.limit_timer = QtCore.QTimer(self)
        self.limit_timer.setInterval(150)
        self.limit_timer.timeout.connect(self.poll_limits)
        row = QtWidgets.QHBoxLayout()
        self.check_button = QtWidgets.QPushButton("Sprawdź bieżącą treść")
        self.check_button.clicked.connect(self.check_text)
        self.limits_button = QtWidgets.QPushButton("Sprawdź limity osi")
        self.limits_button.setToolTip(
            "Porównuje ścieżkę programu (z układem G54 i korektą narzędzia) z limitami osi w INI")
        self.limits_button.clicked.connect(self.check_limits)
        save = QtWidgets.QPushButton("Zapisz nową kopię…")
        save.clicked.connect(self.choose_destination)
        close = QtWidgets.QPushButton("Zamknij")
        close.clicked.connect(self.reject)
        for button in (self.check_button, self.limits_button, save, close):
            button.setMinimumHeight(44)
            row.addWidget(button)
        layout.addLayout(row)
        for button in self.findChildren(QtWidgets.QPushButton):
            button.setAutoDefault(False)

    def focus_search(self):
        self.find_text.setFocus()
        self.find_text.selectAll()

    def find_match(self):
        needle = self.find_text.text()
        if not needle:
            self.search_result.setText("Wpisz szukany tekst.")
            return False
        document = self.editor.document()
        flags = QtGui.QTextDocument.FindCaseSensitively
        cursor = document.find(needle, self.editor.textCursor(), flags)
        wrapped = cursor.isNull()
        if wrapped:
            cursor = document.find(needle, 0, flags)
        if cursor.isNull():
            self.search_result.setText("Nie znaleziono tekstu.")
            return False
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()
        self.search_result.setText("Znaleziono od początku programu." if wrapped else "Znaleziono.")
        return True

    def replace_match(self):
        needle = self.find_text.text()
        cursor = self.editor.textCursor()
        if not needle or cursor.selectedText() != needle:
            self.find_match()
            return
        cursor.insertText(self.replace_text.text())
        self.editor.setTextCursor(cursor)
        self.find_match()

    def replace_matches(self):
        from linumert.programs.files import EDIT_BYTES

        needle = self.find_text.text()
        if not needle:
            self.search_result.setText("Wpisz szukany tekst.")
            return
        text = self.editor.toPlainText()
        count = text.count(needle)
        replacement = self.replace_text.text()
        size = len(text.encode("utf-8")) + count * (
            len(replacement.encode("utf-8")) - len(needle.encode("utf-8")))
        if size > EDIT_BYTES:
            self.search_result.setText("Zamiana przekroczyłaby limit edycji 256 KiB.")
            return
        if count and needle != replacement:
            cursor = self.editor.textCursor()
            cursor.beginEditBlock()
            cursor.select(QtGui.QTextCursor.Document)
            cursor.insertText(text.replace(needle, replacement))
            cursor.endEditBlock()
            self.editor.setTextCursor(cursor)
        self.search_result.setText(f"Wystąpienia: {count}. Cofnij zmiany: Ctrl+Z w edytorze.")

    def invalidate_check(self):
        self.limit_revision += 1
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

    @staticmethod
    def machine_ini():
        ini = os.environ.get("INI_FILE_NAME", "")
        return ini if ini and Path(ini).is_file() else ""

    def check_limits(self):
        ini = self.machine_ini()
        if not ini:
            self.validation.setText("Brak pliku INI maszyny: nie można sprawdzić limitów osi.")
            return
        if self.limit_job is not None:
            return
        from linumert.programs.limits import check_ngc, parameter_file

        fd, tmp = tempfile.mkstemp(prefix="linumert-limity-", suffix=".ngc")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(self.editor.toPlainText())
        self.limit_job = (self.limit_pool.submit(check_ngc, tmp, ini, parameter_file(ini)),
                          tmp, self.limit_revision)
        self.limits_button.setEnabled(False)
        self.validation.setText("Sprawdzanie limitów osi…")
        self.limit_timer.start()

    def poll_limits(self):
        if self.limit_job is None:
            self.limit_timer.stop()
            return
        future, tmp, revision = self.limit_job
        if not future.done():
            return
        self.limit_timer.stop()
        self.limit_job = None
        self.limits_button.setEnabled(True)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        if revision != self.limit_revision:
            self.validation.setText("Treść zmieniona: sprawdź limity osi ponownie.")
            return
        try:
            found = future.result()
        except Exception as exc:  # noqa: BLE001 - brak rs274 albo błąd programu: komunikat
            self.validation.setText(f"Limity osi niesprawdzone: {exc}")
            return
        self.issues.clear()
        for v in found[:MAX_ISSUES]:
            item = QtWidgets.QListWidgetItem(v.message())
            item.setData(QtCore.Qt.UserRole, (v.line or 1, 1))
            self.issues.addItem(item)
        self.issues.setVisible(bool(found))
        if found:
            self.validation.setText(
                f"Ruchy poza limitami osi: {len(found)}. Program zatrzymałby się w trakcie "
                "obróbki; popraw program albo układ detalu (G54). Sprawdzane są punkty końcowe.")
            self.show_issue(self.issues.item(0))
        else:
            self.validation.setText("Punkty końcowe ruchów mieszczą się w limitach osi "
                                    "(łuki między punktami nie są sprawdzane).")

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
