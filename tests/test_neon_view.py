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
    assert screen.path_scene.parent() is screen      # bez hosta: właścicielem jest ekran
    assert isinstance(screen.viewports["workpiece"], QtWidgets.QLabel)
    layout_only = SCREENS["classic-digital"](prefs, palette_for(prefs))
    assert not layout_only.viewports and layout_only.path_scene is None


def test_loader_json_roundtrip_and_errors():
    from linumert_neon_loader import toolpath_from_json, toolpath_to_json

    tp = demo_toolpath()
    back = toolpath_from_json(toolpath_to_json(tp).encode(), tp.source)
    assert len(back) == len(tp) and back.source == tp.source
    assert [m.line for m in back.moves] == [m.line for m in tp.moves]
    assert back.length == pytest.approx(tp.length, rel=1e-6)
    for bad in (b'{"error": "linia 7: zly kod"}', b'[]', b'{"version": 2, "moves": []}',
                b'{"version": 1, "moves": [[1, "tak", 0, []]]}'):
        with pytest.raises(ValueError):
            toolpath_from_json(bad)


def test_loader_process_reports_missing_interpreter_honestly(app):
    import importlib.util

    if importlib.util.find_spec("gcode") is not None:
        pytest.skip("środowisko z LinuxCNC: wariant bez interpretera nie dotyczy")
    from linumert_skin_monitor import ProgramLoader

    loader = ProgramLoader(timeout_s=20)
    seen = []
    loader.loaded.connect(lambda tp, note: seen.append((tp, note)))
    loader.start(str(ROOT / "config/sim/nc_files/linumert_neon_demo.ngc"))
    import time
    end = time.monotonic() + 20
    while not seen and time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)
    assert seen and seen[0][0] is None and "gcode" in seen[0][1]


def test_monitor_follows_live_program_and_survives_skin_switch(app):
    import json
    import time
    from dataclasses import replace
    from types import SimpleNamespace

    from linumert_skin_contract import PresentationPreferences
    from linumert_skin_monitor import SkinMonitor
    from linumert_skin_status import decode_sample, read_status

    window = SkinMonitor(PresentationPreferences("classic-digital", "neon-punk", "pl"))
    window.reader.timer.stop()
    window.loader.start = lambda path: None          # bez procesu: ścieżka podana niżej
    window.show()
    app.processEvents()
    try:
        assert "toolpath" not in window.viewports      # bez programu: tylko opis stanu
        api = SimpleNamespace(MODE_MANUAL=1, MODE_MDI=3, MODE_AUTO=2, STATE_ESTOP=1,
                              STATE_ESTOP_RESET=2, STATE_OFF=3, STATE_ON=4, INTERP_IDLE=1,
                              INTERP_READING=2, INTERP_PAUSED=3, INTERP_WAITING=4)
        tp = demo_toolpath()
        target = tp.moves[30]
        here = target.at(target.length / 3)
        status = SimpleNamespace(
            poll=lambda: None, linear_units=1.0, angular_units=1.0, axis_mask=7,
            actual_position=tuple(float(v) for v in here + (100, 100, -150)) + (0,) * 6,
            task_mode=2,
            task_state=4, interp_state=2, estop=0, enabled=True, file="/nc/neon.ngc",
            motion_line=target.line, g5x_offset=(100, 100, -150) + (0,) * 6,
            g92_offset=(0,) * 9, tool_offset=(0,) * 9, rotation_xy=0.0,
            distance_to_go=1.25, dtg=(1, 0, 0) + (0,) * 6)
        sample = decode_sample(json.dumps(read_status(status, api)).encode(), time.monotonic())
        window.present(sample, "sampled")
        assert window.program_file == "/nc/neon.ngc"
        window.program_loaded(tp, "neon.ngc · test")
        window.present(sample, "sampled")
        scene = window.shared["path_scene"]
        assert scene.live and scene.index == 30 and scene.dtg() == pytest.approx(1.25)
        assert isinstance(window.viewports["toolpath"], NeonDetailPanel)
        window.select("skin", "industrial-pro")
        window.select("skin", "classic-digital")
        window.select("theme", "classic-turquoise")
        assert window.shared["path_scene"] is scene    # zmiana skórki/motywu: ta sama scena
        assert window.viewports["toolpath"].scene is scene
        # A new program must remove the previous geometry before asynchronous loading.
        sample = replace(sample, file="/nc/next.ngc", acquired_at=time.monotonic())
        window.present(sample, "sampled")
        assert "path_scene" not in window.shared
        assert "toolpath" not in window.viewports
        window.program_loaded(tp, "next.ngc · test")
        window.present(None, "read-failed")
        assert window.program_file is None
        assert "path_scene" not in window.shared
        assert "toolpath" not in window.viewports
        requests = []
        window.loader.start = requests.append
        window.present(replace(sample, acquired_at=time.monotonic()), "recovered")
        assert requests == ["/nc/next.ngc"]
        window.program_loaded(tp, "next.ngc · test")
        status.file = ""
        window.present(decode_sample(json.dumps(read_status(status, api)).encode(),
                                     time.monotonic()), "sampled")
        assert "path_scene" not in window.shared and "toolpath" not in window.viewports
    finally:
        window.close()
        app.processEvents()


