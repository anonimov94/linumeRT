"""Warstwa dostepu do LinuxCNC (linuxcnc.command/stat) z atrapa do testow bez LinuxCNC."""

from .fake import FakeMachine
from .model import (
    AxisSnapshot,
    InterpState,
    MachineSnapshot,
    Mode,
    TaskState,
)

__all__ = [
    "AxisSnapshot",
    "FakeMachine",
    "InterpState",
    "MachineSnapshot",
    "Mode",
    "TaskState",
]
