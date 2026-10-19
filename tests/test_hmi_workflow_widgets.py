"""Widgety HMI bez połączenia z maszyną. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def page_env(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PyQt5.QtWidgets")
    app = qt.QApplication.instance() or qt.QApplication([])
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "screens/linumert"))
    info = SimpleNamespace(AVAILABLE_JOINTS=[0, 1, 2, 3],
                           GET_NAME_FROM_JOINT={0: "X", 1: "Y", 2: "Y2", 3: "Z"})
    status = SimpleNamespace(stat=SimpleNamespace(joint=[{"homed": False}] * 4))
    action = Mock()
    core = types.ModuleType("qtvcp.core")
    core.Info, core.Status, core.Action = lambda: info, lambda: status, lambda: action
    monkeypatch.setitem(sys.modules, "qtvcp", types.ModuleType("qtvcp"))
    monkeypatch.setitem(sys.modules, "qtvcp.core", core)
    names = ("linumert_shell_pages", "linumert_homing_page")
    for name in names:
        monkeypatch.delitem(sys.modules, name, raising=False)
    module = importlib.import_module("linumert_homing_page")
    shell = SimpleNamespace(s=module.model.ShellState(estop=False, machine_on=True),
                            home_all=Mock(), _allowed=Mock(return_value=True))
    page = module.HomingPage(shell)
    yield page, shell, status, action
    page.close()
    page.deleteLater()
    app.processEvents()
    for name in names:
        sys.modules.pop(name, None)


def test_homing_navigation_does_not_command_motion(page_env):
    page, _shell, _status, action = page_env
    page.refresh()
    assert not action.mock_calls
    assert set(page.joint_buttons) == {0, 3}  # oba Y tylko w sekwencji portalu
    assert page.table.rowCount() == 4
    page.joint_buttons[3].click()
    action.SET_MACHINE_HOMING.assert_called_once_with(3)


def test_homing_blocks_commands_during_program_and_homing(page_env):
    page, shell, status, action = page_env
    for state in ("run", "paused"):
        shell.s.interp = state
        page.refresh()
        assert not page.home.isEnabled()
        page.joint_buttons[0].click()
    shell.s.interp = "idle"
    status.stat.joint = [{"homing": True}] + [{"homed": True}] * 3
    page.refresh()
    assert "3 / 4" in page.summary.text() and not page.home.isEnabled()
    assert not action.mock_calls
