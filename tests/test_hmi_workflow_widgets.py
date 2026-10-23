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
        for entry in ("ramp", "helix"):
            page.inputs["entry"].setCurrentText(entry)
            lines = page.preview()
            assert any(" Z-" in line and " X" in line for line in lines)
            assert "kąt" in page.lbl_issue.text() and not action.mock_calls
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


def _cycles(page_env, monkeypatch):
    pytest.importorskip("yaml")
    _home, shell, _status, action = page_env
    shell.c = {"bg2": "#000000", "fg3": "#666666", "teal": "#2dd4bf"}
    monkeypatch.delitem(sys.modules, "linumert_cycles_page", raising=False)
    module = importlib.import_module("linumert_cycles_page")
    return module, module.CyclesPage(shell), shell


def _face_step(page, tool_d="10"):
    page.cmb.setCurrentIndex(page.cmb.findText("Wymiana narzędzia"))
    page.inputs["tool"].setText("1")
    page.add_step()
    page.cmb.setCurrentIndex(page.cmb.findText("Planowanie"))
    for name, value in (("x1", "100"), ("y1", "50"), ("depth", "1"), ("tool_d", tool_d)):
        page.inputs[name].setText(value)
    page.add_step()


def test_cycles_steps_checked_with_tool_db(page_env, monkeypatch):
    """Cykle (Model-Author: Claude, sesja 040): kroki porównane z bazą narzędzi w GUI."""
    from linumert.tools.db import Tool

    module, page, shell = _cycles(page_env, monkeypatch)
    shell.tools = None
    _face_step(page)
    assert "niedostępna" in page.lbl_tools.text()
    tool = Tool(1, 1, "flat", params={"d": 10.0, "l": 40.0, "flute_length": 20.0})
    shell.tools = SimpleNamespace(_open=lambda: True, db=SimpleNamespace(get={1: tool}.get))
    page.pop_step()
    page.add_step()
    assert "zgodne z bazą" in page.lbl_tools.text()
    page.pop_step()
    page.inputs["tool_d"].setText("12")
    page.add_step()
    text = page.lbl_tools.text()
    assert "Średnica narzędzia = 12 nie zgadza" in text and "T1" in text
    assert len(page.check_tools()) == 1 and page.text().count("M2") == 1
    page.close()


def test_cycles_estimate_runs_off_gui_thread(page_env, monkeypatch, tmp_path):
    """Cykle (Model-Author: Claude, sesja 053): czas obróbki z wątku tła, GUI nie stoi."""
    import linumert.programs.estimate as estimate

    module, page, _shell = _cycles(page_env, monkeypatch)
    page.estimate()
    assert "Brak kroków" in page.lbl_time.text()
    _face_step(page)
    monkeypatch.setenv("INI_FILE_NAME", str(tmp_path / "m.ini"))
    seen = {}

    def fake(path, ini):
        seen["text"], seen["ini"] = Path(path).read_text(), ini
        return estimate.Estimate(total=125.4, rapid=5, feed=110.4, tool_change=10)

    monkeypatch.setattr(estimate, "estimate_ngc", fake)
    page.estimate()
    assert "Liczenie" in page.lbl_time.text()
    page._job[0].result(timeout=5)
    page._poll_estimate()
    assert "2:05" in page.lbl_time.text() and "wymiany 0:10" in page.lbl_time.text()
    assert seen["text"] == page.text() and seen["ini"].endswith("m.ini")
    monkeypatch.setattr(estimate, "estimate_ngc", lambda *a: (_ for _ in ()).throw(
        estimate.InterpreterUnavailable("brak rs274")))
    page.estimate()
    page._job[0].exception(timeout=5)
    page._poll_estimate()
    assert "niedostępny: brak rs274" in page.lbl_time.text()
    page.close()


def test_cycles_export_subroutines_to_ini_dir(page_env, monkeypatch, tmp_path):
    """Cykle (Model-Author: Claude, sesja 048): eksport o<lrt_...> do katalogu z INI."""
    module, page, _shell = _cycles(page_env, monkeypatch)
    ini = tmp_path / "cfg" / "m.ini"
    ini.parent.mkdir()
    ini.write_text("[RS274NGC]\nSUBROUTINE_PATH = ../macros:../nc_files/user_macros\n")
    monkeypatch.setenv("INI_FILE_NAME", str(ini))
    assert page.subroutine_dir() == str(tmp_path / "nc_files" / "user_macros")
    monkeypatch.setattr(module.QtWidgets.QFileDialog, "getExistingDirectory",
                        staticmethod(lambda *a, **k: a[2]))
    paths = page.export_subroutines()
    assert [Path(p).name for p in paths] == ["lrt_face_mill.ngc", "lrt_drill_grid.ngc",
                                             "lrt_drill_circle.ngc"]
    assert "Zapisano 3 podprogramy" in page.lbl_issue.text()
    page.close()


