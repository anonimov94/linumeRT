# SPDX-License-Identifier: GPL-2.0-or-later
"""Persistence, literal filters and failure fallback. Model-Author: Codex."""

import csv
import io
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from linumert.diag.journal import Journal


class DiagnosticHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.sqlite3"

    def open(self, **kwargs):
        journal = Journal(self.path, **kwargs)
        self.addCleanup(journal.close)
        return journal

    def test_restart_preserves_unicode_newlines_levels_and_csv(self):
        journal = self.open()
        journal.add("info", "Start")
        message = 'E-4003; brak łącza\nnapęd "X"'
        journal.add("err", message)
        journal.close()
        restored = self.open()
        self.assertEqual([e[2] for e in restored.matching()], [message, "Start"])
        rows = list(csv.reader(io.StringIO(restored.csv()), delimiter=";"))
        self.assertEqual(rows[1][1:], ["err", message])
        self.assertIsNotNone(datetime.fromisoformat(rows[1][0]).tzinfo)
        self.assertEqual(restored.warning, "")

    def test_retention_bounds_disk_and_memory(self):
        journal = self.open(limit=3)
        for number in range(7):
            journal.add("info", str(number))
        self.assertEqual([e[2] for e in journal.matching()], ["6", "5", "4"])
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM messages").fetchone()[0], 3)
        journal.close()
        self.assertEqual(len(self.open(limit=3).matching()), 3)

    def test_filters_are_literal_case_insensitive_and_combine_with_level(self):
        journal = self.open()
        journal.add("err", "Żółć 100%_ napęd")
        journal.add("warn", "żółć — ostrzeżenie")
        self.assertEqual(len(journal.matching(query="ŻÓŁĆ")), 2)
        self.assertEqual(len(journal.matching("err", "100%_")), 1)
        self.assertEqual(journal.matching("err", "' OR 1=1"), [])
        self.assertEqual(len(list(csv.reader(io.StringIO(journal.csv("warn")),
                                             delimiter=";"))), 2)

    def test_corrupt_database_is_not_overwritten_and_new_messages_remain_visible(self):
        self.path.write_bytes(b"not a sqlite database")
        journal = self.open()
        journal.add("err", "Nowy komunikat")
        self.assertIn("tylko w pamięci", journal.warning)
        self.assertEqual(journal.matching()[0][2], "Nowy komunikat")
        self.assertEqual(self.path.read_bytes(), b"not a sqlite database")

    def test_busy_database_does_not_drop_the_current_message(self):
        journal = self.open()
        journal.add("info", "Przed blokadą")
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN EXCLUSIVE")
            journal.add("err", "Podczas blokady")
        self.assertIn("tylko w pamięci", journal.warning)
        self.assertEqual(journal.matching()[0][2], "Podczas blokady")
        journal.add("info", "Po blokadzie")
        self.assertEqual(len(journal.matching()), 3)

    def test_unwritable_parent_falls_back_without_erasing_messages(self):
        self.path.parent.joinpath("not-a-directory").write_text("keep")
        journal = Journal(self.path.parent / "not-a-directory" / "journal.db")
        self.addCleanup(journal.close)
        journal.add("info", "Dostępny w pamięci")
        self.assertTrue(journal.warning)
        self.assertEqual(len(journal.matching()), 1)


if __name__ == "__main__":
    unittest.main()
