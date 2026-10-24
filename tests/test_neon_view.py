# SPDX-License-Identifier: GPL-2.0-or-later
"""Renderer Classic × Neon: scena, kolory stref, następny punkt, montaż w Classic.

Model-Author: Claude
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt5")
from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "screens" / "linumert"))
from linumert.programs.toolpath import demo_toolpath  # noqa: E402
from linumert_neon_view import (  # noqa: E402
    NEON,
    NeonDetailPanel,
    NeonPathView,
    NeonTimeline,
    PathScene,
)


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _count(image, hex_value, tol=40):
    target = QtGui.QColor(hex_value)
    hits = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            c = image.pixelColor(x, y)
            if (abs(c.red() - target.red()) + abs(c.green() - target.green())
                    + abs(c.blue() - target.blue())) < tol:
                hits += 1
    return hits


def test_path_roles_match_design_tokens():
    tokens = yaml.safe_load((ROOT / "docs/design/tokens.yaml").read_text(encoding="utf-8"))
    roles = tokens["motywy"]["sciezka"]
    assert {roles["start"], roles["koniec"], roles["nastepny"], roles["g0"],
            roles["do_wykonania"], roles["os_x"]} == {
        NEON["lime"], NEON["magenta"], NEON["yellow"], NEON["orange"],
        NEON["violet"], NEON["red"]}


def test_scene_playback_step_seek_and_end(app):
    scene = PathScene(demo_toolpath())
    scene.timer.stop()
    n = len(scene.toolpath)
    assert scene.playing and scene.zone(0) == "start" and scene.zone(n - 1) == "end"
    scene.advance(0.5)
    assert scene.toolpath.travelled(scene.index, scene.s) > 0
    scene.step(1)
    assert not scene.playing and scene.s == 0
    before = scene.index
    scene.step(-1)
    assert scene.index == before - 1
    scene.seek(scene.toolpath.length / 2)
    assert 0 < scene.index < n
    assert scene.dtg() == pytest.approx(scene.toolpath.moves[scene.index].length - scene.s)
    scene.set_zone_count(99)
    assert scene.zone_count == 15
    scene.playing = True
    scene.advance(10_000)
    assert scene.done and not scene.playing and scene.next_move() is None


def test_live_scene_follows_motion_line_without_local_playback(app):
    tp = demo_toolpath()
    scene = PathScene(tp, live=True)
    scene.timer.stop()
    assert not scene.playing
    target = tp.moves[20]
    middle = target.at(target.length / 2)
    scene.follow(target.line, middle)
    assert scene.index == 20 and scene.dtg() == pytest.approx(target.length / 2, abs=1e-6)
    for action in (scene.toggle, scene.restart, lambda: scene.step(1), lambda: scene.seek(0)):
        action()
        assert scene.index == 20       # podgląd na żywo nie przewija ścieżki


def test_views_render_zones_next_point_and_timeline(app):
    scene = PathScene(demo_toolpath())
    scene.timer.stop()
    scene.playing = False
    scene.seek(30)                     # w strefie START
    detail = NeonDetailPanel(scene)
    machine = NeonPathView(scene, "machine")
    timeline = NeonTimeline(scene)
    for widget, size in ((detail, (800, 600)), (machine, (500, 600)), (timeline, (600, 32))):
        widget.resize(*size)
        widget.show()
    app.processEvents()
    shot = detail.view.grab().toImage()
    assert _count(shot, NEON["lime"]) > 20
    assert _count(shot, NEON["yellow"]) > 10
    assert "NASTĘPNY P" in detail.info.text() and "DTG" in detail.info.text()
    scene.seek(scene.toolpath.length - 5)   # w strefie KONIEC
    app.processEvents()
    assert _count(machine.grab().toImage(), NEON["magenta"]) > 5
    assert _count(timeline.grab().toImage(), NEON["magenta"]) > 5
    timeline.mousePressEvent(QtGui.QMouseEvent(
        QtCore.QEvent.MouseButtonPress, QtCore.QPointF(5, 10), QtCore.Qt.LeftButton,
        QtCore.Qt.LeftButton, QtCore.Qt.NoModifier))
    assert scene.index < 3
    with pytest.raises(ValueError):
        NeonPathView(scene, "top")


def test_classic_skin_uses_neon_views_with_shared_scene(app):
    from linumert_skin_contract import PresentationPreferences, palette_for
    from linumert_skin_screens import SCREENS

    prefs = PresentationPreferences("classic-digital", "neon-punk", "pl")
    screen = SCREENS["classic-digital"](prefs, palette_for(prefs),
                                        lambda role, palette: QtWidgets.QLabel(role))
    assert isinstance(screen.viewports["toolpath"], NeonDetailPanel)
    assert isinstance(screen.viewports["machine"], NeonPathView)
    assert screen.viewports["toolpath"].scene is screen.viewports["machine"].scene
    assert screen.path_scene.parent() is screen
    assert isinstance(screen.viewports["workpiece"], QtWidgets.QLabel)
    layout_only = SCREENS["classic-digital"](prefs, palette_for(prefs))
    assert not layout_only.viewports and layout_only.path_scene is None
