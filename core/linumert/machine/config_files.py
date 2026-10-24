"""Backup and preview of generated configuration files (session 062).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import difflib
import shutil
import tempfile
from pathlib import Path, PurePosixPath


def _relative(name: str) -> Path:
    path = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or path.is_absolute():
        raise ValueError(f"Nieprawidłowa ścieżka konfiguracji: {name}")
    if not path.parts or any(part in (".", "..") for part in path.parts):
        raise ValueError(f"Nieprawidłowa ścieżka konfiguracji: {name}")
    return Path(*path.parts)


def _check_tree(directory: Path) -> None:
    # Backup and diff must never follow links into another configuration or device.
    if directory.is_symlink():
        raise ValueError("Katalog konfiguracji nie może być dowiązaniem.")
    if directory.exists() and not directory.is_dir():
        raise ValueError("Ścieżka konfiguracji musi wskazywać katalog.")
    for path in directory.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"Nieobsługiwany plik konfiguracji: {path}")


def configuration_diff(directory: Path, files: dict[str, str]) -> str:
    """Preview only generated files; unrelated operator files are left out."""
    directory = Path(directory)
    _check_tree(directory)
    changes = []
    for name, content in sorted(files.items()):
        path = directory / _relative(name)
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        changes.extend(difflib.unified_diff(
            old.splitlines(keepends=True), content.splitlines(keepends=True),
            fromfile=f"before/{name}", tofile=f"after/{name}",
        ))
    return "".join(changes)


def backup_configuration(directory: Path) -> Path | None:
    """Copy the entire existing configuration before a build; never overwrite a backup.

    New destinations return None. Existing empty directories also receive a backup.
    Errors propagate to the builder so it cannot proceed after an incomplete backup.
    This function does not modify the source configuration.
    """
    directory = Path(directory)
    _check_tree(directory)
    if not directory.exists():
        return None
    archive = Path(tempfile.mkdtemp(prefix=f"{directory.name}.backup-", dir=directory.parent))
    backup = archive / directory.name
    shutil.copytree(directory, backup)
    return backup
