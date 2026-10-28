"""Strona Maszyna w 1280×768: przyciski ruchu ręcznego (także Z) są widoczne bez przewijania.

Sesja 028 (M2): odbiór 1280×768 wykazał, że panel jogu leżał pod kartami Narzędzie i Posuw i jego
przyciski wychodziły poza ekran. W JOG/MDI panel jest teraz na górze prawej kolumny, w AUTO na dole.
Atrapa LinuxCNC jak w tests/test_hmi_assembly.py. Model-Author: Claude · 2026-10-25.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def test_jog_buttons_visible_without_scrolling_on_1280x768(tmp_path):  # D36, 028
    import pytest

    pytest.importorskip("PyQt5")
    result = subprocess.run([sys.executable, __file__],
                            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


def check():
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
    window.resize(1280, 768)
    window.show()
    shell.select_area("machine")

    def settle():
        shell.refresh()
        for _ in range(8):
            app.processEvents()

    def visible(key):
        btn = shell.buttons[key]
        view = shell.content.viewport()
        rect = btn.rect().translated(btn.mapTo(view, btn.rect().topLeft()))
        return btn.isVisible() and view.rect().contains(rect)

    shell.s.mode = "manual"
    settle()
    hidden = [k for k in ("jog_X-1", "jog_X1", "jog_Y-1", "jog_Y1", "jog_Z-1", "jog_Z1")
              if not visible(k)]
    assert not hidden, f"przyciski poza widocznym obszarem w JOG: {hidden}"
    if len(sys.argv) > 1:
        assert window.grab().save(sys.argv[1])
    # Dowód, że kontrola wykrywa również ucięcie poziome i ukryty przycisk.
    btn = shell.buttons["jog_Z1"]
    original = btn.pos()
    view = shell.content.viewport()
    offset = btn.mapTo(view, btn.rect().topLeft())
    btn.move(original.x() + view.width() - offset.x() - btn.width() + 1, original.y())
    assert not visible("jog_Z1"), "kontrola przepuszcza prawą krawędź poza viewportem"
    btn.move(original)
    btn.hide()
    assert not visible("jog_Z1"), "kontrola przepuszcza ukryty przycisk"
    btn.show()
    assert visible("jog_Z1")
    shell.s.mode = "mdi"
    settle()
    assert visible("jog_Z1"), "przycisk Z+ poza widocznym obszarem w MDI"
    assert shell._manual_on_top and shell._machine_right.indexOf(shell._manual_frame) == 0
    shell.s.mode = "auto"
    settle()
    assert not shell._manual_on_top, "w AUTO panel ma wrócić pod karty stanu"
    assert shell._machine_right.indexOf(shell._manual_frame) == shell._machine_right.count() - 1
    assert window.width() == 1280 and window.height() == 768


if __name__ == "__main__":
    check()
