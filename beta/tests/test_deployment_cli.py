# SPDX-License-Identifier: GPL-2.0-or-later
"""Pełna ścieżka CLI bez wykonywania HAL. Model-Author: Codex."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from linumert.machine.deployment import hal_files_from_ini, main

INI = """[LINUMERT]
MACHINE_PROFILE=hardware
[SAFETY]
ESTOP_MONITOR_PIN=hm2.in-01
PC_HEARTBEAT_OUTPUT_PIN=hm2.out-01
PC_WATCHDOG_MONITOR_PIN=hm2.in-02
EXTERNAL_PC_WATCHDOG=1
PHYSICAL_RESET=1
AUTOMATIC_RESTART=0
[HAL]
HALFILE=first.hal
HALFILE=second.hal
POSTGUI_HALFILE=post.hal
"""


class DeploymentCliTest(unittest.TestCase):
    def test_all_files_checked_and_loop_in_last_file_blocks_result(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ini = root / "machine.ini"
            ini.write_text(INI)
            (root / "first.hal").write_text(
                "net monitor hm2.in-01 => iocontrol.0.emc-enable-in\n")
            (root / "second.hal").write_text(
                "net beat linumert.hmi-heartbeat => hm2.out-01\n")
            post = root / "post.hal"
            post.write_text("net feedback hm2.in-02 => linumert.pc-watchdog-ok\n")
            self.assertEqual(len(hal_files_from_ini(ini)), 3)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = main([str(ini), "--hal-from-ini"])
            report = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertTrue(report["static_hal_passed"])
            self.assertFalse(report["hardware_verified"])
            post.write_text(post.read_text() + "net monitor iocontrol.0.user-enable-out\n")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = main([str(ini), "--hal-from-ini"])
            report = json.loads(output.getvalue())
            self.assertEqual(result, 2)
            self.assertTrue(report["declaration_complete"])
            self.assertFalse(report["static_hal_passed"])

    def test_missing_files_and_inline_commands_are_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            ini = Path(d) / "machine.ini"
            for text in (INI, INI + "HALCMD=setp iocontrol.0.emc-enable-in 1\n"):
                ini.write_text(text)
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main([str(ini), "--hal-from-ini"]), 2)
                self.assertTrue(json.loads(output.getvalue())["errors"])


if __name__ == "__main__":
    unittest.main()
