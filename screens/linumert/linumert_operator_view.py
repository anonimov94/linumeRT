# SPDX-License-Identifier: GPL-2.0-or-later
"""Startup presentation selection; no Qt, commands or HAL. Model-Author: Codex."""

import json
import os
import tempfile
from pathlib import Path

from linumert_skin_contract import SKIN_IDS

FAMILIES = ("shell", *SKIN_IDS)


def settings_path():
    value = os.environ.get("LINUMERT_OPERATOR_PREFERENCES")
    return Path(value) if value else Path.home() / ".config/linumert/operator-view.json"


def load_family(path=None):
    """Missing or invalid preferences retain the existing shell."""
    try:
        with (Path(path) if path is not None else settings_path()).open(encoding="utf-8") as f:
            data = json.loads(f.read(4096))
        if (not isinstance(data, dict) or type(data.get("version")) is not int
                or data["version"] != 1 or data.get("skin") not in FAMILIES):
            return "shell"
        return data["skin"]
    except (OSError, ValueError, TypeError):
        return "shell"


def startup_family():
    # Explicit launch overrides remain useful for an isolated acceptance run.
    value = os.environ.get("LINUMERT_OPERATOR_SKIN") or load_family()
    if value not in FAMILIES:
        raise ValueError(f"Nieobsługiwany widok HMI: {value}")
    return value


def save_family(family, path=None):
    if family not in FAMILIES:
        raise ValueError("Nieobsługiwany widok HMI")
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "skin": family}, f)
            f.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return path
