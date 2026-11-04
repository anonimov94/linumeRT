# SPDX-License-Identifier: GPL-2.0-or-later
"""Environment inventory on absent and present components. Model-Author: Codex."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from linumert.diag.doctor import format_report, inspect_environment, main


class DoctorTests(unittest.TestCase):
    def test_missing_cnc_is_reported_without_starting_processes(self):
        with patch("linumert.diag.doctor.shutil.which", return_value=None), \
                patch("linumert.diag.doctor.importlib.util.find_spec", return_value=None), \
                patch("subprocess.Popen", side_effect=AssertionError("process started")):
            report = inspect_environment()
        missing = [c["name"] for c in report["checks"] if c["status"] == "missing"]
        self.assertIn("linuxcnc", missing)
        self.assertIn("PATH:rs274", missing)
        self.assertFalse(report["hardware_verified"])
        self.assertIn("NIEZWERYFIKOWANE", format_report(report))

    def test_present_components_do_not_qualify_machine(self):
        with patch("linumert.diag.doctor.shutil.which", return_value="/usr/bin/tool"), \
                patch("linumert.diag.doctor.importlib.util.find_spec", return_value=object()), \
                patch("pathlib.Path.read_text", return_value="1\n"):
            report = inspect_environment()
        self.assertFalse(report["hardware_verified"])
        self.assertIn("latencja RT", report["not_checked"])
        self.assertIn("latencja niezmierzona", format_report(report))

    def test_json_cli_handles_unavailable_platform(self):
        output = io.StringIO()
        with patch("platform.freedesktop_os_release", side_effect=OSError("absent")), \
                patch("pathlib.Path.read_text", side_effect=OSError("denied")), \
                contextlib.redirect_stdout(output):
            self.assertEqual(main(["--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["schema_version"], 1)
        self.assertIn("brak odczytu", format_report(report))