def test_cycles_estimate_does_not_publish_stale_program_time(page_env, monkeypatch, tmp_path):
    import threading

    import linumert.programs.estimate as estimate

    _module, page, _shell = _cycles(page_env, monkeypatch)
    _face_step(page)
    monkeypatch.setenv("INI_FILE_NAME", str(tmp_path / "m.ini"))
    release = threading.Event()

    def calculate(*_args):
        assert release.wait(5)
        return estimate.Estimate(total=125)

    monkeypatch.setattr(estimate, "estimate_ngc", calculate)
    page.estimate()
    future, path, _revision = page._job
    try:
        page.pop_step()
    finally:
        release.set()
    future.result(timeout=5)
    page._poll_estimate()
    assert "Program zmieniony" in page.lbl_time.text()
    assert not Path(path).exists()
    page._poll_estimate()  # zaległy tick timera po odebraniu wyniku
    page.close()


def test_cycles_close_cleans_pending_estimate_file(page_env, monkeypatch, tmp_path):
    import threading

    import linumert.programs.estimate as estimate

    _module, page, _shell = _cycles(page_env, monkeypatch)
    _face_step(page)
    monkeypatch.setenv("INI_FILE_NAME", str(tmp_path / "m.ini"))
    started, release, finished = (threading.Event() for _ in range(3))

    def calculate(path, _ini):
        started.set()
        assert release.wait(5)
        assert Path(path).is_file()
        return estimate.Estimate(total=1)

    monkeypatch.setattr(estimate, "estimate_ngc", calculate)
    page.estimate()
    future, path, _revision = page._job
    try:
        assert started.wait(5)
        page.close()
        assert Path(path).exists()
        future.add_done_callback(lambda _future: finished.set())
    finally:
        release.set()
    future.result(timeout=5)
    assert finished.wait(5) and not Path(path).exists()


@pytest.mark.parametrize("units", ["mm", "inch"])
def test_cycles_lnx_roundtrip_preserves_metadata_and_edits_selected_step(
        page_env, monkeypatch, tmp_path, units):
    from linumert.programs.lnx import LnxProgram, Step, load_lnx, save_lnx
    from linumert.programs.stock import Stock
    from linumert.tools.db import Tool

    module, page, shell = _cycles(page_env, monkeypatch)
    original = LnxProgram(name="Pokrywa", units=units, comment="Zachowaj opis",
                          stock=Stock(shape="BOX", x=40, y=30, z=10, material="aluminium"),
                          steps=[Step(generator="tool_change", version=1, params={"tool": 1}),
                                 Step(generator="pocket_rect", version=1,
                                      params={"width": 20, "height": 16, "tool_d": 8, "depth": 1},
                                      comment="Stary program"),
                                 Step(generator="face_mill", version=1, enabled=False,
                                      params={}, comment="Nie obrabiaj")])
    source, target = tmp_path / "source.lnx", tmp_path / "copy.lnx"
    save_lnx(original, source)
    monkeypatch.setattr(module.QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(source), "")))
    monkeypatch.setattr(module.QtWidgets.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))

    def click(label):
        button = next(b for b in page.findChildren(module.QtWidgets.QPushButton)
                      if b.text() == label)
        button.click()

    click("Otwórz .lnx…")
    assert page.program == original and page.step_list.count() == 3
    page.step_list.setCurrentRow(1)
    assert page._gen().version == 1 and "G1 Z-1" in page.text()
    assert "pominiety" in page.text() and ";@STOCK" in page.text()
    click("Zapisz .lnx…")
    assert load_lnx(target) == original
    assert ("G21" if units == "mm" else "G20") in page.text()
    tool = Tool(1, 1, "flat", params={"d": 8 if units == "mm" else 8 * 25.4,
                                    "l": 40, "flute_length": 20})
    shell.tools = SimpleNamespace(_open=lambda: True, db=SimpleNamespace(get={1: tool}.get))
    page.inputs["tool_d"].setText("10")
    click("Zmień wybrany")
    assert page.program.steps[1].params["tool_d"] == 10
    assert page.program.steps[1].comment == "Stary program"
    assert page.program.steps[1].version == 1 and not page.program.steps[2].enabled
    assert "nie zgadza" in page.lbl_tools.text() and page._dirty
    click("Zapisz .lnx…")
    saved = load_lnx(target)
    assert saved.stock == original.stock and saved.comment == original.comment
    assert saved.steps[2] == original.steps[2]
    assert saved.steps[1].params["tool_d"] == 10
    page.close()


