# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded UTF-8 program editing and exclusive copy saving. Model-Author: Codex."""

import os
import tempfile
from pathlib import Path

EDIT_BYTES = 256 * 1024


def read_editable(path: Path) -> str:
    with path.open("rb") as source:
        data = source.read(EDIT_BYTES + 1)
    if len(data) > EDIT_BYTES:
        raise ValueError("Edytor obsługuje pliki do 256 KiB.")
    return data.decode("utf-8-sig")


def save_new_program(path: Path, text: str) -> None:
    """Publish a complete new file atomically; never replace an existing file or symlink."""
    data = text.encode("utf-8")
    if len(data) > EDIT_BYTES:
        raise ValueError("Edytor zapisuje pliki do 256 KiB.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".linumert-", delete=False) as f:
            temporary = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # Unlike replace/rename, link fails atomically if the destination already exists.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
