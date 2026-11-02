"""Poziomy dostępu ekranu: role, PIN (scrypt) w SQLite, uprawnienia i audyt (sesja 036).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

Role rosnąco: operator < technolog < serwis. Operator nie loguje się (rola domyślna).
PIN technologa i serwisu jest przechowywany wyłącznie jako skrót `hashlib.scrypt` z losową solą
(nigdy jawnie) i porównywany w stałym czasie. Po `MAX_FAILURES` błędnych próbach logowanie jest
blokowane na `LOCKOUT_S`. Dopóki nie ustawiono żadnego PIN-u, kontrola jest **wyłączona**
(`Session.enforced` = False) i wszystko działa jak przed sesją 036 — nie ma domyślnych PIN-ów.
Opcjonalny klucz z pulpitu (pin HAL) podnosi rolę przez `Session.set_key()`.

Uprawnienia dotyczą prezentacji i edycji danych na ekranie. Nie są funkcją bezpieczeństwa:
E-STOP, STO, limity i interlocki pozostają w HAL/sprzęcie (CLAUDE.md §6).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

ROLES = ("operator", "technolog", "serwis")
ROLE_LABEL = {"operator": "Operator", "technolog": "Technolog", "serwis": "Serwis"}
PERMISSIONS = {
    "tools.edit": "technolog",        # baza narzędzi: dodawanie, zapis, usuwanie
    "offsets.edit": "technolog",      # zero detalu G54…, definicja przygotówki
    "settings": "serwis",             # konfiguracja ekranu i maszyny
    "classic": "serwis",              # pełny QtDragon (w tym jego ustawienia)
}
PIN_MIN, PIN_MAX = 4, 12
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}
MAX_FAILURES = 5
LOCKOUT_S = 30.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS pins (
    role TEXT PRIMARY KEY, salt BLOB NOT NULL, hash BLOB NOT NULL,
    n INTEGER NOT NULL, r INTEGER NOT NULL, p INTEGER NOT NULL, changed REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, role TEXT NOT NULL,
    action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
"""


class AccessError(ValueError):
    """Odmowa z powodem dla operatora (zły PIN, blokada, nieznana rola)."""


def rank(role: str) -> int:
    if role not in ROLES:
        raise AccessError(f"Nieznana rola: {role!r}")
    return ROLES.index(role)


def required_role(permission: str) -> str:
    return PERMISSIONS.get(permission, "operator")


def _digest(pin: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=64 * 1024 * 1024,
                          dklen=32)


def _check_pin_format(pin: str) -> None:
    if not (isinstance(pin, str) and pin.isdigit() and PIN_MIN <= len(pin) <= PIN_MAX):
        raise AccessError(f"PIN musi mieć {PIN_MIN}–{PIN_MAX} cyfr.")


class AccessStore:
    """SQLite: skróty PIN-ów i audyt. Jedno połączenie na proces ekranu."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Serwer headless jest wielowątkowy (uvicorn + pętla stanu), a sqlite3 w
        # CPython 3.11 ma threadsafety=3 (serialized) — połączenie jest współdzielone.
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.db.commit()
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def close(self) -> None:
        self.db.close()

    def configured_roles(self) -> set[str]:
        return {row[0] for row in self.db.execute("SELECT role FROM pins")}

    def set_pin(self, role: str, pin: str, by: str = "serwis") -> None:
        if rank(role) == 0:
            raise AccessError("Operator nie ma PIN-u.")
        _check_pin_format(pin)
        salt = os.urandom(16)
        digest = _digest(pin, salt, **SCRYPT)
        self.db.execute("INSERT OR REPLACE INTO pins VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (role, salt, digest, SCRYPT["n"], SCRYPT["r"], SCRYPT["p"], time.time()))
        self.db.commit()
        self.audit(by, "pin.set", role)

    def clear_pin(self, role: str, by: str = "serwis") -> None:
        self.db.execute("DELETE FROM pins WHERE role = ?", (role,))
        self.db.commit()
        self.audit(by, "pin.clear", role)

    def verify(self, role: str, pin: str) -> bool:
        row = self.db.execute("SELECT salt, hash, n, r, p FROM pins WHERE role = ?",
                              (role,)).fetchone()
        if row is None or not isinstance(pin, str):
            return False
        salt, stored, n, r, p = row
        return hmac.compare_digest(_digest(pin, salt, n, r, p), stored)

    def audit(self, role: str, action: str, detail: str = "") -> None:
        self.db.execute("INSERT INTO audit (ts, role, action, detail) VALUES (?, ?, ?, ?)",
                        (time.time(), role, action, str(detail)[:500]))
        self.db.commit()

    def history(self, limit: int = 200, action: str | None = None) -> list[tuple]:
        sql = "SELECT ts, role, action, detail FROM audit"
        args: tuple = ()
        if action:
            sql += " WHERE action LIKE ?"
            args = (action + "%",)
        return list(self.db.execute(sql + " ORDER BY id DESC LIMIT ?", args + (limit,)))


@dataclass
class Session:
    """Bieżąca rola ekranu; logowanie PIN-em, klucz z pulpitu, decyzje o uprawnieniach."""

    store: AccessStore
    login_role: str = "operator"
    key_role: str | None = None
    failures: int = 0
    locked_until: float = 0.0
    clock: object = time.monotonic

    @property
    def enforced(self) -> bool:
        return bool(self.store.configured_roles())

    @property
    def role(self) -> str:
        roles = [self.login_role] + ([self.key_role] if self.key_role else [])
        return max(roles, key=rank)

    def allowed(self, permission: str) -> bool:
        return not self.enforced or rank(self.role) >= rank(required_role(permission))

    def check(self, permission: str, detail: str = "") -> bool:
        """Jak `allowed`, a odmowę zapisuje w audycie."""
        if self.allowed(permission):
            return True
        self.store.audit(self.role, "denied", f"{permission} {detail}".strip())
        return False

    def login(self, role: str, pin: str) -> str:
        rank(role)
        now = self.clock()
        if now < self.locked_until:
            raise AccessError(f"Logowanie zablokowane na {self.locked_until - now:.0f} s "
                              "po błędnych PIN-ach.")
        if role == "operator":
            self.logout()
            return self.role
        if role not in self.store.configured_roles():
            raise AccessError(f"Rola {ROLE_LABEL[role]} nie ma ustawionego PIN-u.")
        if not self.store.verify(role, pin):
            self.failures += 1
            self.store.audit(self.role, "login.failed", role)
            if self.failures >= MAX_FAILURES:
                self.failures = 0
                self.locked_until = now + LOCKOUT_S
                self.store.audit(self.role, "login.locked", f"{LOCKOUT_S:.0f} s")
            raise AccessError("Błędny PIN.")
        self.failures = 0
        self.login_role = role
        self.store.audit(role, "login", role)
        return self.role

    def logout(self) -> None:
        if self.login_role != "operator":
            self.store.audit(self.login_role, "logout", "")
        self.login_role = "operator"

    def set_key(self, role: str | None) -> None:
        """Klucz z pulpitu (pin HAL): None = wyjęty. Zmiana trafia do audytu."""
        if role is not None:
            rank(role)
        if role != self.key_role:
            self.store.audit(role or self.login_role, "key", role or "wyjęty")
        self.key_role = role
