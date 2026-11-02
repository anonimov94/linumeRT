# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded tool history preserves chronological ordering. Model-Author: Codex."""

import unittest
from dataclasses import replace

from linumert.tools.db import Tool, ToolDB


class ToolHistoryLimitTests(unittest.TestCase):
    def test_latest_entries_are_selected_before_decoding(self):
        with ToolDB(":memory:") as db:
            tool = Tool(1, 1)
            db.add(tool)
            for value in ("pierwsza", "druga", "trzecia"):
                db.update(replace(tool, description=value))
            db.add(Tool(2, 2))
            self.assertEqual(len(db.history(1)), 4)
            latest = db.history(1, limit=2)
            self.assertEqual([row["after"]["description"] for row in latest], ["druga", "trzecia"])
            self.assertEqual(db.history(limit=1)[0]["number"], 2)
            self.assertEqual(db.history(99, limit=1), [])
            # A damaged old snapshot must not be decoded when outside the requested window.
            db.db.execute("UPDATE history SET before = 'invalid json' WHERE id = 1")
            self.assertEqual(db.history(1, limit=2), latest)

    def test_invalid_limits_are_rejected(self):
        with ToolDB(":memory:") as db:
            for limit in (0, -1, True, 1.5, "2"):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    db.history(limit=limit)
