"""Zrzut rzeczywistego widoku 3D pod Xvfb/Mesa. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.linuxcnc
def test_report_captures_current_3d_camera(tmp_path):
    result = subprocess.run([sys.executable, __file__, str(tmp_path / "report3d.png")],
                            env={**os.environ, "QT_QPA_PLATFORM": "xcb",
                                 "LIBGL_ALWAYS_SOFTWARE": "1"},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "report3d.png").stat().st_size > 5000


def capture(path):
    from types import ModuleType
    from unittest.mock import Mock

    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / "screens/linumert"), str(root / "core"), str(root / "simulation")]
    from PyQt5 import QtGui, QtWidgets

    core = ModuleType("qtvcp.core")
    core.Action, core.Info, core.Status = Mock, Mock, Mock
    sys.modules["qtvcp"] = ModuleType("qtvcp")
    sys.modules["qtvcp.core"] = core
    import linumert_shell_model
    import linumert_sim_page
    import numpy as np

    assert linumert_sim_page.gl is not None, "CI wymaga pyqtgraph/OpenGL dla rzeczywistego 3D"
    app = QtWidgets.QApplication([])
    view = linumert_sim_page.View3D(linumert_shell_model.load_tokens()["kolory"])
    view.resize(640, 480)
    view.show()
    app.processEvents()
    heights = np.zeros((20, 30))
    heights[5:15, 5:25] = -5
    view.set_stock({"x0": 0, "x1": 30, "y0": 0, "y1": 20, "cell": 1, "z1": 0}, heights)
    view.set_tool([(0, 0), (2, 0), (2, 20)])
    view.move_tool((10, 10, -4), "feed")
    app.processEvents()
    first = view.snapshot_png()
    assert not QtGui.QImage.fromData(first).isNull()
    view.view.setCameraPosition(azimuth=30, elevation=60)
    app.processEvents()
    second = view.snapshot_png()
    assert second != first, "zrzut musi przedstawiać bieżącą kamerę"
    Path(path).write_bytes(second)
    view.close()


if __name__ == "__main__":
    capture(sys.argv[1])
