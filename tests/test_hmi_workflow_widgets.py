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
    names = ("linumert_shell_pages", "linumert_homing_page", "linumert_program_page",
             "linumert_offsets_page")
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


def test_program_selection_previews_without_loading(page_env, tmp_path):
    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_program_page")
    page = module.ProgramPage(shell)
    path = tmp_path / "program ze spacją.ngc"
    path.write_text("G21 G90\nG0 X10\nM2\n")
    assert page.show_file(path)
    assert "G0 X10" in page.preview.toPlainText() and not action.mock_calls
    page.load.click()
    action.OPEN_PROGRAM.assert_called_once_with(str(path))
    action.reset_mock()
    shell.s.interp = "paused"
    page.refresh()
    page.load.click()
    assert not action.mock_calls
    page.close()


def test_program_bad_file_preserves_previous_preview(page_env, tmp_path):
    _home, shell, _status, _action = page_env
    module = importlib.import_module("linumert_program_page")
    page = module.ProgramPage(shell)
    path = tmp_path / "good.ngc"
    path.write_text("M2\n")
    assert page.show_file(path)
    assert not page.show_file(tmp_path / "missing.ngc")
    assert page.path == path and "M2" in page.preview.toPlainText()
    page.close()


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


def test_zero_detalu_edits_all_shapes_without_machine_commands(page_env):
    _home, shell, _status, action = page_env
    shell.c = importlib.import_module("linumert_shell_model").load_tokens()["kolory"]
    module = importlib.import_module("linumert_offsets_page")
    page = module.OffsetsPage(shell)
    for index, shape in enumerate(("box", "cylinder", "tube", "casting")):
        page.shape.setCurrentIndex(index)
        assert page.valid and page.view.spec.shape == shape
    page.profile.table.item(1, 1).setText("45")
    assert page.view.spec.profile[1] == (15, 45)
    page.position[0].setValue(123)
    assert page.view.spec.position[0] == 123
    page.scene_event({"ev": "machine", "name": "Test XYZ", "bodies": []})
    assert page.machine_name.text() == "Test XYZ"
    assert not action.mock_calls
    page.close()
