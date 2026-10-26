# SPDX-License-Identifier: GPL-2.0-or-later
"""D38 interlocks and compensation-preserving pause state. Model-Author: Codex."""

import unittest
from dataclasses import replace

from linumert.programs.pause_retract import PauseRetract, PauseSnapshot, RetractRefused


def snapshot(correction=410, **changes):
    s = PauseSnapshot(True, True, True, True, ("part.ngc", 3, correction, 43, 54),
                      -20, 0, 0, -120, 0)
    return replace(s, **changes)


class PauseRetractTests(unittest.TestCase):
    def test_wait_for_servo_enable_before_changing_counts_and_latch_its_loss(self):
        c, s = PauseRetract(), snapshot(offset_enabled=False)
        c.start(s, 2, 60)
        for _ in range(10):
            c.tick(s, 0.02)
        self.assertEqual(c.phase, "arming")
        self.assertEqual(c.target, 0)
        c.tick(replace(s, offset_enabled=True), 0.02)
        self.assertGreater(c.target, 0)
        c.tick(s, 0.02)
        self.assertEqual(c.phase, "fault")

    def test_g40_g41_g42_keep_frame_and_resume_only_at_zero(self):
        for correction in (400, 410, 420, 411, 421):
            with self.subTest(correction=correction):
                c, s = PauseRetract(), snapshot(correction)
                c.start(s, 2, 60)
                for _ in range(400):
                    c.tick(replace(s, offset=c.target, requested=c.target), 0.01)
                self.assertEqual(c.phase, "retracted")
                self.assertEqual(c.target, 2)
                self.assertEqual(c.frame, s.frame)
                c.return_to_path(replace(s, offset=2, requested=2), resume=True)
                for _ in range(400):
                    self.assertFalse(c.tick(replace(s, offset=2, requested=2), 0.01))
                self.assertEqual(c.phase, "returning")  # Request zero is not actual zero.
                self.assertFalse(c.tick(replace(s, offset=0.00011), 0.01))
                self.assertFalse(c.tick(replace(s, settled=False), 0.01))
                self.assertTrue(c.active)
                self.assertTrue(c.tick(s, 0.01))
                self.assertFalse(c.active)
                self.assertFalse(c.tick(s, 0.01))

    def test_resume_accepts_settled_inch_roundoff_within_tolerance(self):
        c, s = PauseRetract(), snapshot()
        c.start(s, 2, 60)
        for _ in range(400):
            c.tick(replace(s, offset=c.target, requested=c.target), 0.01)
        self.assertEqual(c.phase, "retracted")
        c.return_to_path(replace(s, offset=2, requested=2), resume=True)
        for _ in range(400):
            self.assertFalse(c.tick(replace(s, offset=2, requested=2), 0.01))
        residual = replace(
            s, offset=1.0119131067838497e-06,
            requested=6.642306770998641e-07, settled=True,
        )
        self.assertTrue(c.tick(residual, 0.01))
        self.assertFalse(c.active)

    def test_changed_frame_pause_limits_or_readiness_latches_without_lowering(self):
        for change in ({"frame": ("other",)}, {"paused": False}, {"ready": False},
                       {"limited": True}, {"still": False}):
            with self.subTest(change=change):
                c, s = PauseRetract(), snapshot()
                c.start(s, 2, 60)
                c.tick(s, 0.1)
                target = c.target
                self.assertFalse(c.tick(replace(s, **change), 0.1))
                self.assertEqual(c.phase, "fault")
                self.assertEqual(c.target, target)
                self.assertTrue(c.active)
                with self.assertRaises(RetractRefused):
                    c.return_to_path(s)

    def test_refuse_invalid_start_without_moving(self):
        for s in (snapshot(paused=False), snapshot(still=False), snapshot(offset=1),
                  snapshot(requested=1), snapshot(z=-5), snapshot(z=float("nan")),
                  snapshot(settled=False)):
            c = PauseRetract()
            with self.assertRaises(RetractRefused):
                c.start(s, 10, 200)
            self.assertFalse(c.active)
            self.assertEqual(c.target, 0)

    def test_power_off_cancels_without_auto_resume(self):
        c, s = PauseRetract(), snapshot()
        c.start(s, 2, 60)
        c.tick(s, 0.1)
        self.assertFalse(c.tick(replace(s, powered=False), 0.1))
        self.assertFalse(c.active)
        self.assertEqual(c.target, 0)
        self.assertFalse(c.resume)

    def test_validate_quantized_height_before_taking_ownership(self):
        # 0.01 mm on a native inch machine would silently round to zero.
        for height, z in ((0.01 / 25.4, -20), (1.0006, -1.0108)):
            c = PauseRetract()
            with self.assertRaises(RetractRefused):
                c.start(snapshot(z=z), height, 60)
            self.assertFalse(c.active)
            self.assertEqual(c.target, 0)
        c = PauseRetract()
        c.start(snapshot(), 1.2346, 60)
        self.assertEqual(c.height, 1.235)
