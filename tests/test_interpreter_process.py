# SPDX-License-Identifier: GPL-2.0-or-later
"""Process boundary tests without LinuxCNC. Model-Author: Codex."""

import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
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
        args = json.loads(self.record.read_text())
        self.assertEqual(args[0], "-i")
        self.assertEqual(Path(args[1]).name, "analysis.ini")
        self.assertEqual(args[2:4], ["-t", str(self.root / "configs/sim/axis/sim.tbl")])
        self.assertEqual(args[4], "-v")
        self.assertEqual(args[6:], ["-n", "0", str(self.program)])
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
        args = json.loads(self.record.read_text())
        self.assertEqual(args[0], "-v")
        self.assertEqual(args[2:], ["-n", "0", str(self.program)])

    def test_legacy_rs274_cannot_truncate_live_mmap_or_shared_parameters(self):
        """Reproduce the 2.9.10 startup side effect before parsing any CLI options."""
        live = self.base / "live-home"
        live.mkdir()
        mmap = live / ".tool.mmap"
        mmap.write_bytes(b"live controller tool mapping")
        sim_var = self.root / "configs/sim/axis/sim.var"
        sim_var.write_text("original parameters\n")
        self.executable(
            "import os,json\nfrom pathlib import Path\n"
            "home=Path(os.environ['HOME'])\n"
            "(home/'.tool.mmap').write_bytes(b'')\n"
            "Path('sim.var').write_text('interpreter changes')\n"
            "Path(os.environ['TEST_RECORD']).write_text(json.dumps(\n"
            "[str(home), str(Path.cwd()), os.environ['TMPDIR']]))\n"
            "print('    1 N..... PROGRAM_END()')\n"
        )
        with patch.dict(os.environ, {"HOME": str(live)}):
            for _ in range(2):
                self.assertTrue(check_with_linuxcnc(self.program, self.root).ok)
                home, cwd, tmp = json.loads(self.record.read_text())
                self.assertEqual(home, cwd)
                self.assertEqual(home, tmp)
                self.assertNotEqual(home, str(live))
                self.assertFalse(Path(home).exists(), "private state was not cleaned")
            self.assertEqual(os.environ["HOME"], str(live))
        self.assertEqual(mmap.read_bytes(), b"live controller tool mapping")
        self.assertEqual(sim_var.read_text(), "original parameters\n")

    def test_flooding_semantic_check_is_incomplete(self):
        self.executable("import os\nwhile True: os.write(1,b'x'*65536)\n")
        result = check_with_linuxcnc(self.program, self.root)
        self.assertFalse(result.ok)
        self.assertFalse(result.completed)
        self.assertIn("limit danych", result.messages[0])

    def test_parameter_file_exists_before_first_save_and_ini_cannot_share_it(self):
        shared = self.base / "controller.var"
        shared.write_text("live parameters\n")
        (self.root / "configs/sim/axis/axis.ini").write_text(
            f"[RS274NGC]\nPARAMETER_FILE = {shared}\n")
        self.executable(
            "import configparser,sys,os\nfrom pathlib import Path\n"
            "args=sys.argv[1:]\n"
            "cli=Path(args[args.index('-v')+1])\n"
            "assert cli.is_file(), 'first save would emit missing-backup warning'\n"
            "config=configparser.ConfigParser()\n"
            "config.read(args[args.index('-i')+1])\n"
            "actual=Path(config['RS274NGC']['PARAMETER_FILE']).resolve()\n"
            "assert actual == cli and actual.parent == Path(os.environ['HOME'])\n"
            "actual.write_text('offline changes')\n"
            "print('    1 N..... PROGRAM_END()')\n"
        )
        result = check_with_linuxcnc(self.program, self.root)
        self.assertTrue(result.ok, result.messages)
        self.assertEqual(shared.read_text(), "live parameters\n")

    def test_estimate_never_returns_partial_or_nonzero_exit_result(self):
        from linumert.programs.estimate import estimate_ngc

        for body, message in [
            ("while True: pass\n", "limit czasu"),
            ("import os\nwhile True: os.write(2,b'x'*65536)\n", "limit danych"),
            ("print('    1 N..... PROGRAM_END()')\nraise SystemExit(7)\n", "końca"),
        ]:
            with self.subTest(message=message):
                self.executable(body)
                with self.assertRaisesRegex(ValueError, message):
                    estimate_ngc(self.program, self.base / "unused.ini", self.root, timeout=0.5)
