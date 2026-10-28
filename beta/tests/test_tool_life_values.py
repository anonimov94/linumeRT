# SPDX-License-Identifier: GPL-2.0-or-later
"""Finite, nonnegative tool usage and optional planned life. Model-Author: Codex."""

import csv
import io
import unittest
from dataclasses import replace

from linumert.tools.db import Tool, ToolDB, ToolDBError


class ToolLifeValuesTests(unittest.TestCase):
    def test_valid_life_and_usage_including_overdue_tool(self):
        for life, used in ((None, 0), (120.25, 7.125), (120, 250)):
            with self.subTest(life=life, used=used), ToolDB(":memory:") as db:
                tool = Tool(1, 1, life_min=life, used_min=used)
                db.add(tool)
                self.assertEqual(db.get(1), tool)

    def test_invalid_values_are_reported_without_mutation(self):
        with ToolDB(":memory:") as db:
            tool = Tool(1, 1, life_min=120, used_min=7)
            db.add(tool)
            history = db.history()
            for name in ("life_min", "used_min"):
                invalid = (-1, float("nan"), float("inf"), "7", True)
                invalid += (0,) if name == "life_min" else (None,)
                for value in invalid:
                    with self.subTest(name=name, value=value), \
                            self.assertRaises(ToolDBError) as error:
                        db.update(replace(tool, **{name: value}))
                    self.assertTrue(any(issue.field == name for issue in error.exception.issues))
                    self.assertEqual(db.get(1), tool)
                    self.assertEqual(db.history(), history)

    def test_nonfinite_csv_does_not_change_database(self):
        with ToolDB(":memory:") as db:
            tool = Tool(1, 1, life_min=120, used_min=7)
            db.add(tool)
            history = db.history()
            reader = csv.DictReader(io.StringIO(db.export_csv()))
            rows = list(reader)
            rows[0]["used_min"] = "inf"
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            with self.assertRaises(ToolDBError):
                db.import_csv(output.getvalue())
            self.assertEqual(db.get(1), tool)
            self.assertEqual(db.history(), history)
