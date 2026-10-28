# SPDX-License-Identifier: GPL-2.0-or-later
"""INI machine units apply to table I/O, not the mm database. Model-Author: Codex."""

import tempfile
import unittest
from pathlib import Path

from linumert.tools.db import Tool, ToolDB
from linumert.tools.tbl import parse_tbl
from linumert_sim.tooldata import open_db, save_tool, table_units


def profile(root, units="inch", seed=""):
    ini = root / "test.ini"
    ini.write_text(f"[TRAJ]\nLINEAR_UNITS = {units}\n[EMCIO]\nTOOL_TABLE = tool.tbl\n"
                   f"[LINUMERT]\nTOOL_DB = tools.db\n{seed}", encoding="utf-8")
    return ini


class ToolTableUnitsTests(unittest.TestCase):
    def test_inch_import_and_save_convert_lengths_but_not_angles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ini = profile(root)
            (root / "tool.tbl").write_text("T1 P1 Z2 A90 D0.25 I95 J155 Q3\n")
            db, table = open_db(ini)
            try:
                original = db.get(1)
                self.assertAlmostEqual(original.diameter, 6.35)
                self.assertAlmostEqual(original.offsets["Z"], 50.8)
                self.assertEqual(original.offsets["A"], 90)
                self.assertEqual(original.lathe, {"I":95, "J":155, "Q":3})
                tool = Tool(1, 1, params={"d":6.35, "d_wear":-0.0254},
                            offsets=original.offsets, lathe=original.lathe)
                save_tool(db, tool, table, units=table_units(ini))
                entry = parse_tbl(table.read_text())[0]
                self.assertAlmostEqual(entry.values["D"], 0.249)
                self.assertEqual(entry.values["Z"], 2)
                self.assertEqual(entry.values["A"], 90)
                self.assertEqual(entry.values["I"], 95)
            finally:
                db.close()

    def test_mm_seed_is_exported_in_machine_units(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ini = profile(root, seed="TOOL_SEED = seed.yaml\n")
            (root / "seed.yaml").write_text(
                "tools:\n- number: 1\n  type: flat\n  length: 50.8\n"
                "  params: {d: 6.35, l: 30, flute_length: 15}\n", encoding="utf-8")
            db, table = open_db(ini)
            try:
                self.assertAlmostEqual(db.get(1).params["d"], 6.35)
                entry = parse_tbl(table.read_text())[0]
                self.assertAlmostEqual(entry.values["D"], 0.25)
                self.assertEqual(entry.values["Z"], 2)
            finally:
                db.close()

    def test_unknown_units_fail_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ini = profile(root, units="cm")
            table = root / "tool.tbl"
            table.write_text("T1 P1 D0.25\n")
            before = table.read_bytes()
            with self.assertRaises(ValueError):
                open_db(ini)
            self.assertFalse((root / "tools.db").exists())
            with ToolDB(":memory:") as db:
                with self.assertRaises(ValueError):
                    save_tool(db, Tool(1, 1), table, units="cm")
                self.assertEqual(db.tools(), [])
                self.assertEqual(db.history(), [])
            self.assertEqual(table.read_bytes(), before)

    def test_known_aliases_and_default(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for value, expected in (("mm", "mm"), ("metric", "mm"),
                                    ("INCH", "inch"), ("in", "inch")):
                with self.subTest(value=value):
                    self.assertEqual(table_units(profile(root, units=value)), expected)
            ini = root / "missing-unit.ini"
            ini.write_text("[TRAJ]\n")
            self.assertEqual(table_units(ini), "mm")
