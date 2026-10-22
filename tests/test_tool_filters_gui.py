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
