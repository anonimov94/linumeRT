"""Locate optional standalone rs274 tests; never manages a live CNC process.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import os
from pathlib import Path

import pytest


def rip_root() -> Path:
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache/linuxcnc-2.9"))
    if not (root / "scripts/rip-environment").is_file() or not (root / "bin/rs274").is_file():
        pytest.skip(f"brak interpretera LinuxCNC RIP w {root}")
    return root
