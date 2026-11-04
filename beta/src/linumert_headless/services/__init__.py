"""Usługi domen aplikacji headless.

SPDX-License-Identifier: GPL-2.0-or-later

Każda usługa:
- mówi do **portu** (``ports.py``), nie do LinuxCNC/Plant/plików bezpośrednio,
- przyjmuje i zwraca **modele** z ``schema.py`` (te same co REST/WS/CLI/SDK),
- zgłasza błędy jako ``ApiError`` z kodem, nie wyjątki bibliotek.

Usługi nie wiedzą nic o transporcie ani o GUI. Rejestracja operacji kontraktu jest
w ``app.py``, więc dodanie funkcji = metoda usługi + wpis w rejestrze.
"""

from __future__ import annotations

from .access import AccessService
from .alarm import AlarmService
from .cam import CamService, load_generators
from .diag import DiagService
from .machine import MachineService
from .machineconfig import MachineConfigService
from .offset import OffsetService
from .paths import ProjectPaths
from .plant import PlantService
from .program import ProgramService
from .sim import SimService
from .system import SystemService
from .tool import ToolService

__all__ = [
    "AccessService",
    "AlarmService",
    "CamService",
    "DiagService",
    "MachineConfigService",
    "MachineService",
    "OffsetService",
    "PlantService",
    "ProgramService",
    "ProjectPaths",
    "SimService",
    "SystemService",
    "ToolService",
    "load_generators",
]
