"""Konfiguracja aplikacji headless.

SPDX-License-Identifier: GPL-2.0-or-later

Wartości domyślne są bezpieczne dla pracy bez sprzętu: backend ``fake``, nasłuch na
``127.0.0.1``. Żeby wystawić API na sieć (np. GUI na innym komputerze), trzeba podać
``--listen 0.0.0.0`` **i** token — transport odmawia pracy bez tokenu poza localhost.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from .services.paths import ROOT, ProjectPaths

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
POLL_HZ = 50.0


@dataclass
class AppConfig:
    """Parametry uruchomienia aplikacji; czyta też zmienne środowiskowe ``LRT_*``."""

    root: Path = field(default_factory=lambda: ROOT)
    backend: str = "fake"                 # fake | linuxcnc
    axes: tuple[str, ...] = ("X", "Y", "Z")
    listen: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    token: str = ""
    poll_hz: float = POLL_HZ
    autostart: bool = True            # False = zegar atrapy sterowany ręcznie (testy)
    state_dir: Path | None = None
    log_level: str = "INFO"
    allow_origins: tuple[str, ...] = ()
    # Jawne opt-in: akceptuj dowolny nagłówek Host (podgląd/demo przez proxy).
    # Domyślnie wyłączone — kontrola Host blokuje DNS-rebinding.
    allow_any_host: bool = False

    def paths(self) -> ProjectPaths:
        return ProjectPaths(self.root)

    def resolved_token(self) -> str:
        """Token z konfiguracji albo ``LRT_TOKEN``; dla localhost może być pusty."""
        token = self.token or os.environ.get("LRT_TOKEN", "")
        if not token and not self.is_local:
            token = secrets.token_urlsafe(24)
        return token

    @property
    def is_local(self) -> bool:
        return self.listen in {"127.0.0.1", "localhost", "::1"}

    def require_token_for_network(self) -> None:
        """Poza localhost token jest obowiązkowy (brak domyślnego hasła)."""
        if self.is_local:
            return
        if not (self.token or os.environ.get("LRT_TOKEN")):
            raise ValueError(
                "nasłuch poza 127.0.0.1 wymaga tokenu: --token albo LRT_TOKEN "
                "(brak domyślnych poświadczeń)")


__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "POLL_HZ", "AppConfig"]
