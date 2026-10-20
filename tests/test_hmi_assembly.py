# SPDX-License-Identifier: GPL-2.0-or-later
"""Składanie i układ całego HMI bez CNC; ruch sprawdza osobny test RIP. Model-Author: Codex."""
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


def test_full_hmi_fits_small_screen_without_navigation_commands(tmp_path):
    pytest.importorskip("PyQt5")
    result = subprocess.run([sys.executable, __file__, str(tmp_path / "shell.png")],
                            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "shell.png").stat().st_size > 20000


def smoke(snapshot):
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / "screens/linumert"), str(root / "core"), str(root / "simulation")]
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication([])
    info = SimpleNamespace(AVAILABLE_AXES=["X", "Y", "Z"], AVAILABLE_JOINTS=[0, 1, 2],
                           GET_NAME_FROM_JOINT={0: "X", 1: "Y", 2: "Z"}, JOINT_SEQUENCE=[1, 1, 0],
                           MAX_FEED_OVERRIDE=120, MAX_SPINDLE_OVERRIDE=120,
                           MIN_SPINDLE_OVERRIDE=50, MACHINE_IS_METRIC=True,
                           INIPATH=str(root / "config/sim/linumert_xyz/linumert_xyz.ini"))
    status, action = Mock(), Mock()
    status.stat.joint = [dict(homed=True, min_hard_limit=False, max_hard_limit=False,
                              fault=False, enabled=True, ferror_current=0)] * 3
    status.stat.joints = 3
    core = ModuleType("qtvcp.core")
    core.Action, core.Info, core.Status = lambda: action, lambda: info, lambda: status
    sys.modules["qtvcp"] = ModuleType("qtvcp")
    sys.modules["qtvcp.core"] = core
    lc = ModuleType("linuxcnc")
    for i, name in enumerate(("NML_ERROR", "OPERATOR_ERROR", "NML_TEXT", "OPERATOR_TEXT",
                               "NML_DISPLAY", "OPERATOR_DISPLAY")):
        setattr(lc, name, i)
    sys.modules["linuxcnc"] = lc
    import linumert_shell

    linumert_shell.LinumertShell._start_mushroom = lambda self: None
    linumert_shell.sim_page.gl = None
    linumert_shell.sim_page.SimPage.start = lambda *a: None
    window = QtWidgets.QMainWindow()
    window.setCentralWidget(QtWidgets.QLabel("classic"))
    shell = linumert_shell.LinumertShell(SimpleNamespace(w=window, add_status=Mock())).install()
    shell.s.estop, shell.s.machine_on, shell.s.homed = False, True, {"X", "Y", "Z"}
    shell.select_area("sim")
    shell.refresh()
    window.resize(1280, 768)
    window.show()
    app.processEvents()
    shell.show_alarm("warn", "długi komunikat " * 100)
    app.processEvents()
    assert window.width() == 1280
    shell.reset_alarms(False)
    assert window.height() == 768
    assert len(shell.operator_panels) == 2
    assert shell.alarm.isVisible() and all(row.isVisible() for row in shell.alarm.rows)
    status.stat.joint[0]["fault"] = True
    shell.show_alarm("err", "Awaria napędu")
    shell.reset_alarms(False)
    assert shell.alarm.entries  # przyczyna fizycznego alarmu nadal obecna
    status.stat.joint[0]["fault"] = False
    shell.reset_alarms(False)
    assert not shell.alarm.entries
    shell.acknowledge_estop = Mock()
    shell.reset_alarms(True)
    shell.acknowledge_estop.assert_not_called()  # zdrowy obwód nie jest przełączany Resetem
    shell.s.estop = True
    shell.reset_alarms(True)
    shell.acknowledge_estop.assert_called_once()
    shell.sim.client.send = Mock()
    shell.sim.resume_preview.click()
    shell.sim.client.send.assert_called_once_with(cmd="resume_preview")
    shell.sim.on_message({"ev": "resume_preview", "ok": True, "text": "Podgląd bez wykonania",
                          "overlap": 2, "feed": 200, "entry": (0, 0, -2),
                          "points": [(0, 0, 1, "rapid"), (1, 0, -2, "feed"),
                                     (2, 0, -2, "feed")]})
    app.processEvents()
    assert shell.sim._resume_dialog.isVisible()
    assert shell.sim._resume_dialog.grab().save(str(Path(snapshot).with_name("resume-preview.png")))
    shell.sim._resume_dialog.close()
    assert not action.mock_calls, action.mock_calls
    assert window.grab().save(snapshot)
    window.close()


if __name__ == "__main__":
    smoke(sys.argv[1])
