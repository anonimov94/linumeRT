# SPDX-License-Identifier: GPL-2.0-or-later
"""Symulacja raportuje zdarzenia bez dostępu do komend CNC. Model-Author: Codex."""
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



if __name__ == "__main__":
    unittest.main()
