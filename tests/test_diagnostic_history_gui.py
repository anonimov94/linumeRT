# SPDX-License-Identifier: GPL-2.0-or-later
"""Click actual diagnostic filters/export and reopen history. Model-Author: Codex."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("PyQt5"), "PyQt5 unavailable")
class DiagnosticHistoryGuiTests(unittest.TestCase):
    def test_filters_export_reopen_and_missing_disk(self):
        root = Path(__file__).resolve().parents[1]
        script = r'''
import csv
import os
import sys
from pathlib import Path
from unittest.mock import patch
from PyQt5 import QtWidgets
from linumert_log_view import LogView, journal_path

app = QtWidgets.QApplication([])
work = Path(sys.argv[1])
colors = {"err": "red", "amber": "orange", "fg2": "gray"}
os.environ["INI_FILE_NAME"] = str(work / "first.ini")
first = journal_path()
os.environ["INI_FILE_NAME"] = str(work / "second.ini")
assert first != journal_path()
view = LogView(colors, path=work / "journal.db")
for i in range(205):
    view.add("info", "Informacja " + str(i))
view.add("err", 'E-4003; łącze\nnapęd "X"')
assert view.list.count() == 200
view.search.setText("informacja")
output = work / "messages.csv"
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(output), "")):
    view.export.click()
with output.open(encoding="utf-8-sig", newline="") as stream:
    assert len(list(csv.reader(stream, delimiter=";"))) == 206
view.search.clear()
view.level.setCurrentIndex(1)
assert view.list.count() == 1
view.search.setText("E-4003")
assert "łącze" in view.list.item(0).text()
view.resize(1050, 350)
view.show()
app.processEvents()
assert view.grab().save(str(work / "history.png"))
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("", "")):
    view.export.click()
with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(work), "")), \
        patch.object(QtWidgets.QMessageBox, "warning") as warning:
    view.export.click()
    assert warning.called
view.journal.close()
restored = LogView(colors, path=work / "journal.db")
restored.level.setCurrentIndex(1)
assert restored.list.count() == 1
restored.journal.close()
blocked = work / "blocked"
blocked.write_text("not a directory")
fallback = LogView(colors, path=blocked / "history.db")
fallback.add("err", "Nadal widoczny")
assert fallback.list.count() == 1 and "tylko w pamięci" in fallback.summary.text()
fallback.journal.close()

# Actual Diagnostics page composition, without a CNC connection or commands.
from types import ModuleType, SimpleNamespace
core = ModuleType("qtvcp.core")
core.Action = core.Info = core.Status = lambda: SimpleNamespace()
sys.modules["qtvcp"] = ModuleType("qtvcp")
sys.modules["qtvcp.core"] = core
import linumert_shell_pages as pages
import linumert_shell_model as model
tokens = model.load_tokens()
window = QtWidgets.QWidget()
window.setObjectName("lrtRoot")
window.setStyleSheet(model.shell_qss(tokens))
layout = QtWidgets.QVBoxLayout(window)
page = pages.DiagPage(SimpleNamespace(c=tokens["kolory"]))
layout.addWidget(page)
page.add_log("err", "E-4003 — brak ramek magistrali")
page.log_view.level.setCurrentIndex(1)
assert page.log.count() == 1
window.resize(1100, 600)
window.show()
app.processEvents()
assert window.height() == 600
page.scroll.ensureWidgetVisible(page.log_view.summary)
app.processEvents()
assert page.scroll.verticalScrollBar().maximum() > 0
assert page.log_view.export.isEnabled()
assert window.grab().save(str(work / "diagnostics.png"))
page.log_view.journal.close()
'''
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
                       XDG_DATA_HOME=folder,
                       PYTHONPATH=str(root / "screens/linumert") + os.pathsep + str(root / "core"))
            result = subprocess.run([sys.executable, "-c", script, folder], env=env,
                                    capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
