"""linumeRT headless (beta) — aplikacja CNC bez GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Bliźniacza aplikacja projektu linumeRT z całkowicie usuniętym GUI: **bez Qt, bez OpenGL,
bez ekranu QtVCP i bez panelu web**. Zostaje rdzeń (programy, narzędzia, CAM, konfiguracja,
alarmy, diagnostyka), symulacja materiału i Plant — wirtualna obrabiarka.

Cała funkcjonalność jest wystawiona jako **kontrakt operacji** (``contract.py``) dostępny
przez REST, WebSocket, CLI i SDK Pythona. GUI powstaje na końcu projektu: czyta
``GET /api/v1/contract`` i buduje interfejs — backend nie wymaga zmian.

Szybki start::

    linumertd serve --backend fake --port 8080     # serwer API
    linumertctl system info                        # CLI
    python -m linumert_headless contract           # kontrakt JSON

NIEZWERYFIKOWANE NA SPRZĘCIE — backend ``fake`` i Plant nie są dowodem działania maszyny.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .app import Application, build_application
from .contract import Context, Contract, Operation
from .errors import ApiError
from .schema import SCHEMA_VERSION
from .state import StateHub

__all__ = [
    "SCHEMA_VERSION",
    "ApiError",
    "Application",
    "Context",
    "Contract",
    "Operation",
    "StateHub",
    "__version__",
    "build_application",
]
