# SPDX-License-Identifier: GPL-2.0-or-later
"""Process boundary tests without LinuxCNC. Model-Author: Codex."""

import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

from linumert.programs.linuxcnc_check import check_with_linuxcnc


class InterpreterProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "RIP ' $ (test)"
        (self.root / "bin").mkdir(parents=True)
        (self.root / "scripts").mkdir()
        (self.root / "configs/sim/axis").mkdir(parents=True)
        (self.root / "configs/sim/axis/axis.ini").write_text("")
        script = self.root / "scripts/rip-environment"
        script.write_text(f"export PATH={shlex.quote(str(self.root / 'bin'))}:\"$PATH\"\n")
        self.record = self.base / "args.json"
        self.program = self.base / "part ' ; $(touch INJECTED) ; '.ngc"
        self.program.write_text("M2\n")
        self.env = patch.dict(os.environ, {"TEST_RECORD": str(self.record)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def executable(self, body):
        binary = self.root / "bin/rs274"
        binary.write_text(f"#!{sys.executable}\n" + body)
        binary.chmod(0o755)

    def test_literal_paths_and_arguments(self):
        self.executable(
            "import os, sys, json\n"
            "from pathlib import Path\n"
            "Path(os.environ['TEST_RECORD']).write_text(json.dumps(sys.argv[1:]))\n"
            "print('    1 N..... PROGRAM_END()')\n"
        )
        result = check_with_linuxcnc(self.program, self.root)
        self.assertTrue(result.ok, result.messages)
        self.assertEqual(json.loads(self.record.read_text()),
                         ["-i", "axis.ini", "-t", "sim.tbl", "-n", "0", str(self.program)])
        self.assertFalse((self.root / "configs/sim/axis/INJECTED").exists())

    def test_nonzero_exit_never_passes_after_program_end(self):
        self.executable("print('    1 N..... PROGRAM_END()')\nraise SystemExit(7)\n")
        result = check_with_linuxcnc(self.program, self.root)
        self.assertTrue(result.completed)
        self.assertFalse(result.ok)
        self.assertIn("kodem 7", result.messages[-1])

    def test_timeout(self):
        self.executable("import time\ntime.sleep(10)\n")
        result = check_with_linuxcnc(self.program, self.root, timeout=0.05)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.ok)

    def test_system_interpreter_preserves_path(self):
        self.executable(
            "import os, sys, json\n"
            "from pathlib import Path\n"
            "Path(os.environ['TEST_RECORD']).write_text(json.dumps(sys.argv[1:]))\n"
            "print('    1 N..... PROGRAM_END()')\n"
        )
        with patch("linumert.programs.linuxcnc_check.find_linuxcnc", return_value=([], None)):
            with patch.dict(os.environ, {"PATH": str(self.root / "bin")}):
                # Bash is invoked by name, so preserve its directory too.
                os.environ["PATH"] += os.pathsep + "/bin"
                result = check_with_linuxcnc(self.program)
        self.assertTrue(result.ok, result.messages)
        self.assertEqual(json.loads(self.record.read_text()), ["-n", "0", str(self.program)])
