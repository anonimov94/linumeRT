# SPDX-License-Identifier: GPL-2.0-or-later
"""Prototype package and switch boundary regressions. Model-Author: Codex."""

import json
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screens" / "linumert"))
import linumert_skin_runtime as runtime  # noqa: E402


def manifest():
    return {"skin": "classic-digital", "version": "0.1.0", "api": 1,
            "views": sorted(runtime.VIEW_IDS),
            "global_controls": sorted(runtime.GLOBAL_IDS),
            "resolutions": [[1280, 800], [1920, 1080]]}


class SkinRuntimeTests(unittest.TestCase):
    def test_metadata_roundtrip_and_detachment(self):
        source = manifest()
        parsed = runtime.SkinManifest.from_json(json.dumps(source))
        source["views"].clear()
        self.assertEqual(set(parsed.views), runtime.VIEW_IDS)
        self.assertEqual(parsed.resolutions, ((1280, 800), (1920, 1080)))
        with self.assertRaises(FrozenInstanceError):
            parsed.api = 2

    def test_reject_incomplete_or_executable_manifest(self):
        invalid = (("api", True), ("api", 2), ("skin", "../other"),
                   ("version", "1.0"), ("version", "1.0.beta"),
                   ("views", ["dro"]), ("global_controls", ["stop"]),
                   ("resolutions", [[1280, True]]),
                   ("resolutions", [[1280, 800]]),
                   ("entrypoint", "os.system"))
        for key, value in invalid:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                runtime.SkinManifest.from_json(json.dumps({**manifest(), key: value}))

    def test_each_motion_precondition_must_be_explicit(self):
        ready = runtime.SwitchSnapshot(10., True, True, True, True, False, False)
        self.assertTrue(runtime.switch_gate(ready, 10.1).allowed)
        for field, value in (("connected", False), ("stopped", False),
                             ("interpreter_idle", False), ("queue_empty", False),
                             ("homing", True), ("command_pending", True),
                             ("stopped", None), ("homing", 0)):
            with self.subTest(field=field, value=value):
                changed = replace(ready, **{field: value})
                self.assertFalse(runtime.switch_gate(changed, 10.1).allowed)
        self.assertFalse(runtime.switch_gate(None, 10.1).allowed)
        self.assertEqual(ready.sampled_at, 10.)

    def test_stale_future_or_invalid_clock_never_allows_switch(self):
        ready = runtime.SwitchSnapshot(10., True, True, True, True, False, False)
        self.assertTrue(runtime.switch_gate(ready, 10.5).allowed)
        for now in (10.50001, 9.9, float("nan"), float("inf"), -1, True):
            with self.subTest(now=now):
                self.assertFalse(runtime.switch_gate(ready, now).allowed)
        for timestamp in (float("nan"), float("inf"), -1, None):
            self.assertFalse(runtime.switch_gate(replace(ready, sampled_at=timestamp), 10.).allowed)


if __name__ == "__main__":
    unittest.main()
