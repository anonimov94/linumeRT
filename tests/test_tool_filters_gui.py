# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only tool searches through real Qt widgets/SQLite. Model-Author: Codex."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUI_SETUP = r'''
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock
from PyQt5 import QtCore, QtWidgets

root, work = Path(sys.argv[1]), Path(sys.argv[2])
core = ModuleType("qtvcp.core")
core.Action = core.Info = core.Status = lambda: SimpleNamespace()
sys.modules["qtvcp"] = ModuleType("qtvcp")
sys.modules["qtvcp.core"] = core
cnc = ModuleType("linuxcnc")
cnc.stat = cnc.command = Mock(side_effect=AssertionError("unexpected CNC command"))
sys.modules["linuxcnc"] = cnc
sim_page = ModuleType("linumert_sim_page")
sim_page.ROOT = str(root)
sys.modules["linumert_sim_page"] = sim_page
tooldata = ModuleType("linumert_sim.tooldata")
tooldata.open_db = tooldata.save_tool = Mock(side_effect=AssertionError("unexpected write"))
sys.modules["linumert_sim"] = ModuleType("linumert_sim")
sys.modules["linumert_sim.tooldata"] = tooldata
from linumert_tools_page import ToolsPage
from linumert.tools.db import Tool, ToolDB
import linumert_shell_model as model

app = QtWidgets.QApplication([])
db = ToolDB(work / "tools.db")
db.add(Tool(12, 3, type="flat", params={"d":6, "l":30, "flute_length":15},
            description="Frez ŻÓŁĆ"))
db.add(Tool(27, 9, type="ball", params={"d":8, "l":40}, description="Kulowy"))
db.add(Tool(50, 20, description="Bez geometrii", diameter=5))
'''


@unittest.skipUnless(importlib.util.find_spec("PyQt5"), "PyQt5 unavailable")
class ToolFilterGuiTests(unittest.TestCase):
    def test_history_button_shows_changes_without_writes_or_cnc(self):
        script = GUI_SETUP + r'''
from dataclasses import replace
from unittest.mock import patch
from linumert_tool_history import ToolHistoryDialog

