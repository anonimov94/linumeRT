# SPDX-License-Identifier: GPL-2.0-or-later
"""Audyt HAL nie wykonuje skryptów ani nie wymaga LinuxCNC. Model-Author: Codex."""
import configparser
import tempfile
import unittest
from pathlib import Path

from linumert.machine.hal_audit import audit_hal

HAL = """net safety hm2.in-01 => iocontrol.0.emc-enable-in
net heartbeat linumert.hmi-heartbeat => hm2.out-01
net feedback hm2.in-02 => linumert.pc-watchdog-ok
"""


class HalAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = configparser.ConfigParser()
        self.cfg.read_dict({"LINUMERT": {"MACHINE_PROFILE": "hardware"},
                            "SAFETY": {"ESTOP_MONITOR_PIN": "hm2.in-01",
                                       "PC_HEARTBEAT_OUTPUT_PIN": "hm2.out-01",
                                       "PC_WATCHDOG_MONITOR_PIN": "hm2.in-02"}})

    def audit(self, text):
        path = self.root / "main.hal"
        path.write_text(text)
        return audit_hal([path], self.cfg, self.root)

    def test_direct_connections_and_comments(self):
        self.assertEqual(self.audit(HAL + "# user-enable-out is a comment\n"), [])

    def test_loop_split_across_net_lines_is_detected(self):
        errors = self.audit(HAL + "net safety iocontrol.0.user-enable-out\n")
        self.assertTrue(any("pętla" in e for e in errors))

    def test_missing_each_connection_is_reported(self):
        for line in HAL.splitlines():
            self.assertTrue(self.audit(HAL.replace(line, "")))

    def test_includes_are_relative_to_configuration_and_cycles_fail(self):
        (self.root / "child.hal").write_text(HAL)
        self.assertEqual(self.audit("source child.hal\n"), [])
        (self.root / "child.hal").write_text("source main.hal\n")
        self.assertTrue(any("cykliczne" in e for e in self.audit("source child.hal\n")))

    def test_unresolved_missing_and_tcl_files_fail(self):
        for text in ("source absent.hal", "source $dynamic", "source config.tcl",
                     "net [CONFIG]SIGNAL hm2.in-01", "net 'unfinished"):
            self.assertTrue(self.audit(text))

    def test_mutations_not_modelled_are_reported(self):
        for text in ("unlinkp hm2.in-01", "delsig safety",
                     "setp iocontrol.0.emc-enable-in 1"):
            self.assertTrue(self.audit(HAL + text))

    def test_pin_cannot_belong_to_two_signals(self):
        self.assertTrue(self.audit(HAL + "net other hm2.in-01\n"))

    def test_arrows_and_continuations(self):
        text = HAL.replace("=> iocontrol", "=> \\\n iocontrol")
        self.assertEqual(self.audit(text), [])


if __name__ == "__main__":
    unittest.main()
