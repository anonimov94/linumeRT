# SPDX-License-Identifier: GPL-2.0-or-later
"""Live simulation uses mm for both metric and inch status. Model-Author: Codex."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from linumert_sim.live import Live, main


class LiveUnitsTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.instances = []
        self.output_patch = patch("linumert_sim.live.emit")
        self.output = self.output_patch.start()

    def tearDown(self):
        for live in self.instances:
            live.close()
            if live.db is not None:
                live.db.close()
        self.output_patch.stop()
        self.work.cleanup()

    def make_live(self, units, *, seed=False):
        root = Path(self.work.name) / f"{units}-{len(self.instances)}"
        root.mkdir()
        ini = root / "machine.ini"
        ini.write_text(f"[TRAJ]\nLINEAR_UNITS = {units}\n[RS274NGC]\n"
                       "PARAMETER_FILE = machine.var\n[EMCIO]\nTOOL_TABLE = tool.tbl\n"
                       "[LINUMERT]\nTOOL_DB = tools.db\n" +
                       ("TOOL_SEED = seed.yaml\n" if seed else ""))
        if seed:
            (root / "seed.yaml").write_text(
                "tools:\n- number: 1\n  type: flat\n  length: 10\n"
                "  params: {d: 6, l: 8, flute_length: 8}\n")
        factor = 25.4 if units == "inch" else 1.0
        status = SimpleNamespace(
            poll=Mock(), actual_position=[0.0] * 9, g5x_offset=[0.0] * 9,
            spindle=[{"enabled":True, "direction":1, "speed":1200}], motion_type=2,
            motion_line=4, current_line=4, tool_in_spindle=1,
            tool_table=[SimpleNamespace(id=1, zoffset=10 / factor, diameter=6 / factor)])
        cnc = SimpleNamespace(stat=lambda: status,
                              command=Mock(side_effect=AssertionError("unexpected CNC command")))
        live = Live(str(ini), None, cnc)
        live.map_file = root / "material.f32"
        self.instances.append(live)
        return live, status, cnc

    def test_status_and_tool_table_become_physical_mm(self):
        for units in ("mm", "inch"):
            with self.subTest(units=units):
                live, status, cnc = self.make_live(units)
                factor = 25.4 if units == "inch" else 1.0
                status.actual_position[:3] = [value / factor for value in (12.7, -25.4, 50.8)]
                sample = live.sample(1.0)
                np.testing.assert_allclose(sample.nose, (12.7, -25.4, 50.8))
                self.assertEqual((sample.rpm, sample.motion, sample.line), (1200, "feed", 4))
                live.reload_tools()
                self.assertAlmostEqual(live.engine.tools[1].gauge, 10)
                self.assertAlmostEqual(live.engine.tools[1].diameter, 6)
                self.assertFalse(cnc.command.called)

    def test_stock_origin_from_parameter_file_and_status_is_scaled(self):
        for saved in (False, True):
            with self.subTest(saved=saved):
                live, status, _cnc = self.make_live("inch")
                status.g5x_offset[:3] = (1, -2, 0.5)
                if saved:
                    (live.ini_path.parent / "machine.var").write_text("5221 1\n5222 -2\n5223 0.5\n")
                live.set_stock(";@STOCK BOX X10 Y20 Z5 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=0")
                stock = live.engine.stock
                self.assertAlmostEqual(stock.x0, 25.4)
                self.assertAlmostEqual(stock.y0, -50.8)
                self.assertAlmostEqual(stock.z_top, 12.7)
                self.assertAlmostEqual(stock.z_bottom, 7.7)

    def test_metric_and_inch_profiles_remove_identical_material_and_record_same_tip(self):
        maps, traces = [], []
        for units in ("mm", "inch"):
            live, status, cnc = self.make_live(units, seed=True)
            live.reload_tools()
            live.set_stock(";@STOCK BOX X10 Y10 Z5 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=0")
            before = live.engine.stock.volume()
            factor = 25.4 if units == "inch" else 1.0
            for t, x in enumerate((1, 5)):
                status.actual_position[:3] = [x / factor, 1 / factor, 8 / factor]
                sample = live.sample(float(t))
                live.engine.step(sample)
                live.record_resume_sample(sample)
            self.assertLess(live.engine.stock.volume(), before)
            maps.append(live.engine.stock.h.copy())
            traces.append(live._resume_trace)
            self.assertFalse(cnc.command.called)
        np.testing.assert_allclose(maps[0], maps[1])
        np.testing.assert_allclose(traces[0], traces[1], atol=1e-9)

    def test_unknown_units_report_error_before_status_or_worker_start(self):
        ini = Path(self.work.name) / "invalid.ini"
        ini.write_text("[TRAJ]\nLINEAR_UNITS = cm\n")
        cnc = SimpleNamespace(stat=Mock(), command=Mock())
        with patch.dict("sys.modules", {"linuxcnc":cnc}), \
                patch("linumert_sim.live.os.nice"), \
                patch("linumert_sim.live.threading.Thread") as worker:
            self.assertEqual(main(["--ini", str(ini)]), 2)
        worker.assert_not_called()
        cnc.stat.assert_not_called()
        cnc.command.assert_not_called()
        self.assertEqual(self.output.call_args.kwargs["ev"], "error")
        self.assertIn("cm", self.output.call_args.kwargs["text"])
