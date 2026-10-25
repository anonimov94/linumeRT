# SPDX-License-Identifier: GPL-2.0-or-later
"""Samotest czeka na model HMI, nie tylko status CNC. Model-Author: Codex."""
import ast
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class SelftestSynchronizationTest(unittest.TestCase):
    def test_settled_waits_for_hmi_idle(self):
        path = Path(__file__).resolve().parents[1] / "screens/linumert/linumert_shell_selftest.py"
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SelfTest")
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_settled")
        stat = SimpleNamespace(poll=Mock(), interp_state=1, current_vel=0.0, inpos=True)
        namespace = {"STATUS": SimpleNamespace(stat=stat), "time": time}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
        state = SimpleNamespace(interp="run")
        obj = SimpleNamespace(shell=SimpleNamespace(s=state))
        settled = namespace["_settled"]
        self.assertFalse(settled(obj))  # sterownik już idle, widok nadal blokuje przyciski
        state.interp = "idle"
        self.assertTrue(settled(obj))
        stat.current_vel = 1.0
        self.assertFalse(settled(obj))


    def test_finish_exposes_missing_custom_page_instead_of_hiding_fallback(self):
        path = Path(__file__).resolve().parents[1] / "screens/linumert/linumert_shell_selftest.py"
        cls = next(n for n in ast.parse(path.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == "SelfTest")
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_finish")
        namespace = {"json": json, "os": os}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
        with tempfile.TemporaryDirectory() as out:
            obj = SimpleNamespace(timer=SimpleNamespace(stop=Mock()), out=out,
                                  steps=[], errors=[],
                                  shell=SimpleNamespace(tools=None, cycles=object()))
            namespace["_finish"](obj)
            result = json.loads((Path(out) / "wynik.json").read_text())
            self.assertEqual(result["pages"], {"tools": False, "cycles": True})
            self.assertEqual(result["errors"], [])  # no exceptions still allows a degraded page


if __name__ == "__main__":
    unittest.main()
