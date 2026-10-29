"""Usługa systemowa: informacje o aplikacji, zdrowie, kontrakt.

SPDX-License-Identifier: GPL-2.0-or-later

Te trzy zapytania wystarczą, żeby dowolne GUI mogło się podłączyć i sprawdzić, z czym
rozmawia: ``system.info`` (wersja, backend, brak GUI/OpenGL), ``system.health`` (czy backend
żyje, wersja stanu) i ``system.contract`` (pełna lista operacji ze schematami JSON).
"""

from __future__ import annotations

import platform
import sys
import time
from collections.abc import Callable

from .. import __version__
from ..schema import ContractOut, HealthOut, SystemInfo

APPLICATION = "linumeRT headless (beta)"
NO_GUI_NOTE = ("aplikacja bez GUI: brak Qt, OpenGL i panelu web; interfejs buduje klient "
               "na podstawie kontraktu (REST/WebSocket/SDK)")


class SystemService:
    """Operacje domeny ``system``."""

    domain = "system"

    def __init__(self, *, backend_name: str = "", state_version: Callable[[], int] | None = None,
                 backend_alive: Callable[[], bool] | None = None,
                 uptime: Callable[[], float] | None = None):
        self._backend_name = backend_name
        self._state_version = state_version or (lambda: 0)
        self._backend_alive = backend_alive or (lambda: True)
        self._uptime = uptime or (lambda: time.monotonic())
        self._started = time.monotonic()

    def info(self) -> SystemInfo:
        return SystemInfo(
            application=APPLICATION,
            version=__version__,
            backend=self._backend_name,
            python=sys.version.split()[0],
            platform=platform.platform(),
            gui=False,
            opengl=False,
            notes=NO_GUI_NOTE,
        )

    def health(self) -> HealthOut:
        return HealthOut(
            ok=self._backend_alive(),
            backend=self._backend_name,
            backend_alive=self._backend_alive(),
            uptime_s=round(time.monotonic() - self._started, 3),
            threads=_thread_count(),
            state_version=self._state_version(),
        )

    def contract(self, export: dict) -> ContractOut:
        """Kontrakt z rejestru (``contract.Contract.export``) jako model API."""
        return ContractOut.model_validate({
            "application": APPLICATION,
            "version": __version__,
            "operations": export.get("operations", []),
            "events": export.get("events", []),
        })


def _thread_count() -> int:
    import threading

    return threading.active_count()


__all__ = ["APPLICATION", "NO_GUI_NOTE", "SystemService"]
