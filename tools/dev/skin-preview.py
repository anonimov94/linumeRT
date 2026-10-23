#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the standalone Qt skin study. Model-Author: Codex."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "screens/linumert"), str(ROOT / "core"), str(ROOT / "simulation")]
os.environ.setdefault("PYQTGRAPH_QT_LIB", "PyQt5")
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    if os.environ["QT_QPA_PLATFORM"] == "xcb":
        os.environ.setdefault("PYOPENGL_PLATFORM", "glx")
from linumert_skin_preview import main  # noqa: E402

if __name__ == "__main__":
    if "--layout-only" in sys.argv:
        raise SystemExit(main())
    from linumert_skin_viewports import create_viewport
    raise SystemExit(main(viewport_factory=create_viewport))
