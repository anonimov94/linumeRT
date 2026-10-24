"""Regression coverage for machine-unit limits (031/051, LIMITS-PREFLIGHT).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import tempfile
import unittest
from pathlib import Path

from linumert.programs.limits import check_canon, limits_from_ini


class LimitsUnitsTests(unittest.TestCase):
    def test_machine_limits_and_program_positions_use_millimetres(self):
        for units, extent in (("mm", 254), ("inch", 10), ("in", 10), ("imperial", 10)):
            with self.subTest(units=units), tempfile.TemporaryDirectory() as directory:
                ini = Path(directory) / "machine.ini"
                ini.write_text(
                    f"[TRAJ]\nLINEAR_UNITS = {units}\n"
                    f"[AXIS_X]\nMIN_LIMIT = {-extent}\nMAX_LIMIT = {extent}\n",
                    encoding="utf-8",
                )
                limits = limits_from_ini(ini)
                self.assertEqual(limits["X"], (-254.0, 254.0))
                for canon_units, position in (("MM", 127), ("INCHES", 5)):
                    canon = (f"1 N1 USE_LENGTH_UNITS(CANON_UNITS_{canon_units})\n"
                             f"2 N2 STRAIGHT_FEED({position}, 0, 0, 0, 0, 0)")
                    self.assertEqual(check_canon(canon, limits), [])
                for position, side in ((11, "max"), (-11, "min")):
                    canon = ("1 N1 USE_LENGTH_UNITS(CANON_UNITS_INCHES)\n"
                             f"2 N2 STRAIGHT_FEED({position}, 0, 0, 0, 0, 0)")
                    violations = check_canon(canon, limits)
                    self.assertEqual(len(violations), 1)
                    self.assertEqual(violations[0].side, side)
                    self.assertAlmostEqual(violations[0].value, position * 25.4)
                    self.assertEqual(abs(violations[0].limit), 254.0)