original = db.get(12)
db.update(replace(original, description="Nowy opis", offsets={"Z":42.1234}))
db.remove(12)
page = ToolsPage(SimpleNamespace(c=model.load_tokens()["kolory"]), str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.setStyleSheet(model.shell_qss(model.load_tokens()))
page.spin_t.setValue(12)  # History must also be available for a removed T.
before, history = db.tools(), db.history()
def inspect(dialog):
    assert dialog.events.count() == 3 and dialog.records[0]["action"] == "remove"
    rows = lambda: {dialog.details.item(row, 0).text():
                    (dialog.details.item(row, 1).text(), dialog.details.item(row, 2).text())
                    for row in range(dialog.details.rowCount())}
    assert rows()["Opis"] == ("Nowy opis", "—")
    dialog.events.setCurrentRow(1)
    assert rows()["Opis"] == ("Frez ŻÓŁĆ", "Nowy opis")
    assert rows()["Korekcja Z [mm]"] == ("—", "42.1234")
    assert "Numer T" not in rows()  # Show differences rather than unchanged fields.
    dialog.events.setCurrentRow(2)
    assert dialog.records[2]["action"] == "add" and rows()["Numer T"] == ("—", "12")
    dialog.show()
    app.processEvents()
    assert dialog.grab().save(str(work / "tool-history.png"))
    close = dialog.findChild(QtWidgets.QDialogButtonBox)
    close.button(QtWidgets.QDialogButtonBox.Close).click()
with patch.object(ToolHistoryDialog, "exec_", inspect), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.history_button.click()
    warning.assert_not_called()
page.spin_t.setValue(99)
def inspect_empty(dialog):
    assert not dialog.records and dialog.details.rowCount() == 0
    assert "Brak wpisów" in dialog.events.item(0).text()
with patch.object(ToolHistoryDialog, "exec_", inspect_empty), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.history_button.click()
    warning.assert_not_called()
with patch.object(db, "history", side_effect=RuntimeError("Baza niedostępna")), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.history_button.click()
    warning.assert_called_once()
damaged = db.history(12)
damaged[-1]["before"]["params"] = "invalid json"
with patch.object(db, "history", return_value=damaged), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.history_button.click()
    warning.assert_called_once()
assert db.tools() == before and db.history() == history
assert not page.tbl.exists() and not cnc.command.called and not tooldata.save_tool.called
db.close()
'''
        self.run_gui(script)

    def test_write_errors_and_unavailable_cnc_status_are_reported(self):
        script = GUI_SETUP + r'''
import sqlite3
from unittest.mock import patch

cnc.error, cnc.INTERP_IDLE = RuntimeError, 1
page = ToolsPage(SimpleNamespace(c=model.load_tokens()["kolory"], show_alarm=Mock()),
                 str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.load(db.get(12))
before, history = db.tools(), db.history()
save = next(button for button in page.findChildren(QtWidgets.QPushButton)
            if button.text() == "Zapisz")
remove = next(button for button in page.findChildren(QtWidgets.QPushButton)
              if button.text() == "Usuń")
uncaught = []
previous_hook = sys.excepthook
def collect(*exc):
    uncaught.append(exc)
    previous_hook(*exc)
sys.excepthook = collect
status = SimpleNamespace(poll=Mock(), interp_state=cnc.INTERP_IDLE)
for failed in (Mock(side_effect=cnc.error("Brak połączenia")),
               Mock(return_value=SimpleNamespace(poll=Mock(side_effect=cnc.error("Brak danych"))))):
    cnc.stat = failed
    for button in (save, remove):
        page.lbl_issue.clear()
        button.click()
        assert page.lbl_issue.text() and not uncaught
assert db.tools() == before and db.history() == history
assert not tooldata.save_tool.called and not page.tbl.exists()
cnc.stat = Mock(return_value=status)
status.interp_state = 2  # A running/paused program still blocks edits.
save.click()
remove.click()
assert db.tools() == before and not tooldata.save_tool.called
status.interp_state = cnc.INTERP_IDLE
def failed_save(db, tool, tbl):
    db.update(tool)  # Reproduce the existing backend's partial write before file failure.
    raise OSError("Brak miejsca na tool.tbl")
page.txt_desc.setText("Zmiana w bazie przed błędem pliku")
with patch("linumert_tools_page.save_tool", side_effect=failed_save):
    save.click()
assert not uncaught and "baza" in page.lbl_issue.text().casefold()
assert db.get(12).description == "Zmiana w bazie przed błędem pliku"
assert not cnc.command.called and not page.tbl.exists()
with patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.Yes), \
        patch.object(db, "export_tbl", side_effect=OSError("Tylko do odczytu")):
    remove.click()
assert db.get(12) is None and not uncaught
assert "baza" in page.lbl_issue.text().casefold() and not cnc.command.called
with patch.object(db, "get", side_effect=sqlite3.OperationalError("database is locked")):
    save.click()
    remove.click()
assert not uncaught and "database is locked" in page.lbl_issue.text()
assert not cnc.command.called
assert page.shell.show_alarm.called
db.close()
'''
        self.run_gui(script)

    def test_stl_picker_required_path_cancel_and_reload(self):
        script = GUI_SETUP + r'''
from unittest.mock import patch

page = ToolsPage(SimpleNamespace(c=model.load_tokens()["kolory"]), str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.load(Tool(70, 70, type="special_stl", params={"d":8, "l":40}))
assert not page.stl_row.isHidden() and not page.lbl_stl.isHidden()
assert any(issue.field == "stl" for issue in page.current().validate())
model_path = work / "żółć.stl"
model_bytes = b"solid test\nendsolid test\n"
model_path.write_bytes(model_bytes)
with patch.object(QtWidgets.QFileDialog, "getOpenFileName",
                  return_value=(str(model_path), "")) as dialog:
    page.btn_stl.click()
    dialog.assert_called_once()
tool = page.current()
assert tool.stl == str(model_path) and not tool.validate()
with patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "")):
    page.btn_stl.click()
assert page.txt_stl.text() == str(model_path)
db.add(tool)
page.load(db.get(12))
assert page.stl_row.isHidden() and page.lbl_stl.isHidden()
page.load(db.get(70))
assert page.current().stl == str(model_path)
window = QtWidgets.QWidget()
window.setObjectName("lrtRoot")
window.setStyleSheet(model.shell_qss(model.load_tokens()))
QtWidgets.QVBoxLayout(window).addWidget(page)
window.resize(1200, 600)
window.show()
app.processEvents()
assert window.height() == 600  # The editor must scroll instead of forcing a taller screen.
assert page.editor_scroll.horizontalScrollBar().maximum() == 0
page.editor_scroll.ensureWidgetVisible(page.stl_row)
app.processEvents()
hint = page.stl_row.findChild(QtWidgets.QLabel)
assert hint.fontMetrics().boundingRect(
    QtCore.QRect(0, 0, hint.width(), 10000), QtCore.Qt.TextWordWrap,
    hint.text()).height() <= hint.height()
