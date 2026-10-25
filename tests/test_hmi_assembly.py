# SPDX-License-Identifier: GPL-2.0-or-later
"""Składanie i układ całego HMI bez CNC; ruch sprawdza osobny test RIP. Model-Author: Codex."""
import base64
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
    # Rzeczywiste kliknięcie → zrzut Qt → protokół → rzeczywisty zapis HTML.
    from linumert_sim.engine import Event, SimEngine
    from linumert_sim.live import Live
    from linumert_sim.report import SimLog
    from linumert_sim.zmap import StockMap

    live = Live.__new__(Live)
    live.engine, live.log = SimEngine(), SimLog()
    stock = StockMap("BOX", 0, 0, 10, 10, -5, 0, cell=1)
    live.engine.set_stock(stock)
    live.log.tick(100)
    live.log.tick(101, [Event("K-305", "collision", 42, 1, (1, 2, 3))])
    shell.sim.view.set_stock({"x0": 0, "y0": 0, "x1": 10, "y1": 10,
                              "z0": -5, "z1": 0}, stock.h)
    report = Path(snapshot).with_name("clicked-report.html")
    original_dialog = QtWidgets.QFileDialog.getSaveFileName
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(report), ""))
    shell.sim.client.send = Mock(side_effect=lambda **command: live.command(command))
    next(b for b in shell.sim.findChildren(QtWidgets.QPushButton) if b.text() == "Raport").click()
    QtWidgets.QFileDialog.getSaveFileName = original_dialog
    payload = shell.sim.client.send.call_args.kwargs["view_png"]
    assert base64.b64decode(payload).startswith(b"\x89PNG")
    html = report.read_text()
    assert payload in html and 'id="event-0" data-time="1.000000"' in html
    shell.sim.on_message({"ev": "event", "sim_time": 1, "code": "K-305", "kind": "collision",
                          "text": "kolizja", "line": 42, "pos": [1, 2, 3], "stop": False})
    assert shell.sim.events.item(0).text().startswith("1.00 s")
    assert not action.mock_calls, action.mock_calls
    # Real styled pages must fit the operator viewport after shrinking again.
    for width in (1280, 1920, 1280):
        window.resize(width, 768)
        for area in ("start", "tools"):
            shell.select_area(area)
            shell.refresh()
            for _ in range(8):
                app.processEvents()
            scroll = shell.stack.parentWidget().parentWidget()
            assert scroll.horizontalScrollBar().maximum() == 0, (area, width)
            assert window.width() == width
    from PyQt5 import QtCore, QtTest

    window.activateWindow()
    shell.tools.txt_desc.setFocus()
    app.processEvents()
    assert shell.tools.txt_desc.hasFocus()
    QtTest.QTest.keyClicks(shell.tools.txt_desc, "draft")
    assert shell.tools.txt_desc.text().endswith("draft")
    QtTest.QTest.keyClick(shell.tools.txt_desc, QtCore.Qt.Key_Tab)
    app.processEvents()
    assert shell.tools.txt_holder.hasFocus()
    assert window.grab().save(str(Path(snapshot).with_name("tools-responsive.png")))
    shell.select_area("start")
    for _ in range(8):
        app.processEvents()
    assert not action.mock_calls, action.mock_calls
    assert window.grab().save(snapshot)
    window.close()


if __name__ == "__main__":
    smoke(sys.argv[1])
