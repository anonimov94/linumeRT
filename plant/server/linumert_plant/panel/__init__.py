"""Panel web Plant (sesja 022): telemetria, parametry live, presety, pulpit MPG, nagrywanie CSV.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 022.

Narzędzie testowe Plant, nie HMI operatora. Moduły `telemetry`, `desk`, `presets` i `record`
nie zależą od FastAPI — używa ich serwer LRT-NET. Aplikacja web (`app.py`) wymaga opcjonalnej
grupy zależności `panel` (`pip install -e ".[panel]"`); bez niej `create_app()` zgłasza
`PanelUnavailable` z czytelnym komunikatem, a import `linumert_plant` działa dalej.
"""

from __future__ import annotations


class PanelUnavailable(RuntimeError):
    """Brak zależności panelu (fastapi, uvicorn, websockets)."""


def load_app_module():
    """Moduł `app` panelu albo `PanelUnavailable` (brak fastapi/uvicorn)."""
    try:
        from . import app
    except ImportError as exc:
        raise PanelUnavailable(
            f"panel Plant wymaga pakietów fastapi, uvicorn i websockets ({exc.name} brak); "
            'zainstaluj: pip install -e ".[panel]"') from None
    return app
