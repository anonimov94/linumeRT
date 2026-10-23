"""Isolated GL process: ordinary offscreen Qt tests cannot replace the GL check.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get("SKIN01_GL") != "1", reason="requires explicit GL display")
def test_real_depth_culling_cameras_and_interaction(tmp_path):
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tools/dev/renderer-check.py"), "--output", str(tmp_path)],
        env={**os.environ, "QT_QPA_PLATFORM": "xcb", "PYQTGRAPH_QT_LIB": "PyQt5"},
        capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"passed": true' in result.stdout
