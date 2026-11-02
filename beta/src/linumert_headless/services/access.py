"""Usługa poziomów dostępu: role, PIN (scrypt), uprawnienia i audyt.

SPDX-License-Identifier: GPL-2.0-or-later

Model z rdzenia (``linumert.access``): role operator < technolog < serwis. Dopóki nie ustawiono
żadnego PIN-u, kontrola jest **wyłączona** i każdy klient ma rolę operatora — brak domyślnych
PIN-ów. PIN jest trzymany wyłącznie jako skrót ``hashlib.scrypt`` z losową solą i porównywany
w stałym czasie; po serii błędnych prób logowanie jest blokowane.

To nie jest funkcja bezpieczeństwa maszyny: dotyczy prezentacji i edycji danych przez GUI.
E-STOP, STO, limity i interlocki pozostają w HAL/sprzęcie (CLAUDE.md §6).
"""

from __future__ import annotations

import secrets
from pathlib import Path

from linumert.access import AccessError, AccessStore, Session, required_role

from ..errors import Conflict, InvalidRequest, PermissionDenied
from ..schema import LoginOut, LoginRequest, Ok, PinSetRequest, SessionOut
from .paths import ProjectPaths

PERMISSIONS = (
    "machine.control", "machine.config", "program.edit", "tool.edit",
    "offset.edit", "cam.generate", "plant.control", "diag.read", "alarm.ack",
)


class AccessService:
    """Operacje domeny ``access``."""

    domain = "access"

    def __init__(self, paths: ProjectPaths, store_path: Path | None = None):
        self.paths = paths
        self.store_path = store_path or (paths.state / "access.db")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = AccessStore(self.store_path)
        self.sessions: dict[str, Session] = {}

    def close(self) -> None:
        self.store.close()

    # ---- sesje -------------------------------------------------------------
    def session(self, token: str = "") -> Session:
        """Sesja dla tokenu; bez tokenu (albo bez PIN-ów) sesja operatora."""
        if token and token in self.sessions:
            return self.sessions[token]
        return Session(self.store)

    def login(self, request: LoginRequest) -> LoginOut:
        session = Session(self.store)
        try:
            token = session.login(request.role, request.pin)
        except AccessError as exc:
            message = str(exc)
            if "zablokowan" in message.lower() or "lock" in message.lower():
                raise PermissionDenied(message) from exc
            raise InvalidRequest(message) from exc
        real_token = token or secrets.token_urlsafe(16)
        self.sessions[real_token] = session
        return LoginOut(ok=True, role=session.role, token=real_token,
                        enforced=session.enforced,
                        message=f"zalogowano jako {session.role}")

    def logout(self, token: str) -> Ok:
        session = self.sessions.pop(token, None)
        if session is not None:
            session.logout()
        return Ok(message="wylogowano")

    def current(self, token: str = "") -> SessionOut:
        session = self.session(token)
        return SessionOut(
            role=session.role,
            enforced=session.enforced,
            permissions=[p for p in PERMISSIONS if session.allowed(p)],
        )

    # ---- PIN-y -------------------------------------------------------------
    def set_pin(self, request: PinSetRequest, by: str = "serwis") -> Ok:
        try:
            self.store.set_pin(request.role, request.pin, by=by)
        except AccessError as exc:
            raise Conflict(f"nie udało się ustawić PIN-u: {exc}") from exc
        return Ok(message=f"PIN dla roli {request.role} ustawiony")

    def clear_pin(self, role: str, by: str = "serwis") -> Ok:
        try:
            self.store.clear_pin(role, by=by)
        except AccessError as exc:
            raise Conflict(f"nie udało się usunąć PIN-u: {exc}") from exc
        return Ok(message=f"PIN dla roli {role} usunięty")

    def roles(self) -> dict:
        return {"configured": sorted(self.store.configured_roles()),
                "required": {p: required_role(p) for p in PERMISSIONS}}

    def audit(self, limit: int = 200, action: str = "") -> dict:
        rows = self.store.history(limit=limit, action=action or None)
        return {"entries": [{"time": r[0], "role": r[1], "action": r[2],
                             "detail": r[3] if len(r) > 3 else ""} for r in rows]}


__all__ = ["PERMISSIONS", "AccessService"]
