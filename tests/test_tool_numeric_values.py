# SPDX-License-Identifier: GPL-2.0-or-later
"""Reject invalid tool numbers before database/file mutation. Model-Author: Codex."""

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from linumert.tools.db import Tool, ToolDB, ToolDBError
from linumert.tools.tbl import parse_tbl


class ToolNumericValuesTests(unittest.TestCase):
    def test_invalid_values_and_shapes_do_not_enter_database(self):
        cases = [{"diameter": value} for value in
                 (float("inf"), float("nan"), -1, "5", True)]
        cases += [{"offsets": value} for value in
                  ({"Z": float("inf")}, {"X": "1"}, {"Y": True}, {"A": 1 << 2000}, [], None)]
        cases += [{"lathe": value} for value in
                  ({"Q":2.5}, {"Q":10}, {"Q":-1}, {"Q":True}, {"I":float("nan")},
                   {"J":"1"}, {"unknown":0}, [])]
        cases += [{"params": value} for value in ([], None, {"d": 1 << 2000})]
        with ToolDB(":memory:") as db:
            for values in cases:
                with self.subTest(values=values), self.assertRaises(ToolDBError):
                    db.add(Tool(1, 1, **values))
                self.assertEqual(db.tools(), [])
                self.assertEqual(db.history(), [])

    def test_valid_signed_offsets_and_integer_orientation_export(self):
        with ToolDB(":memory:") as db, tempfile.TemporaryDirectory() as folder:
            db.add(Tool(1, 1, diameter=0, offsets={"X":1.25, "Z":-2.125, "A":-30},
                        lathe={"Q":2.0, "I":-10, "J":40}))
            target = Path(folder) / "tool.tbl"
            db.export_tbl(target)
            entry = parse_tbl(target.read_text())[0]
            self.assertEqual(entry.orientation, 2)
            self.assertEqual(entry.values["Z"], -2.125)
            self.assertEqual(entry.values["A"], -30)
            self.assertEqual(entry.values["D"], 0)

    def test_invalid_legacy_database_does_not_replace_table(self):
        with ToolDB(":memory:") as db, tempfile.TemporaryDirectory() as folder:
            db.add(Tool(1, 1, diameter=6))
            target = Path(folder) / "tool.tbl"
            db.export_tbl(target)
            before, history = target.read_bytes(), db.history()
            db.db.execute("UPDATE tools SET diameter = ?", (float("inf"),))
            with self.assertRaises(ToolDBError):
                db.export_tbl(target)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(db.history(), history)

    def test_invalid_csv_batch_is_not_partially_imported(self):
        with ToolDB(":memory:") as db:
            original = Tool(1, 1, description="Before")
            db.add(original)
            history = db.history()
            reader = csv.DictReader(io.StringIO(db.export_csv()))
            first = next(reader)
            first["description"] = "Must not be written"
            second = {**first, "number":"2", "pocket":"2",
                      "offsets":json.dumps({"Z":float("inf")})}
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows([first, second])
            with self.assertRaises(ToolDBError):
                db.import_csv(output.getvalue())
            self.assertEqual(db.tools(), [original])
            self.assertEqual(db.history(), history)
