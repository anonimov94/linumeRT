#!/usr/bin/env python3
"""Strażnik: w beta nie ma Qt, OpenGL, ekranu ani panelu web.

SPDX-License-Identifier: GPL-2.0-or-later

Projekt beta jest aplikacją **bez GUI**. Ten skrypt pilnuje, żeby nic graficznego nie
wróciło przez przypadek (zależność, import, plik ``.ui``/``.qss``, panel web Plant):

1. importy i użycia zabronionych bibliotek graficznych w kodzie Pythona,
2. pliki ekranu (``*.ui``, ``*.qss``, ``*.qrc``, ``render_view.py``) i zabronione ścieżki,
3. zabronione zależności w ``pyproject.toml``.

Wykrywanie jest celowo wąskie (import/instancjacja), więc lista nazw w dokumentacji albo
w teście tego strażnika nie jest naruszeniem. Linia oznaczona ``# gui-guard: allow``
jest pomijana jawnie — tylko dla udokumentowanych wyjątków.

Wyjście: lista naruszeń i kod 1 — do wpięcia w ``make lint`` i CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("src", "tests", "tools")
SELF = Path(__file__).resolve()

GRAPHIC_MODULES = (
    "PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy", "qtvcp", "qtawesome",
    "OpenGL", "pyqtgraph", "vispy", "pygame", "tkinter", "kivy",
)
# Tylko rzeczywiste użycie: import, __import__ albo konstrukcja/odwołanie do typu Qt/GL.
IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+)|.*__import__\(\s*[\"']([\w.]+)[\"'])")
USAGE_RE = re.compile(
    r"\b(?:QApplication|QMainWindow|QWidget|QtWidgets|QtCore|QtGui|QOpenGL\w*|"
    r"GLWidget|glBegin|glEnd|glVertex\w*)\b")
FORBIDDEN_FILES = ("*.ui", "*.qss", "*.qrc", "render_view.py")
FORBIDDEN_PATHS = ("linumert_plant/panel/app.py", "linumert_webhmi", "screens/linumert")
FORBIDDEN_DEPS = ("pyqt5", "pyqt6", "pyside2", "pyside6", "qtpy", "pyqtgraph",
                  "pyopengl", "linumert-webhmi")
ALLOW_MARKER = "gui-guard: allow"


def _imported_names(line: str) -> list[str]:
    match = IMPORT_RE.match(line)
    if not match:
        return []
    groups = [g for g in match.groups() if g]
    names: list[str] = []
    for group in groups:
        names.extend(part.strip().split(".")[0] for part in group.split(",") if part.strip())
    return names


def violations() -> list[str]:
    found: list[str] = []

    for directory in SCAN_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts or path.resolve() == SELF:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            relative = path.relative_to(ROOT)
            for number, line in enumerate(text.splitlines(), 1):
                if ALLOW_MARKER in line:
                    continue
                for name in _imported_names(line):
                    if name in GRAPHIC_MODULES:
                        found.append(f"{relative}:{number}: import {name}")
                if USAGE_RE.search(line):
                    found.append(f"{relative}:{number}: użycie API graficznego")

    for pattern in FORBIDDEN_FILES:
        for path in sorted(ROOT.rglob(pattern)):
            if "__pycache__" in path.parts or ".git" in path.parts:
                continue
            found.append(f"{path.relative_to(ROOT)}: plik ekranu ({pattern})")

    for fragment in FORBIDDEN_PATHS:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and fragment in path.relative_to(ROOT).as_posix():
                found.append(f"{path.relative_to(ROOT)}: zabroniona ścieżka {fragment}")

    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        for number, line in enumerate(pyproject.read_text(encoding="utf-8").splitlines(), 1):
            lowered = line.lower()
            for dep in FORBIDDEN_DEPS:
                if f'"{dep}' in lowered or f"'{dep}" in lowered:
                    found.append(f"pyproject.toml:{number}: zależność {dep}")
    return found


def main() -> int:
    problems = violations()
    if problems:
        print("beta musi pozostać bez GUI — znalezione naruszenia:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print("OK: brak Qt, OpenGL, ekranu i panelu web w beta "
          f"(przeszukane: {', '.join(SCAN_DIRS)}, pyproject.toml)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
