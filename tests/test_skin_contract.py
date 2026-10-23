# SPDX-License-Identifier: GPL-2.0-or-later
"""Presentation contract regressions, runnable without Qt/LinuxCNC or pytest.

Model-Author: Codex.
"""

import itertools
import json
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screens" / "linumert"))
import linumert_skin_contract as skin  # noqa: E402
import linumert_skin_strings as strings  # noqa: E402


def contrast(first, second):
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
                  for c in channels]
        return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(first), luminance(second)))
    return (b + .05) / (a + .05)


class SkinContractTests(unittest.TestCase):
    def test_all_32_selections_roundtrip_independently(self):
        for family, theme, language in itertools.product(
                skin.SKIN_IDS, skin.THEME_IDS, skin.LANGUAGE_IDS):
            with self.subTest(skin=family, theme=theme, language=language):
                original = skin.PresentationPreferences(family, theme, language)
                restored = skin.PresentationPreferences.from_json(original.to_json())
                self.assertEqual(restored, original)
                self.assertIs(skin.palette_for(original), skin.PALETTES[theme])
                changed = replace(original, language="pl" if language == "en" else "en")
                self.assertEqual((changed.skin, changed.theme), (family, theme))

    def test_invalid_profiles_fail_explicitly(self):
        valid = json.loads(skin.PresentationPreferences().to_json())
        for field, value in (("skin", "missing"), ("theme", "missing"),
                             ("language", "de"), ("version", 2), ("version", True),
                             ("skin", []), ("language", None)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    skin.PresentationPreferences.from_json(json.dumps({**valid, field: value}))
        for data in ([], None, {}, {**valid, "command": "M3"}, {"version": 1}):
            with self.assertRaises(ValueError):
                skin.PresentationPreferences.from_json(json.dumps(data))

    def test_profiles_and_palettes_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            skin.PresentationPreferences().skin = "cyberdeck"
        with self.assertRaises(TypeError):
            skin.PALETTES["other"] = skin.PALETTES["ion-blue"]
        with self.assertRaises(FrozenInstanceError):
            skin.PALETTES["ion-blue"].accent = "#000000"

    def test_text_and_status_contrast_on_panel(self):
        for name, palette in skin.PALETTES.items():
            for role in ("text", "muted", "accent", "warning", "error", "success"):
                with self.subTest(theme=name, role=role):
                    self.assertGreaterEqual(contrast(getattr(palette, role), palette.panel), 4.5)

    def test_languages_have_complete_shared_keys(self):
        self.assertEqual(set(strings.STRINGS), set(skin.LANGUAGE_IDS))
        self.assertEqual(set(strings.STRINGS["en"]), set(strings.STRINGS["pl"]))
        for family, theme, language in itertools.product(
                skin.SKIN_IDS, skin.THEME_IDS, skin.LANGUAGE_IDS):
            preferences = skin.PresentationPreferences(family, theme, language)
            for key, expected in strings.STRINGS[language].items():
                self.assertTrue(expected.strip())
                self.assertEqual(strings.text(key, preferences), expected)
            with self.assertRaises(KeyError):
                strings.text("nonexistent", preferences)

    def test_different_statuses_keep_different_labels(self):
        for language in skin.LANGUAGE_IDS:
            preferences = skin.PresentationPreferences(language=language)
            labels = [strings.text(key, preferences) for key in
                      ("estop_active", "estop_clear", "status_unknown",
                       "machine_on", "machine_off", "homed", "not_homed")]
            self.assertEqual(len(labels), len(set(labels)))
            for code in ("E-4200", "W-1000"):
                with self.assertRaises(KeyError):
                    strings.text(code, preferences)


if __name__ == "__main__":
    unittest.main()
