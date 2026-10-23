# SPDX-License-Identifier: GPL-2.0-or-later
"""Experimental presentation preferences; no Qt, HAL or command access.

Model-Author: Codex. Family IDs describe planned layouts, not installed plugins.
"""

import json
from dataclasses import dataclass
from types import MappingProxyType


SKIN_IDS = ("classic-digital", "industrial-pro", "cyberdeck", "organic-vector")
THEME_IDS = ("classic-turquoise", "graphite-gray", "reactor-green", "ion-blue")
LANGUAGE_IDS = ("en", "pl")


@dataclass(frozen=True)
class PresentationPreferences:
    """Three independent axes. Construction rejects unsupported selections."""

    skin: str = "classic-digital"
    theme: str = "classic-turquoise"
    language: str = "en"

    def __post_init__(self):
        for name, allowed in (("skin", SKIN_IDS), ("theme", THEME_IDS),
                              ("language", LANGUAGE_IDS)):
            value = getattr(self, name)
            if not isinstance(value, str) or value not in allowed:
                raise ValueError(f"Unsupported {name}: {value!r}")

    def to_json(self) -> str:
        return json.dumps({"version": 1, "skin": self.skin, "theme": self.theme,
                           "language": self.language}, sort_keys=True)

    @classmethod
    def from_json(cls, text: str):
        data = json.loads(text)
        fields = {"version", "skin", "theme", "language"}
        if not isinstance(data, dict) or set(data) != fields:
            raise ValueError("Expected version, skin, theme and language")
        if type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("Unsupported presentation preferences version")
        return cls(data["skin"], data["theme"], data["language"])


@dataclass(frozen=True)
class Palette:
    """Color roles only; layouts, geometry and fonts belong to the skin."""

    background: str
    panel: str
    raised: str
    text: str
    muted: str
    accent: str
    warning: str = "#fbbf24"
    error: str = "#f87171"
    success: str = "#4ade80"


# Existing turquoise colors come from docs/design/tokens.yaml. New palettes are
# prototype values; warning/error/success retain their meaning in every theme.
# Graphite uses lighter error text to keep 4.5:1 contrast on its #404040 panel.
PALETTES = MappingProxyType({
    "classic-turquoise": Palette("#0a0c0f", "#12171d", "#182029", "#e8eef4",
                                 "#9aa7b4", "#2dd4bf"),
    "graphite-gray": Palette("#202020", "#404040", "#606060", "#ffffff",
                              "#e0e0e0", "#ffffff", error="#ffa0a0"),
    "reactor-green": Palette("#0c110e", "#162019", "#213026", "#edf7ee",
                              "#a4b9a8", "#8bea76"),
    "ion-blue": Palette("#0c111a", "#151f2e", "#202e42", "#edf3ff",
                         "#a7b7d1", "#70b7ff"),
})


def palette_for(preferences: PresentationPreferences) -> Palette:
    """Resolving a palette cannot switch a skin, language or machine mode."""
    return PALETTES[preferences.theme]
