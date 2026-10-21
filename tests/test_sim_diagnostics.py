# SPDX-License-Identifier: GPL-2.0-or-later
"""Symulacja raportuje zdarzenia bez dostępu do komend CNC. Model-Author: Codex."""
import ast
import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from linumert_sim import live as module
from linumert_sim.engine import Event, Load

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticSimulationTest(unittest.TestCase):
    def test_events_are_reported_without_command_channel(self):
        for kind in ("collision", "overload", "warning"):
            for virtual in (False, True):
                with self.subTest(kind=kind, virtual=virtual), tempfile.TemporaryDirectory() as d:
                    ini = Path(d) / "machine.ini"
                    ini.write_text(f"[LINUMERT]\nVIRTUAL_MODE={int(virtual)}\n")
                    stat = SimpleNamespace(poll=Mock(), file="", actual_position=(0, 0, 0),
                                           spindle=[], motion_type=2, motion_line=1,
                                           current_line=1, tool_in_spindle=0)
                    cnc = SimpleNamespace(stat=Mock(return_value=stat),
                                          command=Mock(side_effect=AssertionError("CNC command")),
                                          error=RuntimeError)
                    live = module.Live(str(ini), None, cnc)
                    event = Event("K-305", kind, 1, 0, (0, 0, 0))
                    live.engine = SimpleNamespace(step=Mock(return_value=[event]),
                                                  _active={("K-305",)}, stock=None,
                                                  tools={}, load=Load())
                    live.reload_tools = Mock()
                    commands = queue.Queue()
                    # Obsługa starych poleceń nie przywraca sterowania CNC.
                    commands.put({"cmd": "estop", "on": True})
                    commands.put({"cmd": "recovery", "on": True})
                    with patch.object(module, "emit") as emit, patch.object(
                            module.time, "sleep",
                            side_effect=lambda _, q=commands: q.put({"cmd": "quit"})):
                        live.run(100, commands)
                    cnc.command.assert_not_called()
                    messages = [call.kwargs for call in emit.call_args_list]
                    self.assertIn({"ev": "event", "sim_time": 0, **event.to_dict()}, messages)
                    self.assertIn({"ev": "alarms", "active": ["K-305"]}, messages)

    def test_reset_changes_only_simulated_material(self):
        live = module.Live.__new__(module.Live)
        live.engine = SimpleNamespace(reset_stock=Mock())
        live.log = module.SimLog()
        self.assertTrue(live.command({"cmd": "stock_reset"}))
        live.engine.reset_stock.assert_called_once_with()
        self.assertFalse(live.command({"cmd": "quit"}))

    def test_gui_reports_diagnostic_event_without_estop_claim(self):
        # Wykonujemy rzeczywistą metodę widoku bez instalacji Qt/OpenGL.
        source = (ROOT / "screens/linumert/linumert_sim_page.py").read_text()
        tree = ast.parse(source)
        page = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SimPage")
        method = next(n for n in page.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_on_event")
        namespace = {"KIND_LEVEL": {"collision": "err"}}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(ROOT), "exec"), namespace)
        shell = SimpleNamespace(show_alarm=Mock(), sim_cause="")
        view = SimpleNamespace(shell=shell, _add_event=Mock())
        namespace["_on_event"](view, {"code": "K-305", "kind": "collision",
                                     "stop": True, "text": "kolizja", "pos": [1, 2, 3]})
        alarm = shell.show_alarm.call_args.args[1]
        self.assertIn("diagnostyka symulacji", alarm)
        self.assertNotIn("E-STOP", alarm)
        self.assertEqual(shell.sim_cause, "")
        view._add_event.assert_called_once()


if __name__ == "__main__":
    unittest.main()
