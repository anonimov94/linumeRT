# SPDX-License-Identifier: GPL-2.0-or-later
"""Sposoby renderowania Classic × Neon: presety, profil, regulator jakości, cieniowanie,
tekstura materiału, warstwy wypiekane i strumieniowane.

Model-Author: Claude
"""

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt5")
from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "screens" / "linumert"))
from linumert.programs.toolpath import demo_toolpath  # noqa: E402
from linumert_neon_render import (  # noqa: E402
    LIGHT,
    PRESETS,
    MemoryStore,
    QualityGovernor,
    RenderSettings,
    SettingsStore,
    Shader,
    bake_material,
    convex_hull,
    preset_name,
    shadow_points,
)
from linumert_neon_view import NeonPathView, PathScene  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _scene():
    scene = PathScene(demo_toolpath())
    scene.timer.stop()
    scene.playing = False
    return scene


def test_settings_validate_roundtrip_and_presets():
    assert len({*PRESETS.values()}) == 3
    for name, preset in PRESETS.items():
        assert RenderSettings.from_json(preset.to_json()) == preset
        assert preset_name(preset) == name
    assert preset_name(replace(PRESETS["wysoki"], fps=15)) == "wlasny"
    assert PRESETS["ekonomiczny"].style == "linie" and not PRESETS["ekonomiczny"].glow
    assert PRESETS["wysoki"].shadows and PRESETS["wysoki"].material
    for bad in (dict(style="raytracing"), dict(fps=60), dict(glow=1)):
        with pytest.raises(ValueError):
            RenderSettings(**bad)
    with pytest.raises(ValueError):
        RenderSettings.from_json(json.dumps({"version": 2}))
    with pytest.raises(ValueError):
        RenderSettings.from_json(json.dumps({"version": 1, "turbo": True}))


def test_qsettings_store_falls_back_on_corrupt_profile(tmp_path, app):
    q = QtCore.QSettings(str(tmp_path / "neon.ini"), QtCore.QSettings.IniFormat)
    store = SettingsStore(q)
    default = PRESETS["zrownowazony"]
    assert store.load("render/detail", default) is default
    store.save("render/detail", PRESETS["wysoki"])
    assert store.load("render/detail", default) == PRESETS["wysoki"]
    q.setValue("render/detail", "{nie json")
    assert store.load("render/detail", default) is default


def test_governor_drops_effects_over_budget_and_recovers_with_hysteresis():
    gov = QualityGovernor()
    s = PRESETS["wysoki"]
    for _ in range(3):
        gov.record(40.0, 10.0, 1 / 30)
    assert gov.level == 3
    eff = gov.effective(s)
    assert not (eff.glow or eff.shadows or eff.antialias) and eff.material
    assert gov.effective(replace(s, adaptive=False)) == replace(s, adaptive=False)
    for _ in range(30):                       # 1 s zapasu: jeszcze bez powrotu
        gov.record(1.0, 10.0, 1 / 30)
    assert gov.level == 3
    for _ in range(40):                       # > 2 s zapasu: jeden efekt wraca
        gov.record(1.0, 10.0, 1 / 30)
    assert gov.level == 2


def test_hull_and_shadow_projection():
    hull = convex_hull([(0, 0), (2, 0), (2, 2), (0, 2), (1, 1)])
    assert len(hull) == 4 and (1.0, 1.0) not in hull
    pts = shadow_points([(0, 0, 10), (0, 0, -5)], 0.0)
    assert len(pts) == 1 and pts[0][2] == pytest.approx(0)
    assert pts[0][:2] == pytest.approx(-LIGHT[:2] * 10 / LIGHT[2])


def test_shaded_box_culls_back_faces(app):
    image = QtGui.QImage(200, 200, QtGui.QImage.Format_ARGB32)
    image.fill(0)
    p = QtGui.QPainter(image)
    calls = []
    original = p.drawPolygon

    class Counting:
        def __getattr__(self, name):
            return getattr(p, name)

        def drawPolygon(self, *args):
            calls.append(1)
            return original(*args)

    view = np.array((-0.4, -0.5, 0.75))
    shader = Shader(Counting(), lambda q: np.asarray(q)[..., :2] * 5 + 100, view,
                    PRESETS["zrownowazony"])
    shader.box((0, 0, 0), (10, 10, 10), "#9aa7b4")
    p.end()
    assert len(calls) == 3                     # z 6 ścian widoczne tylko 3


