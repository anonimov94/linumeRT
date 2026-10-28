"""Projection, subpixel packing and depth-layer contracts of the terminal renderer.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from terminal3d import Camera, Raster, Scene  # noqa: E402


@pytest.mark.parametrize("x,y,mask", [(0, 0, 1), (0, 1, 2), (0, 2, 4), (0, 3, 64),
                                      (1, 0, 8), (1, 1, 16), (1, 2, 32), (1, 3, 128)])
def test_braille_subpixels_follow_unicode_dot_numbering(x, y, mask):
    raster = Raster(1, 1)
    raster.dot(x, y, 0, 3)
    assert raster.text() == [chr(0x2800 + mask)]


def test_layers_combine_dots_but_nearer_fragment_owns_color():
    raster = Raster(1, 1)
    for y in range(4):
        for x in range(2):
            raster.dot(x, y, 5, 1)
    raster.dot(0, 0, 0, 4)
    raster.dot(0, 0, 10, 2)
    assert raster.text() == ["⣿"]
    assert "38;5;220m" in raster.text(color=True)[0]
    assert raster.pixels[0, 0] == (0, 4)


@pytest.mark.parametrize("mode,char", [("block", "█"), ("ascii", "*")])
def test_non_braille_rasters_and_clipping(mode, char):
    raster = Raster(1, 1, mode)
    raster.line((0, 0, 0), (0, raster.height - 1, 0), 3)
    raster.dot(-1, 0, 0, 3)
    raster.dot(raster.width, 0, 0, 3)
    assert raster.text() == [char]


def scene():
    # A true XYZ path with changes along every axis, not a pre-drawn screen pattern.
    points = [(0, 0, 0), (8, 0, 0), (8, 6, 0), (8, 6, -4), (0, 0, 0)]
    telemetry = {"t": list(range(len(points))), "drives": {}}
    for i, letter in enumerate("XYZ"):
        values = [p[i] for p in points]
        telemetry["drives"][letter] = {"act": values, "cmd": values}
    return Scene(SimpleNamespace(telemetry=telemetry,
                                 axis_drives={k: [k] for k in "XYZ"}))


def test_z_motion_and_camera_rotation_change_actual_geometry():
    model = scene()
    start = model.panel(1, 80, 24, Camera(), "braille")
    down = model.panel(3, 80, 24, Camera(), "braille")
    rotated = model.panel(3, 80, 24, Camera(yaw=110), "braille")
    assert start != down and down != rotated
    assert "@" in "".join(down)


@pytest.mark.parametrize("width,height", [(79, 10), (120, 26), (180, 48)])
def test_composed_viewports_fit_exact_terminal_dimensions(width, height):
    lines = scene().render(3, width, height, Camera(), color=True)
    plain = [re.sub(r"\033\[[0-9;]*m", "", line) for line in lines]
    assert len(plain) == height and all(len(line) == width for line in plain)
    if width >= 110 and height >= 18:
        assert all(view in "\n".join(plain) for view in ("3D |", "XY |", "XZ |", "YZ |"))


def test_camera_idle_keeps_orbit_and_controls_have_bounds():
    camera = Camera()
    camera.key("")
    assert camera.orbit
    camera.key("a")
    assert not camera.orbit and camera.yaw == 27
    for _ in range(100):
        camera.key("w")
        camera.key("+")
    assert camera.pitch == 80 and camera.zoom == 4
    camera.key("r")
    assert camera == Camera()
