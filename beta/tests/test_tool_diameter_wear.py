# SPDX-License-Identifier: GPL-2.0-or-later
"""Diameter wear reaches tool.tbl exactly once. Model-Author: Codex."""

import tempfile
import unittest
from pathlib import Path

from linumert.tools.db import Tool, ToolDB, ToolDBError
from linumert.tools.tbl import parse_tbl
from linumert_sim.tooldata import cutters, save_tool


def tool(wear):
    return Tool(1, 1, type="flat", params={"d":6, "l":30, "flute_length":15, "d_wear":wear},
                offsets={"Z":42})


class ToolDiameterWearTests(unittest.TestCase):
    def test_both_wear_signs_match_table_and_actual_simulation_cutter(self):
        for wear in (-0.02, 0.02):
            with self.subTest(wear=wear), ToolDB(":memory:") as db, \
                    tempfile.TemporaryDirectory() as folder:
                table = Path(folder) / "tool.tbl"
                save_tool(db, tool(wear), table)
                entry = parse_tbl(table.read_text())[0]
                self.assertAlmostEqual(entry.values["D"], 6 + wear)
                stored = db.get(1)
                self.assertAlmostEqual(stored.diameter, 6 + wear)
                cutter = cutters({1: stored}, [(1, 42, entry.values["D"])])[1]
                self.assertAlmostEqual(2 * cutter.radius, entry.values["D"])
                history = db.history()
                for _ in range(3):
                    self.assertEqual(db.import_tbl(table.read_text()), [])
                self.assertEqual(db.history(), history)

    def test_imported_effective_diameter_keeps_wear_without_doubling(self):
        with ToolDB(":memory:") as db, tempfile.TemporaryDirectory() as folder:
            table = Path(folder) / "tool.tbl"
            save_tool(db, tool(-0.02), table)
            text = "T1 P1 Z42 D5.99\n"
            self.assertEqual(db.import_tbl(text), [1])
            self.assertAlmostEqual(db.get(1).params["d"], 6.01)
            self.assertEqual(db.get(1).params["d_wear"], -0.02)
            self.assertAlmostEqual(db.get(1).diameter, 5.99)
            for _ in range(3):
                self.assertEqual(db.import_tbl(text), [])
                self.assertEqual(db.export_tbl(table).read_text(), text)

    def test_inch_table_does_not_accumulate_wear_on_repeated_import(self):
        with ToolDB(":memory:") as db, tempfile.TemporaryDirectory() as folder:
            db.add(tool(-0.02))
            table = Path(folder) / "tool.tbl"
            text = db.export_tbl(table, units="inch").read_text()
            self.assertAlmostEqual(parse_tbl(text)[0].values["D"] * 25.4, 5.98, places=4)
            db.import_tbl(text, units="inch")
            history = db.history()
            for _ in range(3):
                self.assertEqual(db.import_tbl(text, units="inch"), [])
                self.assertEqual(db.export_tbl(table, units="inch").read_text(), text)
            self.assertEqual(db.history(), history)

    def test_untyped_table_diameter_and_invalid_effective_diameter(self):
        with ToolDB(":memory:") as db:
            plain = Tool(1, 1, diameter=5.98)
            db.add(plain)
            self.assertEqual(db.get(1).tool_diameter(), 5.98)
            for params in ({"d":0.5, "d_wear":-0.5}, {"d_wear":0.02}):
                with self.subTest(params=params), self.assertRaises(ToolDBError):
                    db.add(Tool(2, 2, params=params, diameter=6))
            self.assertEqual(db.tools(), [plain])
