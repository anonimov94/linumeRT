# SPDX-License-Identifier: GPL-2.0-or-later
"""Regression for cleanup after X11 failure, without LinuxCNC. Model-Author: Codex."""

import ast
import signal
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class CleanupTests(unittest.TestCase):
    def function(self, lookup, kill):
        path = Path(__file__).with_name("test_linuxcnc.py")
        tree = ast.parse(path.read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == "shutdown_simulation")
        namespace = {"qtdragon_window": lookup, "os": SimpleNamespace(killpg=kill),
                     "signal": signal, "subprocess": subprocess}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
        return namespace["shutdown_simulation"]

    def test_window_error_still_stops_process(self):
        kill = Mock()
        stop = self.function(Mock(side_effect=RuntimeError("X11")), kill)
        process = Mock(pid=123)
        process.poll.return_value = None
        with self.assertRaisesRegex(RuntimeError, "X11"):
            stop(process, False)
        kill.assert_called_once_with(123, signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=15)

    def test_stuck_process_escalates_and_reaps(self):
        kill = Mock()
        stop = self.function(Mock(), kill)
        process = Mock(pid=123)
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("linuxcnc", 15), 0]
        stop(process, True)
        self.assertEqual([c.args for c in kill.call_args_list],
                         [(123, signal.SIGTERM), (123, signal.SIGKILL)])
        self.assertEqual(process.wait.call_count, 2)

    def test_exit_race_is_reaped(self):
        kill = Mock(side_effect=ProcessLookupError())
        stop = self.function(Mock(), kill)
        process = Mock(pid=123)
        process.poll.return_value = None
        stop(process, True)
        process.wait.assert_called_once_with(timeout=15)
