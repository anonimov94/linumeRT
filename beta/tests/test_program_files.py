# SPDX-License-Identifier: GPL-2.0-or-later
"""File integrity tests without LinuxCNC or Qt. Model-Author: Codex."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from linumert.programs.files import EDIT_BYTES, read_editable, save_new_program


class ProgramFilesTests(unittest.TestCase):
    def test_roundtrip_full_unicode_program(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "część.ngc"
            text = "; próba\n" * 3000 + "M2\n"
            save_new_program(path, text)
            self.assertEqual(read_editable(path), text)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_existing_file_and_symlink_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.ngc"
            path.write_text("original")
            link = Path(folder) / "link.ngc"
            link.symlink_to(path)
            for target in (path, link):
                with self.assertRaises(FileExistsError):
                    save_new_program(target, "new")
            self.assertEqual(path.read_text(), "original")
            self.assertTrue(link.is_symlink())
            self.assertEqual(len(list(Path(folder).iterdir())), 2)

    def test_invalid_encoding_and_size_do_not_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.ngc"
            path.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                read_editable(path)
            path.write_bytes(b"a" * (EDIT_BYTES + 1))
            with self.assertRaises(ValueError):
                read_editable(path)
            target = Path(folder) / "new.ngc"
            with self.assertRaises(ValueError):
                save_new_program(target, "a" * (EDIT_BYTES + 1))
            self.assertFalse(target.exists())

    def test_publish_failure_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("linumert.programs.files.os.link", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    save_new_program(Path(folder) / "new.ngc", "M2\n")
            self.assertEqual(list(Path(folder).iterdir()), [])
