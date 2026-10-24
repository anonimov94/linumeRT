# SPDX-License-Identifier: GPL-2.0-or-later
"""Fonty ekranu z tokens.yaml (sesja 027): IBM Plex Sans (interfejs), JetBrains Mono (liczby).

Model-Author: Claude · 2026-10-24. Pliki TTF i licencje OFL-1.1 w `screens/linumert/fonts/`
(pochodzenie i sumy SHA-256: docs/PROVENANCE.md). Rejestracja w aplikacji, bez instalacji
w systemie; brak pliku = wpis na liście `missing`, ekran używa fontów zastępczych z QSS.
"""

from pathlib import Path

from PyQt5 import QtGui

FONT_DIR = Path(__file__).with_name("fonts")
FAMILIES = ("IBM Plex Sans", "JetBrains Mono")
_registered = {}


def register():
    """Rejestruje TTF z `fonts/` (raz na proces). Zwraca (rodziny, brakujące_pliki)."""
    missing = []
    for path in sorted(FONT_DIR.glob("*.ttf")):
        if path.name in _registered:
            continue
        font_id = QtGui.QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            missing.append(path.name)
            continue
        _registered[path.name] = QtGui.QFontDatabase.applicationFontFamilies(font_id)
    families = sorted({f for fams in _registered.values() for f in fams})
    return families, missing
