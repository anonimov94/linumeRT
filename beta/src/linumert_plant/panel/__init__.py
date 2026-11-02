"""Warstwa danych Plant: telemetria, parametry live, presety, pulpit, nagrywanie CSV.

SPDX-License-Identifier: GPL-2.0-or-later

W projekcie beta (aplikacja bez GUI) **nie ma panelu web**: `app.py`, katalog `static/`
i zależność od fastapi/uvicorn zostały usunięte. Zostają moduły danych, których używa serwer
LRT-NET (`telemetry`, `desk`, `presets`, `record`) — udostępnia je warstwa usług aplikacji
headless przez REST/WebSocket (`linumert_headless`), a nie osobna aplikacja web.
"""

from __future__ import annotations


class PanelUnavailable(RuntimeError):
    """Panel web nie istnieje w projekcie beta — dane Plant idą przez API headless."""


def load_app_module():
    """Zawsze ``PanelUnavailable``: w beta panel web został usunięty (brak GUI)."""
    raise PanelUnavailable(
        "projekt beta nie zawiera panelu web Plant; telemetria i parametry live są "
        "dostępne przez API aplikacji headless (linumert_headless)")
