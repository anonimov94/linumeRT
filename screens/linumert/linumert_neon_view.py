# SPDX-License-Identifier: GPL-2.0-or-later
"""Classic × Neon: szybki podgląd ścieżki QPainter — detal z bliska i cała maszyna.

Model-Author: Claude · 2026-10-24. Bez komend LinuxCNC, pinów HAL i sygnału życia.

Renderer rysuje wyłącznie linie i półprzezroczyste bryły szkieletowe: bez trójkątów,
bufora głębokości i sortowania ścian (problem z SKIN-01 nie występuje). Ścieżka jest
rysowana partiami po klasie koloru, poświata to szeroka półprzezroczysta linia w trybie
CompositionMode_Plus pod cienką jasną. Odświeżanie ≤ 30 Hz (CLAUDE.md §5).

Strefy: pierwsze N punktów programu — lime, ostatnie N — magenta, następny punkt — żółty
celownik z DTG. Widok maszyny jest poglądowy (brama XYZ), nie jest modelem kolizji Plant.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import math
import time

import numpy as np
from linumert.programs.toolpath import DEMO_STOCK, Toolpath
from PyQt5 import QtCore, QtGui, QtWidgets

FRAME_MS = 34
RAPID_FEED = 6000.0
DEFAULT_G54 = (100.0, 100.0, -150.0)   # jak starter symulatora, gdy program nie podał offsetu
SPEEDS = (1, 2, 4, 8, 16, 32, 64)
# Role ścieżki, wspólne dla wszystkich motywów; wartości z docs/design/tokens.yaml (neon).
NEON = {"cyan": "#00f0ff", "lime": "#b6ff00", "magenta": "#ff2bd6", "yellow": "#ffe600",
        "orange": "#ff8a00", "violet": "#8a5cff", "red": "#ff3355"}
MONO = "JetBrains Mono"


def color(hex_value, alpha=1.0):
    c = QtGui.QColor(hex_value)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


class PathScene(QtCore.QObject):
    """Stan wspólny obu widoków: ścieżka, pozycja na niej, odtwarzanie offline albo śledzenie."""

    changed = QtCore.pyqtSignal()

    def __init__(self, toolpath: Toolpath, stock=DEMO_STOCK, live=False, parent=None):
        super().__init__(parent)
        self.toolpath = toolpath
        self.stock = stock
        self.live = live
        self.index, self.s = 0, 0.0
        self.playing = not live
        self.speed = 8
        self.zone_count = 6
        self.seconds = toolpath.seconds(RAPID_FEED)
        offset = toolpath.offset if np.any(toolpath.offset) else np.array(DEFAULT_G54)
        self.offset = np.asarray(offset, dtype=float)
        self._last = time.monotonic()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(FRAME_MS)

    # --- pozycja ---
    @property
    def done(self):
        return self.index >= len(self.toolpath)

    def tool_position(self):
        return self.toolpath.position(self.index, self.s)

    def next_move(self):
        return None if self.done else self.toolpath.moves[self.index]

    def dtg(self):
        return self.toolpath.dtg(self.index, self.s)

    def zone(self, index):
        return self.toolpath.zone(index, self.zone_count)

    def elapsed(self):
        if self.done:
            return float(self.seconds[-1])
        m = self.toolpath.moves[self.index]
        feed = m.feed if not m.rapid and m.feed > 0 else RAPID_FEED
        return float(self.seconds[self.index]) + self.s / (feed / 60.0)

    # --- sterowanie podglądem (tylko offline) ---
    def tick(self):
        now = time.monotonic()
        dt, self._last = min(0.1, now - self._last), now
        if self.playing and not self.live:
            self.advance(dt)
        self.changed.emit()

    def advance(self, dt):
        budget = dt * self.speed
        moves = self.toolpath.moves
        while budget > 0 and not self.done:
            m = moves[self.index]
            v = (m.feed if not m.rapid and m.feed > 0 else RAPID_FEED) / 60.0
            rem = m.length - self.s
            if rem / v > budget:
                self.s += v * budget
                budget = 0
            else:
                budget -= rem / v
                self.index, self.s = self.index + 1, 0.0
        if self.done:
            self.playing = False

    def toggle(self):
        if self.live:
            return
        if self.done:
            self.index, self.s = 0, 0.0
        self.playing = not self.playing

    def step(self, direction):
        if self.live:
            return
        self.playing = False
        if direction > 0 and not self.done:
            self.index, self.s = self.index + 1, 0.0
        elif direction < 0:
            if self.s > 1e-3 and not self.done:
                self.s = 0.0
            elif self.index > 0:
                self.index, self.s = self.index - 1, 0.0

    def restart(self):
        if not self.live:
            self.index, self.s, self.playing = 0, 0.0, True

    def seek(self, distance):
        if not self.live:
            self.index, self.s = self.toolpath.seek(distance)

    def cycle_speed(self):
        self.speed = SPEEDS[(SPEEDS.index(self.speed) + 1) % len(SPEEDS)]

    def set_zone_count(self, count):
        self.zone_count = max(1, min(15, int(count)))

    # --- śledzenie LinuxCNC (tylko odczyt) ---
    def follow(self, motion_line, work_position):
        """Pozycja z stat.motion_line i pozycji w układzie detalu; nic nie wysyła do CNC."""
        self.index, self.s = self.toolpath.locate(int(motion_line), work_position, self.index)


class Camera:
    def __init__(self, yaw, pitch, scale, target):
        self.yaw, self.pitch, self.scale = yaw, pitch, scale
        self.target = np.asarray(target, dtype=float)

    def projector(self, w, h):
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        t, s, ox, oy = self.target, self.scale, w / 2, h / 2

        def project(points):
            p = np.asarray(points, dtype=float) - t
            u = p[..., 0] * cy - p[..., 1] * sy
            v = p[..., 0] * sy + p[..., 1] * cy
            return np.stack((ox + u * s, oy - (p[..., 2] * cp + v * sp) * s), axis=-1)
        return project


BOX_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7))
BOX_FACES = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


def box_corners(a, b):
    return np.array([[a[0], a[1], a[2]], [b[0], a[1], a[2]], [b[0], b[1], a[2]],
                     [a[0], b[1], a[2]], [a[0], a[1], b[2]], [b[0], a[1], b[2]],
                     [b[0], b[1], b[2]], [a[0], b[1], b[2]]])


def polygon(points):
    return QtGui.QPolygonF([QtCore.QPointF(float(x), float(y)) for x, y in points])


class NeonPathView(QtWidgets.QWidget):
    """Jeden widok sceny: mode='detail' (zbliżenie, śledzi narzędzie) albo 'machine'."""

    def __init__(self, scene: PathScene, mode="detail", palette=None, parent=None):
        super().__init__(parent)
        if mode not in ("detail", "machine"):
            raise ValueError(f"unknown neon view: {mode}")
        self.scene, self.mode = scene, mode
        self.bg = getattr(palette, "background", "#07050d")
        self.fg = getattr(palette, "text", "#f3eeff")
        self.muted = getattr(palette, "muted", "#ab9fcc")
        self.accent = getattr(palette, "accent", NEON["cyan"])
        self.follow = True
        if mode == "detail":
            self.camera = Camera(0.62, 0.62, 8.0, (60, 40, -10))
        else:
            self.camera = Camera(0.72, 0.5, 1.0, (0, 0, 0))
            self.zoom = 1.0
        self._drag = None
        self.setMinimumSize(80, 60)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        scene.changed.connect(self.update)

    # --- interakcja (kamera i podgląd offline; bez komend CNC) ---
    def mousePressEvent(self, event):
        self._drag = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        d = event.pos() - self._drag
        self._drag = event.pos()
        self.camera.yaw += d.x() * 0.008
        self.camera.pitch = max(0.1, min(1.45, self.camera.pitch + d.y() * 0.006))
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag = None

    def mouseDoubleClickEvent(self, event):
        if self.mode == "detail":
            self.follow = not self.follow

    def wheelEvent(self, event):
        f = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        if self.mode == "detail":
            self.camera.scale = max(2.0, min(30.0, self.camera.scale * f))
            self.follow = True
        else:
            self.zoom = max(0.6, min(3.0, self.zoom * f))
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            self.scene.toggle()
        elif key == QtCore.Qt.Key_Right:
            self.scene.step(1)
        elif key == QtCore.Qt.Key_Left:
            self.scene.step(-1)
        else:
            super().keyPressEvent(event)

    # --- rysowanie ---
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(self.bg))
        if self.mode == "detail":
            self.paint_detail(p, w, h)
        else:
            self.paint_machine(p, w, h)
        p.end()

    def paint_detail(self, p, w, h):
        sc = self.scene
        tool = sc.tool_position()
        sx, sy, sz = sc.stock
        target = tool if self.follow else np.array((sx / 2, sy / 2, -sz / 2))
        cam = self.camera
        # Pierwsza klatka ustawia kamerę od razu; dalej płynne dojście za narzędziem.
        lag = 0.25 if getattr(self, "_aimed", False) else 1.0
        self._aimed = True
        cam.target = cam.target + (target - cam.target) * lag
        scale = cam.scale if self.follow else min(w, h) / (max(sx, sy) * 1.25)
        saved, cam.scale = cam.scale, scale
        project = cam.projector(w, h)
        cam.scale = saved
        # stół i przygotówka z siatką 10 mm na wierzchu
        self.grid(p, project, (-60, 180), (-60, 140), -sz, 10, color(self.muted, 0.18))
        self.box(p, project, (0, 0, -sz), (sx, sy, 0), self.muted, 0.05)
        self.grid(p, project, (0, sx), (0, sy), 0, 10, color(self.muted, 0.28), inner=True)
        origin = project(np.zeros(3))
        for axis, col in ((0, NEON["red"]), (1, NEON["lime"]), (2, NEON["cyan"])):
            end = np.zeros(3)
            end[axis] = 12
            q = project(end)
            p.setPen(QtGui.QPen(QtGui.QColor(col), 2))
            p.drawLine(QtCore.QPointF(*origin), QtCore.QPointF(*q))
        self.path(p, project, np.zeros(3), glow=1.0, swept=scale)
        self.zone_labels(p, project, np.zeros(3))
        self.tool(p, project, tool, glow=max(6.0, scale))
        self.next_marker(p, project, np.zeros(3), big=True)
        # podziałka 10 mm i opis
        length = 10 * scale
        p.setPen(QtGui.QPen(QtGui.QColor(self.muted), 1.5))
        y = h - 14
        p.drawLine(QtCore.QPointF(w - 14 - length, y), QtCore.QPointF(w - 14, y))
        p.setFont(QtGui.QFont(MONO, 8))
        p.drawText(QtCore.QRectF(w - 120, y - 18, 106, 14), QtCore.Qt.AlignRight, "10 mm")
        self.hud(p, [f"ZBLIŻENIE · {scale:.1f} px/mm" + ("" if self.follow else " · cały detal"),
                     "DEMO offline" if not sc.live else "LinuxCNC · tylko odczyt"])

    def paint_machine(self, p, w, h):
        sc = self.scene
        g = sc.offset
        sx, sy, sz = sc.stock
        lo, hi = np.array((-40, -20, -300)), np.array((460, 340, 110))
        cam = self.camera
        cam.target, cam.scale = (lo + hi) / 2, 1.0
        unit = cam.projector(0, 0)(box_corners(lo, hi))
        ex, ey = np.abs(unit).max(axis=0)
        cam.scale = min((w - 24) / (2 * ex), (h - 24) / (2 * ey)) * self.zoom
        project = cam.projector(w, h)
        tool = sc.tool_position() + g
        self.grid(p, project, (-100, 520), (-80, 400), -300, 40, color(self.muted, 0.12))
        self.box(p, project, (0, 0, -300), (420, 320, -200), NEON["violet"], 0.06)
        self.box(p, project, (10, 10, -200), (410, 310, -182), self.muted, 0.08)
        pen = QtGui.QPen(color(self.muted, 0.5), 1)
        p.setPen(pen)
        for y in range(50, 310, 50):
            a, b = project(np.array([(10, y, -182), (410, y, -182)]))
            p.drawLine(QtCore.QPointF(*a), QtCore.QPointF(*b))
        for x in (-30, 440):
            self.box(p, project, (x - 8, 0, -200), (x + 8, 320, -188), self.muted, 0.1)
        self.box(p, project, (g[0], g[1], g[2] - sz), (g[0] + sx, g[1] + sy, g[2]), self.fg, 0.08)
        for cx, cy in ((g[0] - 18, g[1] + 20), (g[0] - 18, g[1] + sy - 20),
                       (g[0] + sx + 8, g[1] + 20), (g[0] + sx + 8, g[1] + sy - 20)):
            self.box(p, project, (cx, cy - 6, -182), (cx + 10, cy + 6, g[2] - sz + 8),
                     NEON["orange"], 0.12)
        self.path(p, project, g, glow=0.7, swept=0)
        self.zone_labels(p, project, g, labels=False)
        gy = tool[1] + 40
        for x0, x1 in ((-46, -14), (424, 456)):
            self.box(p, project, (x0, gy - 25, -188), (x1, gy + 25, 70), self.accent, 0.06)
        self.box(p, project, (-46, gy - 10, 40), (456, gy + 25, 100), self.accent, 0.07)
        self.box(p, project, (tool[0] - 35, gy - 26, 0), (tool[0] + 35, gy - 10, 110),
                 NEON["magenta"], 0.08)
        self.box(p, project, (tool[0] - 22, tool[1] - 22, tool[2] + 48),
                 (tool[0] + 22, tool[1] + 22, tool[2] + 200), NEON["magenta"], 0.08)
        self.tool(p, project, tool, glow=0)
        self.next_marker(p, project, g, big=False)
        tp = sc.toolpath
        if len(tp):
            p.setFont(QtGui.QFont(MONO, 8, QtGui.QFont.Bold))
            first = project(tp.moves[0].end + g)
            last = project(tp.moves[-1].end + g)
            p.setPen(QtGui.QColor(NEON["lime"]))
            p.drawText(QtCore.QPointF(first[0] + 8, first[1] + 4), "START")
            p.setPen(QtGui.QColor(NEON["magenta"]))
            p.drawText(QtCore.QPointF(last[0] + 8, last[1] + 4), "END")
        self.hud(p, ["MASZYNA · CAŁOŚĆ (poglądowo)",
                     f"G53 X{tool[0]:.3f} Y{tool[1]:.3f} Z{tool[2]:.3f}"])

    # --- elementy ---
    def hud(self, p, lines):
        p.setFont(QtGui.QFont(MONO, 8))
        p.setPen(QtGui.QColor(self.muted))
        for i, text in enumerate(lines):
            p.drawText(QtCore.QPointF(10, 16 + 14 * i), text)

    def grid(self, p, project, xr, yr, z, step, col, inner=False):
        xs = np.arange(xr[0] + (step if inner else 0), xr[1] + (0 if inner else 1), step)
        ys = np.arange(yr[0] + (step if inner else 0), yr[1] + (0 if inner else 1), step)
        if inner:
            xs, ys = xs[xs < xr[1]], ys[ys < yr[1]]
        seg = [((x, yr[0], z), (x, yr[1], z)) for x in xs]
        seg += [((xr[0], y, z), (xr[1], y, z)) for y in ys]
        if not seg:
            return
        q = project(np.array(seg, dtype=float))
        p.setPen(QtGui.QPen(col, 1))
        p.drawLines([QtCore.QLineF(a[0], a[1], b[0], b[1]) for a, b in q])

    def box(self, p, project, a, b, stroke, fill_alpha):
        q = project(box_corners(a, b))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(color(stroke, fill_alpha))
        for face in BOX_FACES:
            p.drawPolygon(polygon(q[list(face)]))
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(stroke), 1))
        p.drawLines([QtCore.QLineF(*q[i], *q[j]) for i, j in BOX_EDGES])

    def cylinder(self, p, project, center, radius, z0, z1, stroke, fill_alpha):
        a = np.linspace(0, 2 * math.pi, 20, endpoint=False)
        ring = np.column_stack((center[0] + radius * np.cos(a), center[1] + radius * np.sin(a)))
        bottom = project(np.column_stack((ring, np.full(len(a), z0))))
        top = project(np.column_stack((ring, np.full(len(a), z1))))
        li, ri = int(np.argmin(bottom[:, 0])), int(np.argmax(bottom[:, 0]))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(color(stroke, fill_alpha))
        p.drawPolygon(polygon([bottom[li], top[li], top[ri], bottom[ri]]))
        p.setPen(QtGui.QPen(QtGui.QColor(stroke), 1.2))
        p.drawPolygon(polygon(bottom))
        p.drawPolygon(polygon(top))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawLine(QtCore.QPointF(*bottom[li]), QtCore.QPointF(*top[li]))
        p.drawLine(QtCore.QPointF(*bottom[ri]), QtCore.QPointF(*top[ri]))

    def tool(self, p, project, tip, glow):
        self.cylinder(p, project, tip, 3, tip[2], tip[2] + 26, self.accent, 0.18)
        self.cylinder(p, project, tip, 11, tip[2] + 26, tip[2] + 48, self.muted, 0.1)
        if self.mode == "detail":
            self.cylinder(p, project, tip, 20, tip[2] + 48, tip[2] + 110, self.muted, 0.06)
        if glow:
            q = project(tip)
            r = 18 + glow
            grad = QtGui.QRadialGradient(QtCore.QPointF(*q), r)
            grad.setColorAt(0, color(self.accent, 0.75))
            grad.setColorAt(1, color(self.accent, 0))
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(grad)
            p.drawEllipse(QtCore.QPointF(*q), r, r)
            p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            p.setBrush(QtCore.Qt.NoBrush)

    def path(self, p, project, offset, glow, swept):
        sc = self.scene
        groups = {k: QtGui.QPainterPath() for k in
                  ("done", "todo", "rapid", "rapid_done", "start", "end")}
        swept_path = QtGui.QPainterPath()
        tool = sc.tool_position()
        for i, m in enumerate(sc.toolpath.moves):
            q = project(m.points + offset)
            zone = sc.zone(i)
            if i == sc.index and zone == "mid" and not m.rapid:
                k = int(np.searchsorted(m.cum, sc.s))
                head = project(tool + offset)
                done = np.vstack((q[:k], head[None]))
                todo = np.vstack((head[None], q[k:]))
                groups["done"].addPolygon(polygon(done))
                groups["todo"].addPolygon(polygon(todo))
                if swept:
                    swept_path.addPolygon(polygon(done))
                continue
            finished = i < sc.index
            if zone != "mid":
                key = zone
            elif m.rapid:
                key = "rapid_done" if finished else "rapid"
            else:
                key = "done" if finished else "todo"
            groups[key].addPolygon(polygon(q))
            if swept and finished and not m.rapid:
                swept_path.addPolygon(polygon(q))
        p.setBrush(QtCore.Qt.NoBrush)
        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)

        def stroke(path, col, width, alpha, dash=False):
            pen = QtGui.QPen(color(col, alpha), width)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            if dash:
                pen.setDashPattern([4, 4])
            p.setPen(pen)
            p.drawPath(path)

        if swept:
            stroke(swept_path, self.accent, 6 * swept, 0.07)   # szerokość freza Ø6
        stroke(groups["todo"], NEON["violet"], 1.2 * glow, 0.5)
        stroke(groups["rapid"], NEON["orange"], 1.1 * glow, 0.55, dash=True)
        stroke(groups["rapid_done"], NEON["orange"], 1.1 * glow, 0.25, dash=True)
        for key, col in (("done", self.accent), ("start", NEON["lime"]), ("end", NEON["magenta"])):
            wide = 6 if key == "done" else 7
            stroke(groups[key], col, wide * glow, 0.18)
            stroke(groups[key], col, (1.6 if key == "done" else 2.0) * glow, 1.0)
        p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)

    def zone_labels(self, p, project, offset, labels=True):
        sc = self.scene
        n = len(sc.toolpath)
        p.setFont(QtGui.QFont(MONO, 7, QtGui.QFont.Bold))
        metrics = p.fontMetrics()
        placed = []
        for i, m in enumerate(sc.toolpath.moves):
            zone = sc.zone(i)
            if zone == "mid":
                continue
            col = QtGui.QColor(NEON["lime"] if zone == "start" else NEON["magenta"])
            x, y = project(m.end + offset)
            if not labels:
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(col)
                p.drawEllipse(QtCore.QPointF(x, y), 2.6, 2.6)
                continue
            dy = 0
            while any(abs(px - x) < 16 and abs(py - (y + dy)) < 16 for px, py in placed):
                dy -= 17
            placed.append((x, y + dy))
            text = str(i + 1) if zone == "start" else ("END" if i == n - 1 else f"−{n - i}")
            width = max(18, metrics.horizontalAdvance(text) + 10)
            if dy:
                p.setPen(QtGui.QPen(color(col.name(), 0.5), 1))
                p.drawLine(QtCore.QPointF(x, y), QtCore.QPointF(x, y + dy))
            rect = QtCore.QRectF(x - width / 2, y + dy - 8, width, 16)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(rect, 8, 8)
            p.setPen(QtGui.QColor(self.bg))
            p.drawText(rect, QtCore.Qt.AlignCenter, text)
        p.setBrush(QtCore.Qt.NoBrush)

    def next_marker(self, p, project, offset, big):
        sc = self.scene
        m = sc.next_move()
        if m is None:
            return
        q = project(m.end + offset)
        head = project(sc.tool_position() + offset)
        yellow = QtGui.QColor(NEON["yellow"])
        pen = QtGui.QPen(color(NEON["yellow"], 0.85), 1.2)
        pen.setDashPattern([3, 4])
        p.setPen(pen)
        p.drawLine(QtCore.QPointF(*head), QtCore.QPointF(*q))
        pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 6)
        r = (11 if big else 8) + 4 * pulse
        center = QtCore.QPointF(*q)
        p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        p.setPen(QtGui.QPen(color(NEON["yellow"], 0.25), 6))
        p.drawEllipse(center, r, r)
        p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
        p.setPen(QtGui.QPen(yellow, 2))
        p.drawEllipse(center, r, r)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.drawLine(QtCore.QPointF(q[0] + dx * (r + 3), q[1] + dy * (r + 3)),
                       QtCore.QPointF(q[0] + dx * (r + 9), q[1] + dy * (r + 9)))
        p.setBrush(yellow)
        p.drawEllipse(center, 2.5, 2.5)
        p.setBrush(QtCore.Qt.NoBrush)
        # etykieta: numer punktu, linia programu, DTG
        l1 = f"P{sc.index + 1:03d} · N{m.line:04d}"
        l2 = f"DTG {sc.dtg():.3f} mm"
        p.setFont(QtGui.QFont(MONO, 8, QtGui.QFont.DemiBold))
        fm = p.fontMetrics()
        bw = max(fm.horizontalAdvance(l1), fm.horizontalAdvance(l2)) + 16
        bh = 2 * fm.height() + 10
        bx, by = q[0] + r + 14, q[1] - bh - 8
        if bx + bw > self.width() - 8:
            bx = q[0] - r - 14 - bw
        if by < 8:
            by = q[1] + r + 8
        p.setPen(QtGui.QPen(color(NEON["yellow"], 0.6), 1))
        p.drawLine(center, QtCore.QPointF(bx if bx > q[0] else bx + bw, by + bh / 2))
        p.setBrush(color(self.bg, 0.88))
        p.setPen(QtGui.QPen(yellow, 1))
        p.drawRoundedRect(QtCore.QRectF(bx, by, bw, bh), 7, 7)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QColor(self.muted))
        p.drawText(QtCore.QPointF(bx + 8, by + 4 + fm.ascent()), l1)
        p.setPen(yellow)
        p.drawText(QtCore.QPointF(bx + 8, by + 6 + fm.height() + fm.ascent()), l2)


class NeonTimeline(QtWidgets.QWidget):
    """Oś programu: strefy START/KONIEC, G0, postęp, następny punkt; klik = przewinięcie."""

    def __init__(self, scene: PathScene, palette=None, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.bg = getattr(palette, "background", "#07050d")
        self.line = getattr(palette, "raised", "#2a2140")
        self.accent = getattr(palette, "accent", NEON["cyan"])
        self.setMinimumHeight(30)
        self.setMaximumHeight(34)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        scene.changed.connect(self.update)

    def mousePressEvent(self, event):
        self._seek(event.pos().x())

    def mouseMoveEvent(self, event):
        self._seek(event.pos().x())

    def _seek(self, x):
        self.scene.seek(max(0.0, x / max(1, self.width())) * self.scene.toolpath.length)

    def paintEvent(self, event):
        sc, tp = self.scene, self.scene.toolpath
        w, h = self.width(), self.height()
        total = tp.length or 1.0
        cum = tp.cum

        def x(d):
            return 2 + (w - 4) * d / total

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(self.bg))
        p.setPen(QtGui.QPen(QtGui.QColor(self.line), 1))
        p.drawRoundedRect(QtCore.QRectF(0.5, 4.5, w - 1, h - 9), 6, 6)
        current = tp.travelled(sc.index, sc.s)
        p.fillRect(QtCore.QRectF(x(0), 5, x(current) - x(0), h - 10), color(self.accent, 0.22))
        n, k = len(tp), sc.zone_count
        for i, m in enumerate(tp.moves):
            if m.rapid and sc.zone(i) == "mid":
                p.fillRect(QtCore.QRectF(x(cum[i]), h - 9, max(1, x(cum[i + 1]) - x(cum[i])), 3),
                           color(NEON["orange"], 0.55))
        for a, b, col in ((0, min(k, n), NEON["lime"]), (max(0, n - k), n, NEON["magenta"])):
            xa = x(cum[a])
            xb = max(xa + 3, x(cum[b]))
            p.fillRect(QtCore.QRectF(xa, 6, xb - xa, 4), QtGui.QColor(col))
            for i in range(a, b):
                p.fillRect(QtCore.QRectF(x(cum[i + 1]) - 0.5, 10, 1, h - 20), color(col, 0.8))
        if not sc.done:
            xn = x(cum[sc.index + 1])
            p.fillRect(QtCore.QRectF(xn - 0.5, 4, 1, h - 8), QtGui.QColor(NEON["yellow"]))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(NEON["yellow"]))
            p.drawPolygon(polygon([(xn, 5), (xn - 4, 0), (xn + 4, 0)]))
        p.fillRect(QtCore.QRectF(x(current) - 1.5, 2, 3, h - 4), QtGui.QColor(self.accent))
        p.end()


class NeonDetailPanel(QtWidgets.QWidget):
    """Widok detalu z osią programu i opisem następnego punktu (rola 'toolpath')."""

    def __init__(self, scene: PathScene, palette=None, parent=None):
        super().__init__(parent)
        self.scene = scene
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.view = NeonPathView(scene, "detail", palette)
        self.timeline = NeonTimeline(scene, palette)
        self.info = QtWidgets.QLabel()
        self.info.setTextFormat(QtCore.Qt.PlainText)
        self.info.setStyleSheet(f"font-family: '{MONO}'; color: {NEON['yellow']};")
        # Długi blok G-code nie może poszerzać karty w układzie 1280×800.
        self.info.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.timeline)
        layout.addWidget(self.info)
        scene.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        sc = self.scene
        m = sc.next_move()
        if m is None:
            self.info.setText("Program zakończony · M30")
            return
        zone = {"start": f"START {sc.index + 1}/{sc.zone_count}",
                "end": f"KONIEC −{len(sc.toolpath) - sc.index}", "mid": "PROGRAM"}[sc.zone(sc.index)]
        code = sc.toolpath.source[m.line - 1] if 0 < m.line <= len(sc.toolpath.source) else ""
        self.info.setText(f"NASTĘPNY P{sc.index + 1:03d} · N{m.line:04d} · {zone} · "
                          f"DTG {sc.dtg():.3f} mm · {code}")


def neon_viewport_factory(toolpath=None, live=False):
    """Fabryka ról 'toolpath' (detal) i 'machine' (całość) ze wspólną sceną."""
    from linumert.programs.toolpath import demo_toolpath

    scenes = {}

    def create(role, palette):
        if "scene" not in scenes:
            scenes["scene"] = PathScene(toolpath or demo_toolpath(), live=live)
        scene = scenes["scene"]
        if role == "toolpath":
            return NeonDetailPanel(scene, palette)
        if role == "machine":
            return NeonPathView(scene, "machine", palette)
        return None
    create.scenes = scenes
    return create
