# SPDX-License-Identifier: GPL-2.0-or-later
"""Actual Qt inventory dialog in an isolated process. Model-Author: Codex."""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("PyQt5"), "PyQt5 unavailable")
class DoctorGuiTests(unittest.TestCase):
    def test_diagnostics_opens_readonly_report_without_commands(self):
        root = Path(__file__).resolve().parents[1]
        script = """
import sys
import types
from unittest.mock import Mock, patch
from PyQt5 import QtWidgets

app = QtWidgets.QApplication([])
action = Mock()
core = types.ModuleType("qtvcp.core")
core.Action = lambda: action
core.Info = lambda: types.SimpleNamespace()
core.Status = lambda: types.SimpleNamespace()
sys.modules["qtvcp"] = types.ModuleType("qtvcp")
sys.modules["qtvcp.core"] = core
import linumert_shell_model as model
from linumert_shell_pages import DiagPage
from linumert_doctor_dialog import DoctorDialog

shell = types.SimpleNamespace(c=model.load_tokens()["kolory"])
page = DiagPage(shell)
with patch.object(DoctorDialog, "exec_", return_value=0) as show:
    page.doctor_button.click()
    assert show.call_count == 1
dialog = DoctorDialog()
assert dialog.output.isReadOnly()
assert "NIEZWERYFIKOWANE" in dialog.output.toPlainText()
dialog.refresh_report()
assert not action.mock_calls
dialog.close()
page.close()
"""
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        paths = [str(root / "core"), str(root / "screens/linumert")]
        env["PYTHONPATH"] = os.pathsep.join(paths)
        run = subprocess.run([sys.executable, "-c", script], env=env, cwd=root,
                             capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
