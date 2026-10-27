"""Brama web-hmi: LinuxCNC <-> przeglądarka (REST + WebSocket), poza RT.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from .app import create_app
from .backend import CommandError, FakeBackend, LinuxCNCBackend, MachineBackend
from .gateway import Gateway
from .schema import SCHEMA_VERSION, Command, snapshot_to_dict

__all__ = [
    "SCHEMA_VERSION",
    "Command",
    "CommandError",
    "FakeBackend",
    "Gateway",
    "LinuxCNCBackend",
    "MachineBackend",
    "create_app",
    "snapshot_to_dict",
]