def test_material_cuts_in_time_slices_and_bakes_depth_layers(app):
    scene = _scene()
    stock = scene.enable_material()
    full = stock.volume()
    scene.seek(1500)
    finished = scene.update_material(budget=0.0005)
    while not finished:
        finished = scene.update_material(budget=0.01)
    assert stock.volume() < full * 0.97
    layers = scene.material_image("#00f0ff")
    zs = [z for z, _ in layers]
    assert zs == sorted(zs) and zs[-1] == pytest.approx(0) and min(zs) <= -5.5
    assert all(img.width() == stock.nx and img.height() == stock.ny for _, img in layers)
    assert scene.material_image("#00f0ff") is layers           # bez zmiany = bez wypiekania
    scene.seek(0)
    scene.update_material(budget=0.5)
    assert stock.volume() == pytest.approx(full)                # przewinięcie wstecz = od nowa
    many = bake_material(np.linspace(0, -30, 200).reshape(10, 20), 0.5, 0, 30, "#00f0ff")
    assert len(many) <= 24


def test_view_menu_changes_and_persists_settings(app):
    scene = _scene()
    store = MemoryStore()
    view = NeonPathView(scene, "machine", store=store)
    view.resize(500, 400)
    view.show()
    app.processEvents()
    view._fill_menu()
    labels = [a.text() for a in view.menu.actions() if a.text()]
    assert {"Ekonomiczny", "Zrównoważony", "Wysoki", "Cienie rzucane", "Cieniowany"} <= set(labels)
    economic = next(a for a in view.menu.actions() if a.text() == "Ekonomiczny")
    economic.trigger()
    assert store.data["render/machine"] == PRESETS["ekonomiczny"]
    assert view._active is None
    shadows = next(a for a in view.menu.actions() if a.text() == "Cienie rzucane")
    shadows.trigger()
    assert view.settings.shadows and preset_name(view.settings) == "wlasny"
    view.repaint()
    assert "Render: Własny" in view.quality_text()
    assert view.menu_button.width() >= 44


def test_layers_are_reused_streamed_and_reset_on_seek_back(app):
    scene = _scene()
    view = NeonPathView(scene, "detail")
    view.set_settings(replace(PRESETS["zrownowazony"], adaptive=False), persist=False)
    view.resize(600, 500)
    view.show()
    app.processEvents()
    scene.seek(400)
    view.repaint()
    first = view._active
    assert first["ready"] and first["done_upto"] == scene.index
    scene.seek(402)
    view.repaint()
    assert view._active is first                    # małe przesunięcie: ta sama pixmapa
    for d in range(404, 900, 6):                    # długi przejazd: następne komplety warstw
        scene.seek(d)
        view.repaint()
    assert view._active is not first
    assert view._active["done_upto"] == scene.index
    scene.seek(10)
    view.repaint()
    assert view._active["done_upto"] == scene.index  # przewinięcie wstecz: akumulacja od nowa
    view.camera.yaw += 0.3
    view.repaint()
    assert view._active["key"][0][0] == pytest.approx(round(view.camera.yaw, 4))


def test_all_presets_render_both_views_with_visible_scene(app):
    scene = _scene()
    scene.seek(1500)
    for name, preset in PRESETS.items():
        for mode in ("detail", "machine"):
            view = NeonPathView(scene, mode)
            view.set_settings(replace(preset, adaptive=False), persist=False)
            view.resize(500, 420)
            view.show()
            app.processEvents()
            if preset.material:
                while not scene.update_material(budget=0.05):
                    pass
            image = view.grab().toImage()
            colors = {image.pixel(x, y) for x in range(0, 500, 7) for y in range(0, 420, 7)}
            assert len(colors) > 40, (name, mode)
            view.hide()
            view.deleteLater()


def test_one_off_bake_hitch_does_not_lower_quality(app):
    scene = _scene()
    view = NeonPathView(scene, "detail")
    view.set_settings(PRESETS["wysoki"], persist=False)
    view.resize(600, 500)
    view.show()
    app.processEvents()
    for _ in range(5):
        view._active = None          # wymuszone pełne wypiekanie w każdej klatce
        view.repaint()
    assert view.governor.level == 0
