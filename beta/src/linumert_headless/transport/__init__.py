"""Transporty aplikacji headless: REST, WebSocket, CLI.

SPDX-License-Identifier: GPL-2.0-or-later

Wszystkie trzy używają tego samego kontraktu i tych samych modeli, więc GUI, skrypt i
człowiek w terminalu widzą identyczne operacje i identyczne błędy.
"""

from __future__ import annotations

from .rest import API, create_app, error_response
from .ws import ConnectionHub

__all__ = ["API", "ConnectionHub", "create_app", "error_response"]
