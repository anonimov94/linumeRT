# SPDX-License-Identifier: GPL-2.0-or-later
"""Profile i brak cichego dopuszczenia hardware. Model-Author: Codex."""
import configparser
import tempfile
import unittest
from pathlib import Path

from linumert.machine.deployment import check_deployment, read_deployment


def config(profile="hardware"):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read_dict({"LINUMERT": {"MACHINE_PROFILE": profile},
                   "SAFETY": {"ESTOP_MONITOR_PIN": "hm2.card.input-01",
                              "PC_HEARTBEAT_OUTPUT_PIN": "hm2.card.output-01",
                              "PC_WATCHDOG_MONITOR_PIN": "hm2.card.input-02",
                              "EXTERNAL_PC_WATCHDOG": "1", "PHYSICAL_RESET": "1",
                              "AUTOMATIC_RESTART": "0"}})
    return cfg


class DeploymentTest(unittest.TestCase):
    def test_profiles_are_explicit(self):
        for profile in ("", "Hardware", "unknown"):
            self.assertTrue(check_deployment(config(profile)))
        for profile in ("sim", "plant", "hardware"):
            self.assertEqual(check_deployment(config(profile)), [])

    def test_missing_hardware_conditions_refuse_declaration(self):
        for key in config()["SAFETY"]:
            with self.subTest(key=key):
                cfg = config()
                del cfg["SAFETY"][key]
                self.assertTrue(check_deployment(cfg))

    def test_bypass_virtual_and_automatic_restart_refused(self):
        for key in ("HMI_ESTOP_BYPASS", "VIRTUAL_MODE"):
            cfg = config()
            cfg["LINUMERT"][key] = "1"
            self.assertTrue(check_deployment(cfg))
        cfg = config()
        cfg["SAFETY"]["AUTOMATIC_RESTART"] = "1"
        self.assertTrue(check_deployment(cfg))

    def test_software_loop_and_shared_io_are_not_physical_monitors(self):
        for pin in ("iocontrol.0.user-enable-out", "linumert.hmi.estop-ok",
                    "watchdog.ok-out", "lrt-net.0.din-00", "not a pin"):
            cfg = config()
            cfg["SAFETY"]["ESTOP_MONITOR_PIN"] = pin
            self.assertTrue(check_deployment(cfg))
        cfg = config()
        cfg["SAFETY"]["ESTOP_MONITOR_PIN"] = cfg["SAFETY"]["PC_WATCHDOG_MONITOR_PIN"]
        self.assertTrue(check_deployment(cfg))

    def test_halfile_repetition_allowed_but_safety_repetition_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "machine.ini"
            path.write_text("[HAL]\nHALFILE=a.hal\nHALFILE=b.hal\n")
            read_deployment(path)
            for section, key in (("SAFETY", "PHYSICAL_RESET"),
                                 ("LINUMERT", "MACHINE_PROFILE")):
                path.write_text(f"[{section}]\n{key}=1\n{key.lower()}=0\n")
                with self.assertRaises(ValueError):
                    read_deployment(path)
            path.write_text("[SAFETY]\nPHYSICAL_RESET: 1\n")
            with self.assertRaises(ValueError):
                read_deployment(path)


if __name__ == "__main__":
    unittest.main()
