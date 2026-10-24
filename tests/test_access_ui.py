# SPDX-License-Identifier: GPL-2.0-or-later
"""Sesja 036 na ekranie: przycisk roli, logowanie PIN-em z klawiatury, strażnik uprawnień.

Model-Author: Claude
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt5")
from PyQt5 import QtWidgets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "screens" / "linumert"))
import linumert_access_ui as ui  # noqa: E402
from linumert.access import AccessStore, Session  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def session(tmp_path):
    s = Session(AccessStore(tmp_path / "a.sqlite"))
    yield s
    s.store.close()


def test_db_path_next_to_ini_or_from_setting(tmp_path):
    ini = tmp_path / "m.ini"
    ini.write_text("[EMC]\nMACHINE = x\n")
    assert ui.access_db_path(ini) == tmp_path / ui.DB_NAME
    ini.write_text("[LINUMERT]\nACCESS_DB = dane/role.sqlite\n")
    assert ui.access_db_path(ini) == tmp_path / "dane/role.sqlite"
    assert ui.access_db_path("").name == ui.DB_NAME


def test_open_session_reports_unusable_database(tmp_path):
    blocker = tmp_path / "plik"
    blocker.write_text("x")
    ini = tmp_path / "m.ini"
    ini.write_text(f"[LINUMERT]\nACCESS_DB = {blocker}/a.sqlite\n")
    session, reason = ui.open_session(ini)
    assert session is None and "niedostępne" in reason


def test_role_button_states(app, session):
    button = ui.RoleButton(session)
    assert button.text() == "Dostęp: bez PIN-ów" and "set-pin" in button.toolTip()
    assert button.minimumHeight() >= 44
    session.store.set_pin("technolog", "1357")
    button.refresh()
    assert button.text() == "Operator"
    off = ui.RoleButton(None, "Poziomy dostępu niedostępne: brak zapisu")
    assert not off.isEnabled() and "brak zapisu" in off.toolTip()


def test_pin_dialog_keypad_login_and_logout(app, session):
    session.store.set_pin("technolog", "1357")
    dialog = ui.PinDialog(session)
    assert [dialog.role.itemData(i) for i in range(dialog.role.count())] == ["operator",
                                                                           "technolog"]
    dialog.role.setCurrentIndex(1)
    for key in "1350⌫7":
        dialog._key(key)
    assert dialog.pin.text() == "1357"
    dialog._key("C")
    dialog.pin.setText("9999")
    dialog.attempt()
    assert session.role == "operator" and "Błędny PIN" in dialog.error.text()
    assert dialog.pin.text() == ""
    dialog.pin.setText("1357")
    dialog.attempt()
    assert session.role == "technolog" and dialog.result() == QtWidgets.QDialog.Accepted
    ui.PinDialog(session).logout()
    assert session.role == "operator"


def test_require_warns_with_needed_role_and_audits(app, session):
    alarms = []
    shell = SimpleNamespace(access=session, show_alarm=lambda lvl, txt: alarms.append((lvl, txt)))
    assert ui.require(shell, "tools.edit", "T3")          # bez PIN-ów: jak dotąd
    session.store.set_pin("serwis", "2468")
    assert not ui.require(shell, "settings", "Konfiguracja")
    assert alarms[-1][0] == "warn" and "Serwis" in alarms[-1][1]
    assert session.store.history(1)[0][2:] == ("denied", "settings Konfiguracja")
    session.login("serwis", "2468")
    assert ui.require(shell, "settings")
    ui.audit(shell, "tools.edit", "T3 zapis")
    assert session.store.history(1)[0][1:] == ("serwis", "tools.edit", "T3 zapis")
    assert ui.require(SimpleNamespace(), "settings")        # ekran bez sesji (np. testy stron)
