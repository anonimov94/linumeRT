#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the standalone Qt skin study. Model-Author: Codex."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "screens" / "linumert"))
from linumert_skin_preview import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