def test_preview_keeps_demo_scene_across_skin_and_theme(app):
    from linumert_skin_contract import PresentationPreferences
    from linumert_skin_preview import SkinPreview

    window = SkinPreview(PresentationPreferences("classic-digital", "neon-punk", "pl"),
                         viewport_factory=lambda role, palette: QtWidgets.QLabel(role))
    scene = window.shared["path_scene"]
    scene.timer.stop()
    scene.seek(500)
    for field, value in (("theme", "ion-blue"), ("skin", "cyberdeck"), ("language", "en"),
                         ("skin", "classic-digital")):
        window.select(field, value)
    assert window.shared["path_scene"] is scene and scene.index > 0
    assert window.viewports["machine"].scene is scene
    window.close()


def test_cyberdeck_shares_live_scene_with_classic_and_keeps_both_views(app, tmp_path):
    import time

    from linumert_skin_contract import PresentationPreferences
    from linumert_skin_cyberdeck import SceneOverlay
    from linumert_skin_monitor import SkinMonitor
    from linumert_skin_status import MachineSample

    window = SkinMonitor(PresentationPreferences("classic-digital", "neon-punk", "pl"))
    window.reader.stop()
    window.loader.start = lambda path: None
    window.sample = MachineSample(time.monotonic(), (20.0, 10.0, 0.0) + (0.0,) * 6,
                                  "MODE_AUTO", "STATE_ON", "INTERP_READING", False, True,
                                  file="test.ngc", motion_line=10)
    window.program_file = "test.ngc"
    try:
        window.program_loaded(demo_toolpath(), "program testowy")
        scene = window.shared["path_scene"]
        scene.timer.stop()
        scene.follow(10, (20, 10, 0))
        index = scene.index
        window.select("skin", "cyberdeck")
        window.resize(1280, 768)
        window.show()
        app.processEvents()
        assert window.shared["path_scene"] is scene and scene.index == index
        assert {"toolpath", "machine"} <= window.viewports.keys()
        assert len(window.workspace.findChildren(SceneOverlay)) == 2
        for view in window.viewports.values():
            assert view.isVisible()
        assert window.cards["toolpath"].geometry().right() < (
            window.cards["machine"].geometry().left())
        assert window.grab().save(str(tmp_path / "cyberdeck-live.png"))
        window.select("theme", "classic-turquoise")
        assert window.shared["path_scene"] is scene
        assert len(window.workspace.findChildren(SceneOverlay)) == 2
    finally:
        window.close()
        app.processEvents()
