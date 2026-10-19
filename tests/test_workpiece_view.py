"""Renderowanie czterech przygotówek bez OpenGL. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import importlib
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
