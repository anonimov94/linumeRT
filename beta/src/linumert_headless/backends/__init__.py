"""Backendy portu ``MachinePort``: atrapa (domyślnie) i LinuxCNC.

SPDX-License-Identifier: GPL-2.0-or-later

Backend wybiera konfiguracja (``--backend fake|linuxcnc``). Usługi, transporty i GUI widzą
ten sam interfejs, więc podmiana nie wymaga zmian poza korzeniem kompozycji (``app.py``).
"""

from __future__ import annotations

from .fake import FakeBackend

__all__ = ["FakeBackend"]