field_rect = QtCore.QRect(page.txt_stl.mapToGlobal(QtCore.QPoint()), page.txt_stl.size())
hint_rect = QtCore.QRect(hint.mapToGlobal(QtCore.QPoint()), hint.size())
assert not field_rect.intersects(hint_rect)
save = next(button for button in page.findChildren(QtWidgets.QPushButton)
            if button.text() == "Zapisz")
page.editor_scroll.ensureWidgetVisible(save)
app.processEvents()
assert page.editor_scroll.viewport().rect().contains(
    save.mapTo(page.editor_scroll.viewport(), save.rect().center()))
page.txt_stl.setText("  narzedzia/wlasne.stl  ")
assert page.current().stl == "narzedzia/wlasne.stl"
page.txt_stl.clear()
assert any(issue.field == "stl" for issue in page.current().validate())
page.new_tool()
assert page.txt_stl.text() == "" and page.stl_row.isHidden()
assert db.get(70).stl == str(model_path) and model_path.read_bytes() == model_bytes
assert not page.tbl.exists() and not cnc.command.called and not tooldata.save_tool.called
db.close()
'''
        self.run_gui(script)

    def test_editor_preserves_fields_it_does_not_edit(self):
        script = GUI_SETUP + r'''
from dataclasses import replace

original = Tool(12, 3, type="flat", description="Przed edycją", holder="Oprawka ER32",
                params={"d":6, "l":30, "flute_length":15},
                offsets={"Z":42, "X":1.25, "Y":-2.5, "A":3},
                diameter=6, lathe={"I":80, "J":20, "Q":3}, life_min=120, used_min=7)
