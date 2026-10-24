"""Sesja 036: role, PIN (scrypt) w SQLite, uprawnienia, blokada i audyt.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import sqlite3

import pytest
from linumert.access import (
    LOCKOUT_S,
    MAX_FAILURES,
    AccessError,
    AccessStore,
    Session,
    required_role,
)
from linumert.access.__main__ import main as cli


@pytest.fixture
def store(tmp_path):
    s = AccessStore(tmp_path / "access.sqlite")
    yield s
    s.close()


def test_without_pins_access_control_is_off(store):
    session = Session(store)
    assert not session.enforced and session.role == "operator"
    for permission in ("tools.edit", "offsets.edit", "settings", "classic", "jog"):
        assert session.allowed(permission)
    with pytest.raises(AccessError, match="nie ma ustawionego PIN"):
        session.login("serwis", "1234")


def test_pin_is_never_stored_in_plain_text(store, tmp_path):
    store.set_pin("serwis", "482913")
    store.set_pin("technolog", "1357")
    raw = (tmp_path / "access.sqlite").read_bytes()
    assert b"482913" not in raw and b"1357" not in raw
    rows = sqlite3.connect(tmp_path / "access.sqlite").execute(
        "SELECT role, length(salt), length(hash), n FROM pins ORDER BY role").fetchall()
    assert rows == [("serwis", 16, 32, 2 ** 14), ("technolog", 16, 32, 2 ** 14)]
    assert store.verify("serwis", "482913") and not store.verify("serwis", "482914")
    store.set_pin("serwis", "482913")                 # nowa sól przy każdym ustawieniu
    salts = sqlite3.connect(tmp_path / "access.sqlite").execute(
        "SELECT salt FROM pins WHERE role='serwis'").fetchall()
    assert len(salts) == 1
    for bad in ("12", "1234567890123", "12a4", ""):
        with pytest.raises(AccessError):
            store.set_pin("technolog", bad)
    with pytest.raises(AccessError):
        store.set_pin("operator", "1234")


def test_permissions_follow_role_rank(store):
    store.set_pin("technolog", "1111")
    store.set_pin("serwis", "2222")
    session = Session(store)
    assert session.enforced
    assert required_role("tools.edit") == "technolog" and required_role("settings") == "serwis"
    assert session.allowed("jog") and not session.allowed("tools.edit")
    assert not session.check("settings", "Konfiguracja")
    session.login("technolog", "1111")
    assert session.allowed("tools.edit") and session.allowed("offsets.edit")
    assert not session.allowed("settings") and not session.allowed("classic")
    session.login("serwis", "2222")
    assert all(session.allowed(p) for p in ("tools.edit", "settings", "classic"))
    session.logout()
    assert session.role == "operator" and not session.allowed("tools.edit")
    actions = [row[2] for row in store.history()]
    assert actions[:4] == ["logout", "login", "login", "denied"]


def test_failed_pins_lock_login_temporarily(store):
    store.set_pin("serwis", "2222")
    now = [100.0]
    session = Session(store, clock=lambda: now[0])
    for _ in range(MAX_FAILURES):
        with pytest.raises(AccessError, match="Błędny PIN"):
            session.login("serwis", "0000")
    with pytest.raises(AccessError, match="zablokowane"):
        session.login("serwis", "2222")             # poprawny PIN też czeka
    now[0] += LOCKOUT_S + 0.1
    assert session.login("serwis", "2222") == "serwis"
    actions = [row[2] for row in store.history(50)]
    assert actions.count("login.failed") == MAX_FAILURES and "login.locked" in actions


def test_panel_key_raises_role_and_is_audited(store):
    store.set_pin("serwis", "2222")
    session = Session(store)
    session.set_key("serwis")
    assert session.role == "serwis" and session.allowed("settings")
    session.set_key(None)
    assert session.role == "operator"
    assert [r[2] for r in store.history(2)] == ["key", "key"]
    with pytest.raises(AccessError):
        session.set_key("admin")


def test_audit_filter_and_limit(store):
    for i in range(5):
        store.audit("technolog", "tools.edit", f"T{i}")
    store.audit("serwis", "offsets.edit", "G54")
    assert len(store.history(3)) == 3
    assert [r[3] for r in store.history(action="tools")][:2] == ["T4", "T3"]


def test_cli_sets_and_clears_pins_without_echo(tmp_path, capsys):
    db = str(tmp_path / "a.sqlite")
    answers = iter(["9876", "9876"])
    assert cli(["set-pin", "--db", db, "--role", "serwis"], ask=lambda _p: next(answers)) == 0
    assert "9876" not in capsys.readouterr().out
    mismatch = iter(["1111", "2222"])
    assert cli(["set-pin", "--db", db, "--role", "technolog"],
               ask=lambda _p: next(mismatch)) == 1
    assert cli(["audit", "--db", db]) == 0
    assert "pin.set" in capsys.readouterr().out
    assert cli(["clear-pin", "--db", db, "--role", "serwis"]) == 0
    assert "wyłączona" in capsys.readouterr().out