@pytest.mark.parametrize("content", ['{"schema_version":99}',
    '{"name":"bad","steps":[{"generator":"pocket_rect","version":99}]}',
    '{"name":"bad","steps":[{"generator":"pocket_rect","version":2,"params":{}}]}'])
def test_cycles_lnx_invalid_open_preserves_current_program(
        page_env, monkeypatch, tmp_path, content):
    module, page, _shell = _cycles(page_env, monkeypatch)
    _face_step(page)
    previous = page.text()
    source = tmp_path / "invalid.lnx"
    source.write_text(content)
    monkeypatch.setattr(module.QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(source), "")))
    assert not page.open_lnx()
    assert page.text() == previous and "Nie otwarto" in page.lbl_issue.text()
    page.close()


def test_cycles_lnx_open_cancel_keeps_unsaved_changes(page_env, monkeypatch, tmp_path):
    from linumert.programs.lnx import LnxProgram, save_lnx

    module, page, _shell = _cycles(page_env, monkeypatch)
    _face_step(page)
    previous = page.text()
    source = tmp_path / "empty.lnx"
    save_lnx(LnxProgram(name="inny"), source)
    monkeypatch.setattr(module.QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(source), "")))
    monkeypatch.setattr(module.QtWidgets.QMessageBox, "question",
                        staticmethod(lambda *a, **k: module.QtWidgets.QMessageBox.No))
    assert not page.open_lnx() and page.text() == previous
    page.close()


def test_loop_estimate_failure_keeps_screen_and_syntax_check_available(
        page_env, monkeypatch, tmp_path):
    """Click the real estimate action; emulate the legacy rs274 mmap side effect."""
    from PyQt5.QtWidgets import QApplication

    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_shell_pages")
    monkeypatch.setattr(module, "INFO", SimpleNamespace(MAX_FEED_OVERRIDE=120,
                        MIN_SPINDLE_OVERRIDE=50, MAX_SPINDLE_OVERRIDE=120))
    monkeypatch.setattr(module.STATUS, "connect", Mock(), raising=False)
    program, ini = tmp_path / "loop.ngc", tmp_path / "m.ini"
    program.write_text("o100 while [1]\nG4 P0.1\no100 endwhile\nM2\n")
    ini.write_text("[TRAJ]\n")
    binary = tmp_path / "rs274"
    binary.write_text(f"#!{sys.executable}\nimport os\nfrom pathlib import Path\n"
                      "(Path.home()/'.tool.mmap').write_bytes(b'')\n"
                      "while True: os.write(1,b'x'*65536)\n")
    binary.chmod(0o755)
    live = tmp_path / "live"
    live.mkdir()
    (live / ".tool.mmap").write_bytes(b"live tools")
    monkeypatch.setenv("HOME", str(live))
    monkeypatch.setenv("PATH", str(tmp_path) + ":/usr/bin:/bin")
    monkeypatch.setenv("INI_FILE_NAME", str(ini))
    monkeypatch.setattr("linumert.programs.linuxcnc_check.find_linuxcnc",
                        lambda *_: ([], None))
    shell.s.file = str(program)
    shell.program_lines = program.read_text().splitlines()
    page = module.ProductionPage(shell)
    page.btn_estimate.click()
    assert page._estimate_job is not None
    assert isinstance(page._estimate_job[0].exception(timeout=5), ValueError)
    page.refresh()
    QApplication.processEvents()
    assert "limit danych" in page.lbl_remaining.text()
    assert page.btn_estimate.isEnabled() and page._estimate_value is None
    assert (live / ".tool.mmap").read_bytes() == b"live tools"
    editor = importlib.import_module("linumert_program_page").ProgramPage(shell)
    assert editor.show_file(program)
    editor.check_button.click()
    assert "Nie wykryto błędów składni" in editor.message.text()
    assert not action.mock_calls
    editor.close()
    page.close()


def test_production_overrides_accept_typed_values_without_refresh_erasing_draft(
        page_env, monkeypatch):
    from PyQt5 import QtCore, QtTest, QtWidgets

    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_shell_pages")
    monkeypatch.setattr(module, "INFO", SimpleNamespace(MAX_FEED_OVERRIDE=120,
                        MIN_SPINDLE_OVERRIDE=50, MAX_SPINDLE_OVERRIDE=120))
    monkeypatch.setattr(module.STATUS, "connect", Mock(), raising=False)
    page = module.ProductionPage(shell)
    page.show()
    for key, text, call in (("feed", "85", action.SET_FEED_RATE),
                            ("rapid", "25", action.SET_RAPID_RATE),
                            ("spindle", "115", action.SET_SPINDLE_RATE)):
        action.reset_mock()
        field = page.sliders[key][1]
        field.setFocus()
        QtWidgets.QApplication.processEvents()
        field.selectAll()
        QtTest.QTest.keyClicks(field, text)
        page.on_state()  # Periodic LinuxCNC status must not overwrite unfinished input.
        assert field.cleanText() == text and not action.mock_calls
        QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)
        call.assert_called_once_with(int(text))
        assert page.sliders[key][0].value() == int(text)
    page.close()


