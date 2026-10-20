# SPDX-License-Identifier: GPL-2.0-or-later
"""Program page must start before optional core imports. Model-Author: Codex."""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("PyQt5"), "PyQt5 unavailable")
class ProgramStartupTests(unittest.TestCase):
    def test_startup_defers_core_and_check_loads_it(self):
        root = Path(__file__).resolve().parents[1]
        script = """
import importlib.abc
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import Mock
from PyQt5 import QtWidgets

class NoCore(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "linumert" or fullname.startswith("linumert."):
            raise ImportError("core deliberately unavailable during screen startup")

blocker = NoCore()
sys.meta_path.insert(0, blocker)
action = Mock()
core = types.ModuleType("qtvcp.core")
core.Action = lambda: action
core.Info = lambda: types.SimpleNamespace()
core.Status = lambda: types.SimpleNamespace()
sys.modules["qtvcp"] = types.ModuleType("qtvcp")
sys.modules["qtvcp.core"] = core
app = QtWidgets.QApplication([])
from linumert_program_page import ProgramPage
shell = types.SimpleNamespace(s=types.SimpleNamespace(file="", running=False))
page = ProgramPage(shell)
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "p.ngc"
    path.write_text("M2\\n", encoding="utf-8")
    assert page.show_file(path)
    page.check_button.click()
    assert "niedostępne" in page.message.text()
    sys.meta_path.remove(blocker)
    assert page.check_program() == []
    assert "Nie wykryto" in page.message.text()
assert not action.mock_calls
page.close()
"""
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
                   PYTHONPATH=str(root / "screens/linumert"))
        run = subprocess.run([sys.executable, "-c", script], env=env, cwd=root,
                             capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
