# SPDX-License-Identifier: GPL-2.0-or-later
"""Font-independent saved outlines for text engraving. Model-Author: Codex."""
from .base import Field
from .path_geometry import PathTrace, problem

TEXT_FIELDS = (
    Field("text", "text", "Napis", default="linumeRT"),
    Field("font_family", "text", "Czcionka", default="IBM Plex Sans"),
    Field("font_style", "choice", "Styl czcionki", default="regular",
          choices=("regular", "bold", "italic", "bold_italic")),
    Field("text_height", "float", "Wysokość wersalików", "mm", default=10.0,
          minimum=0.1, maximum=1000),
    Field("tracking", "float", "Dodatkowy odstęp liter", "mm", default=0.0,
          minimum=0, maximum=100),
    Field("line_spacing", "float", "Odstęp wierszy × wysokość", default=1.5,
          minimum=1, maximum=5),
    Field("align", "choice", "Wyrównanie do X", default="left",
          choices=("left", "center", "right")),
    Field("tolerance", "float", "Dokładność krzywych", "mm", default=0.02,
          minimum=0.005, maximum=0.2),
)
LAYOUT_KEYS = tuple(f.name for f in TEXT_FIELDS)


class EngraveText(PathTrace):
    name = "engrave_text"
    version = 1
    title = "Napis — kontury czcionki"
    choice_labels = {
        "font_style": {"regular": "Zwykła", "bold": "Pogrubiona", "italic": "Kursywa",
                       "bold_italic": "Pogrubiona kursywa"},
        "align": {"left": "Do lewej", "center": "Wyśrodkowany", "right": "Do prawej"},
    }
    fields = TEXT_FIELDS + PathTrace.fields

    def normalize(self, params, step=0):
        # Literal text is metadata, never a G-code comment. Parentheses/newlines are valid glyphs.
        text = params.get("text", "linumeRT")
        family = params.get("font_family", "IBM Plex Sans")
        values, issues = super().normalize({**params, "text": "", "font_family": ""}, step)
        if (not isinstance(family, str) or not family.strip() or len(family) > 128
                or any(ord(c) < 32 for c in family)):
            issues.append(problem("font_family", "nazwa czcionki, do 128 znaków", step))
        else:
            values["font_family"] = family
        if not isinstance(text, str) or not text.strip() or len(text) > 128 or any(
                ord(c) < 32 and c != "\n" for c in text):
            issues.append(problem("text", "od 1 do 128 znaków, bez znaków sterujących", step))
        else:
            values["text"] = text
        return values, issues


def register(registry=None):
    from .registry import DEFAULT_REGISTRY

    (registry or DEFAULT_REGISTRY).register(EngraveText)
