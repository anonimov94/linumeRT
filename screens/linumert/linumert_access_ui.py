# SPDX-License-Identifier: GPL-2.0-or-later
"""Poziomy dostępu na ekranie (sesja 036): przycisk roli, logowanie PIN-em, strażnik uprawnień.

Model-Author: Claude · 2026-10-24. Logika w `linumert.access` (rdzeń, bez UI). Uprawnienia
porządkują edycję danych na ekranie; nie są funkcją bezpieczeństwa (CLAUDE.md §6).
"""

import os
from pathlib import Path

from linumert.access import ROLE_LABEL, ROLES, AccessError, AccessStore, Session, required_role
from PyQt5 import QtCore, QtGui, QtWidgets

DB_NAME = "linumert_access.sqlite"


def access_db_path(ini):
    """`[LINUMERT]ACCESS_DB` (względem katalogu INI), domyślnie obok INI maszyny."""
    if not ini:
        return Path.home() / ".local/share/linumert" / DB_NAME
    ini = Path(ini)
    section, value = "", ""
    try:
        for raw in ini.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip().upper()
            elif section == "LINUMERT" and "=" in line:
                key, val = (part.strip() for part in line.split("=", 1))
                if key.upper() == "ACCESS_DB" and val:
                    value = val
    except OSError:
        pass
    path = Path(os.path.expanduser(value)) if value else Path(DB_NAME)
    return path if path.is_absolute() else ini.parent / path


def open_session(ini):
    """Sesja dostępu albo (None, powód) przy błędzie bazy — ekran działa dalej bez ról."""
    try:
        return Session(AccessStore(access_db_path(ini))), ""
    except (OSError, Exception) as exc:  # sqlite3.Error i błędy uprawnień katalogu
        return None, f"Poziomy dostępu niedostępne: {exc}"


def require(shell, permission, detail=""):
    """True, gdy bieżąca rola może; inaczej ostrzeżenie z wymaganą rolą i wpis w audycie."""
    session = getattr(shell, "access", None)
    if session is None or session.check(permission, detail):
        return True
    need = ROLE_LABEL[required_role(permission)]
    shell.show_alarm("warn", f"Wymagana rola: {need} — zaloguj się przyciskiem roli w górnym pasku")
    return False


def audit(shell, action, detail=""):
    session = getattr(shell, "access", None)
    if session is not None:
        session.store.audit(session.role, action, detail)


class PinDialog(QtWidgets.QDialog):
    """Wybór roli i PIN z dotykowej klawiatury (przyciski ≥ 44 px)."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Poziom dostępu")
        lay = QtWidgets.QVBoxLayout(self)
        self.role = QtWidgets.QComboBox()
        configured = session.store.configured_roles()
        for role in ROLES:
            if role == "operator" or role in configured:
                self.role.addItem(ROLE_LABEL[role], role)
        self.role.setCurrentIndex(max(0, self.role.findData(session.login_role)))
        self.role.setMinimumHeight(44)
        lay.addWidget(QtWidgets.QLabel(f"Bieżąca rola: {ROLE_LABEL[session.role]}"))
        lay.addWidget(self.role)
        self.pin = QtWidgets.QLineEdit()
        self.pin.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pin.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r"\d{0,12}"), self.pin))
        self.pin.setPlaceholderText("PIN")
        self.pin.setMinimumHeight(44)
        lay.addWidget(self.pin)
        pad = QtWidgets.QGridLayout()
        keys = [str(d) for d in range(1, 10)] + ["⌫", "0", "C"]
        for i, key in enumerate(keys):
            button = QtWidgets.QPushButton(key)
            button.setMinimumSize(64, 52)
            button.setFocusPolicy(QtCore.Qt.NoFocus)
            button.clicked.connect(lambda _c=False, k=key: self._key(k))
            pad.addWidget(button, i // 3, i % 3)
        lay.addLayout(pad)
        self.error = QtWidgets.QLabel("")
        self.error.setObjectName("lrtMuted")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)
        row = QtWidgets.QHBoxLayout()
        self.login_button = QtWidgets.QPushButton("Zaloguj")
        self.logout_button = QtWidgets.QPushButton("Wyloguj (Operator)")
        cancel = QtWidgets.QPushButton("Anuluj")
        for button in (self.login_button, self.logout_button, cancel):
            button.setMinimumHeight(44)
            row.addWidget(button)
        self.login_button.clicked.connect(self.attempt)
        self.logout_button.clicked.connect(self.logout)
        cancel.clicked.connect(self.reject)
        lay.addLayout(row)

    def _key(self, key):
        text = self.pin.text()
        self.pin.setText("" if key == "C" else text[:-1] if key == "⌫" else (text + key)[:12])

    def attempt(self):
        try:
            self.session.login(self.role.currentData(), self.pin.text())
        except AccessError as exc:
            self.pin.clear()
            self.error.setText(str(exc))
            return
        self.accept()

    def logout(self):
        self.session.logout()
        self.accept()


class RoleButton(QtWidgets.QPushButton):
    """Pigułka roli w górnym pasku; kliknięcie otwiera logowanie."""

    changed = QtCore.pyqtSignal(str)

    def __init__(self, session, reason="", parent=None):
        super().__init__(parent)
        self.session, self.reason = session, reason
        self.setMinimumHeight(44)
        self.clicked.connect(self.open)
        self.refresh()

    def refresh(self):
        if self.session is None:
            self.setText("Dostęp: —")
            self.setToolTip(self.reason or "Poziomy dostępu niedostępne.")
            self.setEnabled(False)
            return
        if not self.session.enforced:
            self.setText("Dostęp: bez PIN-ów")
            self.setToolTip("Kontrola dostępu wyłączona — nie ustawiono PIN-ów. Serwis włącza ją "
                            "poleceniem: python -m linumert.access set-pin --db "
                            f"{self.session.store.path} --role serwis")
            return
        self.setText(ROLE_LABEL[self.session.role])
        self.setToolTip("Zmień rolę: Operator / Technolog / Serwis (PIN)")

    def open(self):
        if self.session is None or not self.session.enforced:
            QtWidgets.QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), self.toolTip())
            return
        PinDialog(self.session, self).exec_()
        self.refresh()
        self.changed.emit(self.session.role)
