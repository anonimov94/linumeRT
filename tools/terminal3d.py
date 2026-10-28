"""Layered, depth-buffered terminal rasterizer; no graphics dependencies.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

DOTS = ((1, 8), (2, 16), (4, 32), (64, 128))
COLORS = {1: 240, 2: 60, 3: 51, 4: 220, 5: 203, 6: 83, 7: 75}


class Raster:
    """Per-dot depth and color layers, packed into terminal character cells."""

    def __init__(self, columns: int, rows: int, mode: str = "braille"):
        self.columns, self.rows, self.mode = columns, rows, mode
        self.sx, self.sy = {"braille": (2, 4), "block": (1, 2), "ascii": (1, 1)}[mode]
        self.width, self.height = columns * self.sx, rows * self.sy
        self.pixels: dict[tuple[int, int], tuple[float, int]] = {}
        self.labels: dict[tuple[int, int], str] = {}

    def dot(self, x: float, y: float, z: float, color: int) -> None:
        x, y = round(x), round(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            old = self.pixels.get((x, y))
            if old is None or z < old[0] - 1e-6 or (abs(z - old[0]) < 1e-6 and color > old[1]):
                self.pixels[x, y] = (z, color)

    def line(self, a, b, color: int) -> None:
        steps = max(1, math.ceil(max(abs(a[0] - b[0]), abs(a[1] - b[1]))))
        # Bound work even for a zoomed line mostly outside the viewport.
        steps = min(steps, 4 * (self.width + self.height))
        for i in range(steps + 1):
            t = i / steps
            self.dot(*(a[k] + (b[k] - a[k]) * t for k in range(3)), color)

    def label(self, p, text: str) -> None:
        x, y = round(p[0]) // self.sx, round(p[1]) // self.sy
        for offset, char in enumerate(text):
            if 0 <= x + offset < self.columns and 0 <= y < self.rows:
                self.labels[x + offset, y] = char

    def text(self, color: bool = False) -> list[str]:
        lines = []
        for row in range(self.rows):
            chars, current_color = [], None
            for col in range(self.columns):
                mask, nearest, ink = 0, math.inf, 0
                for dy in range(self.sy):
                    for dx in range(self.sx):
                        pixel = self.pixels.get((col * self.sx + dx, row * self.sy + dy))
                        if pixel is not None:
                            mask |= DOTS[dy][dx] if self.mode == "braille" else 1 << dy
                            if pixel[0] < nearest:
                                nearest, ink = pixel
                if self.mode == "braille":
                    char = chr(0x2800 + mask) if mask else " "
                elif self.mode == "block":
                    char = (" ", "▀", "▄", "█")[mask]
                else:
                    char = "." if ink in (1, 2) else "*" if ink else " "
                char = self.labels.get((col, row), char)
                if color and ink != current_color:
                    chars.append(f"\033[38;5;{COLORS.get(ink, 250)}m")
                    current_color = ink
                chars.append(char)
            lines.append("".join(chars) + ("\033[0m" if color else ""))
        return lines


@dataclass
class Camera:
    yaw: float = 35.0
    pitch: float = 28.0
    zoom: float = 1.0
    orbit: bool = True

    def key(self, key: str) -> None:
        self.yaw += {"a": -8, "d": 8}.get(key, 0)
        self.pitch = max(-80, min(80, self.pitch + {"w": 6, "s": -6}.get(key, 0)))
        if key in ("+", "="):
            self.zoom = min(4, self.zoom * 1.15)
        if key == "-":
            self.zoom = max(0.3, self.zoom / 1.15)
        if key == "o":
            self.orbit = not self.orbit
        if key in {"a", "d", "w", "s"}:
            self.orbit = False
        if key == "r":
            self.yaw, self.pitch, self.zoom, self.orbit = 35, 28, 1, True


class Scene:
    """Actual and commanded XYZ in one shared physical scale, relative to first sample."""

    def __init__(self, result):
        drives = result.telemetry["drives"]
        count = len(result.telemetry["t"])

        def series(field):
            axes = []
            for letter in "XYZ":
                names = result.axis_drives.get(letter, [])
                axes.append([sum(drives[d][field][i] for d in names) / len(names)
                             if names else 0.0 for i in range(count)])
            return list(zip(*axes, strict=True))

        actual, commanded = series("act"), series("cmd")
        origin = actual[0]
        self.actual = [tuple(p[k] - origin[k] for k in range(3)) for p in actual]
        self.commanded = [tuple(p[k] - origin[k] for k in range(3)) for p in commanded]
        all_points = self.actual + self.commanded
        self.lo = tuple(min(p[k] for p in all_points) for k in range(3))
        self.hi = tuple(max(p[k] for p in all_points) for k in range(3))
        self.center = tuple((a + b) / 2 for a, b in zip(self.lo, self.hi, strict=True))
        self.span = max(1.0, *(b - a for a, b in zip(self.lo, self.hi, strict=True)))
        self.stride = max(1, count // 600)

    def panel(self, index: int, columns: int, rows: int, camera: Camera,
              mode: str, view: str = "3D", color: bool = False) -> list[str]:
        raster = Raster(columns, rows, mode)
        yaw, pitch = math.radians(camera.yaw), math.radians(camera.pitch)
        # Assume cells are roughly twice as tall as wide; braille dots are nearly square.
        pixel_aspect = 2 * raster.sx / raster.sy
        def camera_point(p):
            x, y, z = (p[k] - self.center[k] for k in range(3))
            if view == "3D":
                u = math.cos(yaw) * x - math.sin(yaw) * y
                v = math.sin(yaw) * x + math.cos(yaw) * y
                depth = -math.cos(pitch) * v - math.sin(pitch) * z
                v = math.sin(pitch) * v - math.cos(pitch) * z
                factor = 3 * self.span / (3 * self.span + depth)
            else:
                u, v = {"XY": (x, -y), "XZ": (x, -z), "YZ": (y, -z)}[view]
                depth, factor = 0.0, 1.0
            return u * factor, v * factor, depth

        lo = tuple(min(self.lo[k], -self.span * 0.06) for k in range(3))
        hi = tuple(max(self.hi[k], self.span * 0.06) for k in range(3))
        bounds = [camera_point(p) for p in itertools.product(*[
            (lo[k] - self.span * 0.08, hi[k] + (self.span * 0.20 if k == 2 else 0))
            for k in range(3)])]
        u0, u1 = min(p[0] for p in bounds), max(p[0] for p in bounds)
        v0, v1 = min(p[1] for p in bounds), max(p[1] for p in bounds)
        scale = min((raster.width - 2) / max(u1 - u0, 0.001),
                    (raster.height - 2) * pixel_aspect / max(v1 - v0, 0.001)) * 0.94
        scale *= camera.zoom if view == "3D" else 1

        def project(p):
            u, v, depth = camera_point(p)
            return (raster.width / 2 + (u - (u0 + u1) / 2) * scale,
                    raster.height / 2 + (v - (v0 + v1) / 2) * scale / pixel_aspect, depth)

        def line(a, b, ink):
            raster.line(project(a), project(b), ink)

        # Layer 1: reference floor, motion envelope (not a stock/collision model).
        if view == "3D":
            for i in range(6):
                x, y = (lo[k] + (hi[k] - lo[k]) * i / 5 for k in (0, 1))
                line((x, lo[1], lo[2]), (x, hi[1], lo[2]), 1)
                line((lo[0], y, lo[2]), (hi[0], y, lo[2]), 1)
            for bits in itertools.product((0, 1), repeat=3):
                a = tuple((lo[k], hi[k])[bits[k]] for k in range(3))
                for k in range(3):
                    if bits[k] == 0:
                        b = list(a)
                        b[k] = hi[k]
                        line(a, b, 1)
        # Layers 2/3: complete commanded path and actual history, sharing a depth buffer.
        for points, end, ink in ((self.commanded, len(self.commanded) - 1, 2),
                                 (self.actual, index, 3)):
            samples = list(range(0, end + 1, self.stride))
            if not samples or samples[-1] != end:
                samples.append(end)
            for a, b in zip(samples, samples[1:], strict=False):
                line(points[a], points[b], ink)
        # Layer 4: schematic tool at measured position. This is not cutter geometry.
        tip = self.actual[index]
        top = (tip[0], tip[1], tip[2] + self.span * 0.16)
        line(tip, top, 4)
        radius = self.span * 0.025
        for i in range(12):
            a, b = i * math.tau / 12, (i + 1) * math.tau / 12
            line((top[0] + radius * math.cos(a), top[1] + radius * math.sin(a), top[2]),
                 (top[0] + radius * math.cos(b), top[1] + radius * math.sin(b), top[2]), 4)
        raster.label(project(tip), "@")
        # Coordinate triad uses the same projection as the model.
        origin = tuple(lo[k] - self.span * 0.08 for k in range(3))
        for k, letter in enumerate("XYZ"):
            if view != "3D" and letter not in view:
                continue
            end = list(origin)
            end[k] += self.span * 0.18
            line(origin, end, k + 5)
            raster.label(project(end), letter)
        title = f" {view} | {raster.width}x{raster.height} punktow "
        return [title.ljust(columns, "-")[:columns], *raster.text(color)]

    def render(self, index: int, columns: int, rows: int, camera: Camera,
               mode: str = "braille", color: bool = False) -> list[str]:
        if columns < 110 or rows < 18:
            return self.panel(index, columns, rows - 1, camera, mode, color=color)
        left_width = int(columns * 0.67)
        right_width = columns - left_width - 3
        left = self.panel(index, left_width, rows - 1, camera, mode, color=color)
        right = []
        for i, view in enumerate(("XY", "XZ", "YZ")):
            height = rows // 3 + (1 if i < rows % 3 else 0)
            right += self.panel(index, right_width, height - 1, camera, mode, view, color)
        return [a + " | " + b for a, b in zip(left, right, strict=True)]