db.update(original)
page = ToolsPage(SimpleNamespace(c=model.load_tokens()["kolory"]), str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.load(db.get(12))
history = db.history()
page.txt_desc.setText("Po edycji")
page.spin_z.setValue(43)
edited = page.current()
assert edited.holder == original.holder
assert edited.life_min == 120 and edited.used_min == 7
assert edited.lathe == original.lathe
assert edited.offsets == {**original.offsets, "Z":43}
assert edited.description == "Po edycji" and not edited.validate()
special = Tool(70, 70, type="special_stl", stl="narzedzia/żółć.stl",
               params={"d":4, "l":20}, offsets={"Z":25})
db.add(special)
page.load(db.get(70))
assert page.current().stl == special.stl and not page.current().validate()
page.load(replace(original, number=99, pocket=99))  # A new T must not inherit hidden data.
new = page.current()
assert new.number == 99 and new.holder == "" and new.stl is None
assert new.life_min is None and new.used_min == 0 and new.lathe == {}
assert new.offsets == {"Z":42}
assert len(db.history()) == len(history) + 1  # Only the explicit STL fixture was added.
assert db.get(12) == original and db.get(99) is None
assert not page.tbl.exists() and not cnc.command.called and not tooldata.save_tool.called
db.close()
'''
        self.run_gui(script)

    def test_integer_columns_preserve_trailing_zeroes(self):
        script = GUI_SETUP + r'''
from linumert_tools_page import _fmt

for value in (0, 10, 100, 12000, 12340):
    assert _fmt(value, 0) == str(value), (value, _fmt(value, 0))
assert _fmt(None) == "—" and _fmt(12.500) == "12.5" and _fmt(0.0) == "0"
db.update(Tool(12, 3, type="flat", params={"d":6, "l":30, "flute_length":15,
                                        "flutes":10, "max_rpm":12000}))
page = ToolsPage(SimpleNamespace(c=model.load_tokens()["kolory"]), str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.refresh()
assert page.table.item(0, 7).text() == "10"
assert page.table.item(0, 8).text() == "12000"
db.close()
'''
        self.run_gui(script)

    def test_search_type_refresh_and_selection_do_not_write_or_command_cnc(self):
        script = GUI_SETUP + r'''
before, history = db.tools(), db.history()
tokens = model.load_tokens()
page = ToolsPage(SimpleNamespace(c=tokens["kolory"]), str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.refresh()
visible = lambda: [page.table.item(row, 0).text() for row in range(page.table.rowCount())
                   if not page.table.isRowHidden(row)]
page.table.selectRow(0)
assert page.spin_t.value() == 12
for query, expected in (("t12", ["12"]), ("P9", ["27"]), ("żółć", ["12"]),
                        ("nie ma", []), ("", ["12", "27", "50"])):
    page.search.setText(query)
    assert visible() == expected, (query, visible())
    assert page.spin_t.value() == 12  # No automatic selection/change of the editor.
page.filter_type.setCurrentIndex(page.filter_type.findData("ball"))
assert visible() == ["27"]
page.search.setText("T12")
assert visible() == []
page.search.clear()
page.refresh()  # The unchanged-table optimization must preserve active filters.
assert visible() == ["27"]
page.filter_type.setCurrentIndex(page.filter_type.findData(None))
assert visible() == ["50"]
page.filter_type.setCurrentIndex(0)
page.search.setText("Kulový")
assert visible() == []
page.search.setText("Kulowy")
assert visible() == ["27"]
page.table.selectRow(1)
assert page.spin_t.value() == 27
page.search.clear()
page.filter_type.setCurrentIndex(0)
page.table.selectRow(2)
page.table.setCurrentCell(2, 3)
assert page.spin_t.value() == 50
page.txt_desc.setText("Niezapisana edycja T50")
page.filter_type.setCurrentIndex(page.filter_type.findData("ball"))
warnings = []
previous = QtCore.qInstallMessageHandler(lambda kind, context, text: warnings.append(text))
db.add(Tool(30, 30, type="ball", params={"d":10, "l":50}))
page.refresh()
assert visible() == ["27", "30"]
assert page.table.selectionModel().selectedRows()[0].data(QtCore.Qt.UserRole) == 50
assert page.table.currentColumn() == 3
assert page.spin_t.value() == 50 and page.txt_desc.text() == "Niezapisana edycja T50"
db.update(Tool(50, 20, description="Zmiana zewnętrzna", diameter=5))
page.refresh()
assert page.table.selectionModel().selectedRows()[0].data(QtCore.Qt.UserRole) == 50
assert page.txt_desc.text() == "Niezapisana edycja T50"
db.remove(50)
page.refresh()
assert not page.table.selectedItems() and page.table.currentRow() == -1
assert page.spin_t.value() == 50 and page.txt_desc.text() == "Niezapisana edycja T50"
QtCore.qInstallMessageHandler(previous)
assert not any("already owned" in text for text in warnings), warnings
assert len(db.history()) == len(history) + 3  # Only explicit fixture changes wrote data.
assert db.tools()[:2] == before[:2]
assert not page.tbl.exists()
assert not cnc.command.called and not tooldata.save_tool.called
window = QtWidgets.QWidget()
window.setObjectName("lrtRoot")
window.setStyleSheet(model.shell_qss(tokens))
QtWidgets.QVBoxLayout(window).addWidget(page)
window.resize(1200, 720)
window.show()
app.processEvents()
assert window.grab().save(str(work / "tool-filters.png"))
db.close()
'''
        self.run_gui(script)

    def test_export_whole_database_cancel_and_write_error(self):
        script = GUI_SETUP + r'''
from unittest.mock import patch

db.update(Tool(12, 3, type="flat", description='Frez ŻÓŁĆ, "lewy"', holder="Oprawka Ł",
               params={"d":6, "l":30, "flute_length":15, "hand":-1, "d_wear":-0.02},
               offsets={"Z":42.1234, "X":-0.001}, diameter=6, life_min=120, used_min=7))
before, history = db.tools(), db.history()
page = ToolsPage(SimpleNamespace(c=model.load_tokens()["kolory"]), str(work / "test.ini"))
page.db, page.tbl = db, work / "tool.tbl"
page.refresh()
page.table.selectRow(0)
page.txt_desc.setText("Niezapisany opis")
page.search.setText("T27")
target = work / "narzedzia.csv"
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(target), "")), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.export.click()
    warning.assert_not_called()
text = target.read_text(encoding="utf-8")
assert text == db.export_csv() and "Niezapisany opis" not in text
restored = ToolDB(work / "restored.db")
restored.import_csv(text)
assert restored.tools() == before  # Includes hidden rows, Unicode and complete geometry.
restored.close()
original = target.read_bytes()
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("", "")):
    page.export.click()
assert target.read_bytes() == original
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(work), "")), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.export.click()  # A directory cannot be replaced by a CSV file.
    warning.assert_called_once()
assert target.read_bytes() == original
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(target), "")), \
        patch.object(db, "export_csv", side_effect=RuntimeError("Baza niedostępna")), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    page.export.click()
    warning.assert_called_once()
assert target.read_bytes() == original
assert db.tools() == before and db.history() == history
assert page.spin_t.value() == 12 and page.txt_desc.text() == "Niezapisany opis"
assert not page.tbl.exists() and not cnc.command.called and not tooldata.save_tool.called
db.close()
'''
        self.run_gui(script)

    def run_gui(self, script):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
                       PYTHONPATH=os.pathsep.join((str(root / "screens/linumert"),
                                                  str(root / "core"))))
            result = subprocess.run([sys.executable, "-c", script, str(root), folder],
                                    env=env, capture_output=True, text=True, timeout=20,
                                    check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
