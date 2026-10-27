# SPDX-License-Identifier: GPL-2.0-or-later
"""Convert installed fonts to a persisted vector snapshot. Model-Author: Codex."""
import json

from PyQt5 import QtGui

from linumert.generators.path_geometry import MAX_POINTS, decode_paths


def text_paths(values):
    text = values["text"]
    if not isinstance(text, str) or len(text) > 128 or not text.strip():
        raise ValueError("Wpisz od 1 do 128 znaków.")
    family = values["font_family"]
    if family not in QtGui.QFontDatabase().families():
        raise ValueError("Wybrana czcionka nie jest zainstalowana. Wybierz czcionkę z listy.")
    font = QtGui.QFont(family)
    font.setPixelSize(1000)
    font.setBold(values["font_style"] in ("bold", "bold_italic"))
    font.setItalic(values["font_style"] in ("italic", "bold_italic"))
    cap = QtGui.QFontMetricsF(font).capHeight()
    if cap <= 0:
        raise ValueError("Czcionka nie ma poprawnej wysokości wersalików.")
    factor = values["text_height"] / cap
    font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, values["tracking"] / factor)
    metrics = QtGui.QFontMetricsF(font)
    paths, total = [], 0
    # Flatten after scaling to tolerance-sized pixels, avoiding font-size-dependent accuracy.
    precision = 1 / values["tolerance"]
    transform = QtGui.QTransform.fromScale(factor * precision, factor * precision)
    for row, line in enumerate(text.split("\n")):
        if any(not metrics.inFontUcs4(ord(char)) for char in line if not char.isspace()):
            raise ValueError("Czcionka nie zawiera wszystkich znaków napisu.")
        width = metrics.horizontalAdvance(line) * factor
        dx = {"left": 0, "center": -width / 2, "right": -width}[values["align"]]
        path = QtGui.QPainterPath()
        path.addText(0, 0, font, line)
        for polygon in path.toSubpathPolygons(transform):
            points = [(p.x() / precision + dx,
                       -p.y() / precision - row * values["text_height"] * values["line_spacing"])
                      for p in polygon]
            if len(points) < 3:
                continue
            if points[-1] != points[0]:
                points.append(points[0])
            total += len(points)
            if total > MAX_POINTS:
                raise ValueError("Napis ma zbyt wiele punktów. Zwiększ tolerancję lub skróć napis.")
            paths.append(points)
    encoded = json.dumps(paths, separators=(",", ":"), allow_nan=False)
    decode_paths(encoded)
    return encoded
