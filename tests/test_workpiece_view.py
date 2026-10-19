"""Renderowanie czterech przygotówek bez OpenGL. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("shape", ["box", "cylinder", "tube", "casting"])
def test_software_scene_renders_machine_and_workpiece(monkeypatch, shape):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PyQt5.QtWidgets")
    root = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(root / "screens/linumert"))
    module = importlib.import_module("linumert_workpiece_view")
    app = qt.QApplication.instance() or qt.QApplication([])
    colors = yaml.safe_load((root / "docs/design/tokens.yaml").read_text())["kolory"]
    view = module.WorkpieceView(colors)
    view.set_workpiece(module.Workpiece(shape=shape))
    view.resize(640, 480)
    view.show()
    app.processEvents()
    image = view.grab().toImage()
    background = image.pixelColor(1, 1)
    colored = sum(image.pixelColor(x, y) != background for x in range(0, 640, 8)
                  for y in range(0, 480, 8))
    assert colored > 100
    view.fit(True)
    assert view.focus_part
    view.close()


def test_profile_editor_updates_contour_and_rejects_bad_input(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PyQt5.QtWidgets")
    root = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(root / "screens/linumert"))
    module = importlib.import_module("linumert_profile_editor")
    app = qt.QApplication.instance() or qt.QApplication([])
    colors = yaml.safe_load((root / "docs/design/tokens.yaml").read_text())["kolory"]
    editor = module.ProfileEditor(colors)
    editor.set_points(((0, 20), (10, 30)))
    editor.table.item(1, 1).setText("35,5")
    assert editor.points() == ((0, 20), (10, 35.5))
    editor.add_point()
    assert editor.points()[-1] == (20, 35.5)
    editor.remove_point()
    assert len(editor.points()) == 2
    editor.table.item(0, 0).setText("nan")
    with pytest.raises(ValueError):
        editor.points()
    editor.add_point()  # błędna komórka nie może wywołać wyjątku w slocie Qt
    assert editor.table.rowCount() == 2
    editor.close()
    app.processEvents()


def test_standalone_preview_has_no_linuxcnc_connection(tmp_path):
    pytest.importorskip("PyQt5.QtWidgets")
    root = Path(__file__).parents[1]
    screenshot = tmp_path / "offline.png"
    source = tmp_path / "machine.ini"
    source.write_text("oryginalna konfiguracja")
    run = subprocess.run([sys.executable, str(root / "tools/dev/preview-zero.py"),
                          "--snapshot", str(screenshot)], capture_output=True, text=True,
                         env={**os.environ, "QT_QPA_PLATFORM": "offscreen",
                              "INI_FILE_NAME": str(source)}, timeout=20)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PODGLĄD OFFLINE GOTOWY" in run.stdout
    assert screenshot.read_bytes().startswith(b"\x89PNG")
    assert source.read_text() == "oryginalna konfiguracja"