def test_production_remaining_time_pauses_and_invalidates_changed_program(
        page_env, monkeypatch, tmp_path):
    from linumert.programs.estimate import Estimate

    _home, shell, _status, action = page_env
    module = importlib.import_module("linumert_shell_pages")
    monkeypatch.setattr(module, "INFO", SimpleNamespace(MAX_FEED_OVERRIDE=120,
                        MIN_SPINDLE_OVERRIDE=50, MAX_SPINDLE_OVERRIDE=120))
    monkeypatch.setattr(module.STATUS, "connect", Mock(), raising=False)
    ini, program = tmp_path / "m.ini", tmp_path / "p.ngc"
    ini.write_text("[TRAJ]\n")
    program.write_text("G21\nM2\n")
    shell.s.file, shell.s.total_lines = str(program), 2
    shell.program_lines = program.read_text().splitlines()
    monkeypatch.setenv("INI_FILE_NAME", str(ini))
    monkeypatch.setattr("linumert.programs.estimate.estimate_ngc", lambda *_: Estimate(total=120))
    now = [100]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    page = module.ProductionPage(shell)
    page.btn_estimate.click()
    page._estimate_job[0].result(timeout=5)
    page.refresh()
    assert "02:00" in page.lbl_remaining.text()
    shell.s.interp = "run"
    page.on_state()
    now[0] = 120
    page.refresh()
    assert "01:40" in page.lbl_remaining.text()
    shell.s.interp = "paused"
    page.on_state()
    now[0] = 180
    page.refresh()
    assert "01:40" in page.lbl_remaining.text()
    shell.s.feed_override = 0.5
    page.refresh()
    assert "100%" in page.lbl_remaining.text()
    shell.s.feed_override = 1
    page.refresh()
    assert "100%" in page.lbl_remaining.text()
    page._partial_run = True
    page.refresh()
    assert "od linii" in page.lbl_remaining.text()
    program.write_text("G21\nG0 X0\nM2\n")
    page.refresh()
    assert page._estimate_value is None and "zmienione" in page.lbl_remaining.text()
    assert not action.mock_calls
    page.close()


@pytest.mark.parametrize("override", ["feed_override", "rapid_override"])
@pytest.mark.parametrize("first_state", ["run", "paused"])
def test_eta_override_history_survives_estimation_and_resets_for_next_run(
        page_env, monkeypatch, tmp_path, override, first_state):
    from linumert.programs.estimate import Estimate

    _home, shell, _status, _action = page_env
    module = importlib.import_module("linumert_shell_pages")
    monkeypatch.setattr(module, "INFO", SimpleNamespace(MAX_FEED_OVERRIDE=120,
                        MIN_SPINDLE_OVERRIDE=50, MAX_SPINDLE_OVERRIDE=120))
    monkeypatch.setattr(module.STATUS, "connect", Mock(), raising=False)
    ini, program = tmp_path / "m.ini", tmp_path / "p.ngc"
    ini.write_text("[TRAJ]\n")
    program.write_text("G21\nM2\n")
    shell.s.file = str(program)
    shell.program_lines = program.read_text().splitlines()
    monkeypatch.setenv("INI_FILE_NAME", str(ini))
    monkeypatch.setattr("linumert.programs.estimate.estimate_ngc", lambda *_: Estimate(total=120))
    page = module.ProductionPage(shell)
    shell.s.interp = "run"
    page.on_state()
    setattr(shell.s, override, 0.5)
    page.on_state()  # Status events must latch this even before estimating or refreshing.
    setattr(shell.s, override, 1)
    page.on_state()
    page.btn_estimate.click()
    page._estimate_job[0].result(timeout=5)
    page.refresh()
    assert "100%" in page.lbl_remaining.text()
    shell.s.interp = "idle"
    page.on_state()
    page.refresh()
    assert "Szacowany czas programu" in page.lbl_remaining.text()
    shell.s.interp = first_state
    page.on_state()
    page.refresh()
    assert "Pozostało około" in page.lbl_remaining.text()
    page.close()
