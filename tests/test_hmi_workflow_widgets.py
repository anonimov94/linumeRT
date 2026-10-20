"""Widgety HMI bez połączenia z maszyną. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
                            home_all=Mock(), _allowed=Mock(return_value=True),
                            action=action, info=info)
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


def test_program_syntax_checks_full_text_and_navigates(page_env, tmp_path):
    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_program_page")
    page = module.ProgramPage(shell)
    path = tmp_path / "bad.ngc"
    path.write_text("; comment\n" * 2100 + "G0 X\nM2\n", encoding="utf-8")
    assert page.show_file(path)
    page.check_button.click()
    assert page.issues.count() == 1
    page.show_issue(page.issues.item(0))
    assert page.preview.textCursor().selectedText() == "G0 X"
    assert "2101" in page.filename.text()
    assert not action.mock_calls
    path.write_text("G1 X2\nM2\n", encoding="utf-8")
    page.check_button.click()
    assert page.issues.count() == 0  # missing feed is semantic, not a lexer error
    assert "semantyki" in page.message.text()
    page.close()


def test_program_syntax_limits_and_failed_reread(page_env, tmp_path):
    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_program_page")
    page = module.ProgramPage(shell)
    path = tmp_path / "large.ngc"
    path.write_text(";" + "a" * module.CHECK_BYTES, encoding="utf-8")
    assert page.show_file(path)
    page.check_button.click()
    assert "nie został sprawdzony" in page.message.text()
    path.unlink()
    page.check_button.click()
    assert "Nie można odczytać" in page.message.text()
    assert not action.mock_calls
    page.close()


def test_program_editor_saves_full_copy_without_cnc(page_env, tmp_path):
    _home, _shell, _status, action = page_env
    module = importlib.import_module("linumert_program_editor")
    source = tmp_path / "source.ngc"
    text = "; line\n" * 3000 + "M2\n"
    source.write_text(text, encoding="utf-8")
    editor = module.ProgramEditor(source, text)
    editor.editor.appendPlainText("; changed")
    assert not editor.save_to(source)
    assert source.read_text(encoding="utf-8") == text
    target = tmp_path / "copy.ngc"
    assert editor.save_to(target)
    assert target.read_text(encoding="utf-8").endswith("M2\n\n; changed")
    assert editor.saved_path == target and not action.mock_calls
    editor.close()


def test_program_editor_declines_bad_encoding_and_running(page_env, tmp_path):
    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_program_page")
    page = module.ProgramPage(shell)
    source = tmp_path / "broken.ngc"
    source.write_bytes(b"\xff\nM2\n")
    assert page.show_file(source)
    page.edit_button.click()
    assert "Nie można edytować" in page.message.text()
    shell.s.interp = "run"
    page.refresh()
    assert not page.edit_button.isEnabled()
    page.edit_program()
    assert not action.mock_calls
    page.close()


def test_program_editor_confirm_discard_and_copy_preview(page_env, tmp_path):
    from PyQt5 import QtWidgets

    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_program_page")
    source = tmp_path / "source.ngc"
    source.write_text("M2\n", encoding="utf-8")
    editor = module.ProgramEditor(source, "M2\n")
    editor.show()
    editor.editor.insertPlainText("; edit\n")
    with patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.No):
        editor.reject()
        assert editor.isVisible()
    with patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes):
        editor.reject()
        assert not editor.isVisible()
    target = tmp_path / "copy.ngc"

    def save_dialog(dialog):
        assert dialog.save_to(target)
        return QtWidgets.QDialog.Accepted

    page = module.ProgramPage(shell)
    assert page.show_file(source)
    with patch.object(module.ProgramEditor, "exec_", save_dialog):
        page.edit_button.click()
    assert page.path == target and "M2" in page.preview.toPlainText()
    assert not action.mock_calls
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


def test_zero_detalu_save_load_and_explicit_offset_command(page_env, tmp_path):
    _home, shell, _status, action = page_env
    shell.c = importlib.import_module("linumert_shell_model").load_tokens()["kolory"]
    module = importlib.import_module("linumert_offsets_page")
    page = module.OffsetsPage(shell)
    page.state_path = tmp_path / "przygotówka.json"
    page.shape.setCurrentIndex(3)
    page.offset.setCurrentText("G59")
    for spin, value in zip(page.position, (25.4, 50.8, -25.4), strict=True):
        spin.setValue(value)
    assert page.save() and page.state_path.exists()
    page.shape.setCurrentIndex(0)
    assert page.load(page.state_path) and page.spec.shape == "casting"
    assert not action.mock_calls
    assert not page.apply_zero(confirm=False)  # najpierw bazowanie
    shell.s.homed = set(shell.s.axes)
    shell.s.metric = False
    assert page.apply_zero(confirm=False)
    action.CALL_MDI.assert_called_once_with("G10 L2 P6 X1.000000 Y2.000000 Z-1.000000")
    action.reset_mock()
    shell.s.interp = "run"
    assert not page.apply_zero(confirm=False) and not action.mock_calls
    page.close()


def test_zero_detalu_invalid_load_preserves_model(page_env, tmp_path):
    _home, shell, _status, _action = page_env
    shell.c = importlib.import_module("linumert_shell_model").load_tokens()["kolory"]
    module = importlib.import_module("linumert_offsets_page")
    page = module.OffsetsPage(shell)
    path = tmp_path / "broken.json"
    path.write_text('{"shape": "casting", "profile": [[0, 10], [0, 20]]}')
    previous = page.spec
    assert not page.load(path) and page.spec == previous
    page.close()


def test_offline_preview_cannot_set_offsets_even_when_machine_ready(page_env):
    _home, shell, _status, action = page_env
    shell.c = importlib.import_module("linumert_shell_model").load_tokens()["kolory"]
    shell.preview = True
    shell.s.homed = set(shell.s.axes)
    page = importlib.import_module("linumert_offsets_page").OffsetsPage(shell)
    assert not page.zero_button.isEnabled()
    assert not page.apply_zero(confirm=False) and not action.mock_calls
    page.close()


def test_numeric_keyboard_entry_is_not_clamped_during_typing(page_env):
    _home, shell, _status, _action = page_env
    from PyQt5 import QtCore, QtTest
    shell.c = importlib.import_module("linumert_shell_model").load_tokens()["kolory"]
    page = importlib.import_module("linumert_offsets_page").OffsetsPage(shell)
    page.shape.setCurrentIndex(1)
    spin = page.fields["diameter"]
    spin.lineEdit().selectAll()
    QtTest.QTest.keyClicks(spin.lineEdit(), "12.0001")
    QtTest.QTest.keyClick(spin.lineEdit(), QtCore.Qt.Key_Return)
    assert spin.value() == 12.0001 and spin.decimals() == 4
    spin.setValue(12)
    spin.stepUp()
    assert spin.value() == 13.0
    assert "13.0000" in spin.text()
    page.close()


def test_zero_reads_live_and_saved_machine_offsets_without_commands(page_env, tmp_path):
    _home, shell, _status, action = page_env
    shell.c = importlib.import_module("linumert_shell_model").load_tokens()["kolory"]
    shell.status = SimpleNamespace(stat=SimpleNamespace(g5x_index=1, g5x_offset=[10, 20, -30]))
    ini = tmp_path / "machine.ini"
    ini.write_text("[RS274NGC]\nPARAMETER_FILE=machine.var\n")
    (tmp_path / "machine.var").write_text("5241 45\n5242 60\n5243 -90\n")
    shell.info.INIPATH = str(ini)
    page = importlib.import_module("linumert_offsets_page").OffsetsPage(shell)
    page.machine_zero.click()
    assert tuple(spin.value() for spin in page.position) == (10, 20, -30)
    page.offset.setCurrentText("G55")
    page.machine_zero.click()
    assert tuple(spin.value() for spin in page.position) == (45, 60, -90)
    assert not action.mock_calls
    page.close()


def test_program_check_and_edit(page_env, tmp_path):
    """One check action and copy editing preserve the original without CNC commands."""
    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_program_page")
    page = module.ProgramPage(shell)
    path = tmp_path / "p.ngc"
    path.write_text("G21 G90\nG0 X10\nM2\n")
    page.show_file(path)
    assert page.check_program() == []
    path.write_text("G21 G90\nG0 X10 X20 (\nM2")
    issues = page.check_program()
    assert issues and page.preview.textCursor().blockNumber() == issues[0].line - 1
    editor = module.ProgramEditor(path, page.text)
    editor.editor.setPlainText("G21 G90\nG1 X5 F100\nM2")
    copy = tmp_path / "copy.ngc"
    assert editor.save_to(copy)
    assert "G1 X5" in copy.read_text() and "X20 (" in path.read_text()
    assert page.preview.isReadOnly() and not action.mock_calls
    page.close()


def test_cycles_page_builds_program(page_env, tmp_path, monkeypatch):
    """Cykle: formularz z pól generatora, walidacja, kroki, zapis .ngc i wczytanie bez ruchu."""
    pytest.importorskip("yaml")
    _home, shell, _status, action = page_env
    shell.c = {"bg2": "#000000", "fg3": "#666666", "teal": "#2dd4bf"}
    monkeypatch.delitem(sys.modules, "linumert_cycles_page", raising=False)
    module = importlib.import_module("linumert_cycles_page")
    page = module.CyclesPage(shell)
    for cls, dimensions in ((module.pockets.PocketRect, {"width": "40", "height": "30"}),
                            (module.pockets.PocketCircle, {"diameter": "40"})):
        page.cmb.setCurrentIndex(page.cmb.findText(cls.title))
        for name, value in {"tool_d": "8", "depth": "2", **dimensions}.items():
            page.inputs[name].setText(value)
        assert page.preview() and page.view2d.lines
        assert "frez" in page.lbl_issue.text() and not action.mock_calls
    page.resize(1100, 750)
    page.show()
    module.QtWidgets.QApplication.processEvents()
    assert page.grab().save(str(tmp_path / "cycles-pocket.png"))
    page.cmb.setCurrentIndex(page.cmb.findText("Planowanie"))
    assert page.preview() is None and "brak wymaganego pola" in page.lbl_issue.text()
    for name, value in (("x1", "100"), ("y1", "50"), ("depth", "1"), ("tool_d", "50")):
        page.inputs[name].setText(value)
    page.add_step()
    page.cmb.setCurrentIndex(page.cmb.findText("Otwory: wiercenie i gwintowanie"))
    page.inputs["pattern"].setCurrentText("grid")
    page.inputs["count"].setText("2")
    page.inputs["rows"].setText("2")
    page.inputs["depth"].setText("5")
    page.add_step()
    text = page.text()
    assert "G1 X" in text and "G98 G81" in text and text.rstrip().endswith("M2")
    assert page.view2d.lines and page.lbl_prog.text() == "2 kroków"
    target = tmp_path / "cykle.ngc"
    monkeypatch.setattr(module.QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    shell.s.interp = "idle"
    page.load()
    assert target.read_text() == text
    module.ACTION.OPEN_PROGRAM.assert_called_with(str(target))
    page.close()
