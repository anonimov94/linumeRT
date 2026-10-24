# SPDX-License-Identifier: GPL-2.0-or-later
"""Classic × Neon: szybki podgląd ścieżki QPainter — detal z bliska i cała maszyna.

Model-Author: Claude · 2026-10-24. Bez komend LinuxCNC, pinów HAL i sygnału życia.

Dwa widoki jednej sceny. Styl i efekty (cieniowanie, cienie, poświata, materiał) ustawia
operator per widok (⚙ w rogu); techniki oszczędne opisuje `linumert_neon_render.py`.
Dodatkowo: tło i statyczna ścieżka wypalane do pixmapy — w rzucie równoległym podążanie
kamery za narzędziem to czyste przesunięcie 2D, więc pixmapa jest tylko przesuwana;
w bezczynności odświeżanie 10 Hz; skrawanie materiału porcjami czasu (≤ 10 Hz).

Strefy: pierwsze N punktów programu — lime, ostatnie N — magenta, następny punkt — żółty
celownik z DTG. Widok maszyny jest poglądowy (brama XYZ), nie jest modelem kolizji Plant.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import math
import time

import numpy as np
from linumert.programs.toolpath import DEMO_STOCK, Toolpath
from linumert_neon_render import (
    DEFAULT_PRESET,
    FPS_CHOICES,
    IDLE_FPS,
    METAL,
    PRESET_LABELS,
    PRESETS,
    STYLES,
    MemoryStore,
    QualityGovernor,
    Shader,
    bake_material,
    box_corners,
    color,
    cylinder_points,
    frame_budget_ms,
    image_transform,
    polygon,
    preset_name,
)
from PyQt5 import QtCore, QtGui, QtWidgets

FRAME_MS = 34
RAPID_FEED = 6000.0
DEFAULT_G54 = (100.0, 100.0, -150.0)   # jak starter symulatora, gdy program nie podał offsetu
SPEEDS = (1, 2, 4, 8, 16, 32, 64)
MATERIAL_PERIOD = 0.1                  # skrawanie i wypiekanie tekstury ≤ 10 Hz
MATERIAL_BUDGET = 0.004                # [s] na takt; więcej przy nadrabianiu po przewinięciu
MATERIAL_CATCHUP = 0.012
STREAM_BUDGET = 0.004                  # [s] na klatkę na wypiekanie następnego kompletu warstw
# Role ścieżki, wspólne dla wszystkich motywów; wartości z docs/design/tokens.yaml (motywy).
NEON = {"cyan": "#00f0ff", "lime": "#b6ff00", "magenta": "#ff2bd6", "yellow": "#ffe600",
        "orange": "#ff8a00", "violet": "#8a5cff", "red": "#ff3355"}
MONO = "JetBrains Mono"


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
        self.material = None
        self._cut_d = 0.0
        self._material_at = 0.0
        self._image = (None, None)
        self._last = time.monotonic()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(FRAME_MS)

    # --- pozycja ---
    def projected(self, project, offset):
        """Wszystkie polilinie ruchów rzutowane jednym wywołaniem (lista tablic (n, 2))."""
        if not hasattr(self, "_points"):
            moves = self.toolpath.moves
            self._points = np.concatenate([m.points for m in moves]) if moves else np.zeros((0, 3))
            self._splits = np.cumsum([len(m.points) for m in moves])[:-1]
        return np.split(project(self._points + offset), self._splits)

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

    # --- takt ---
    def tick(self):
        now = time.monotonic()
        dt, self._last = min(0.1, now - self._last), now
        if self.playing and not self.live:
            self.advance(dt)
        if self.material is not None and now - self._material_at >= MATERIAL_PERIOD:
            self._material_at = now
            self.update_material()
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

    # --- materiał (StockMap z linumert_sim, układ detalu, frez palcowy Ø6 z programu demo) ---
    def enable_material(self):
        if self.material is None:
            from linumert_sim.cutter import make_cutter
            from linumert_sim.zmap import StockMap
            sx, sy, sz = self.stock
            self.material = StockMap("BOX", 0.0, 0.0, sx, sy, -sz, 0.0, cell=0.5)
            self._cutter = make_cutter(1, 50.0, 6.0, "flat")
            self._cut_d = 0.0
        return self.material

    def update_material(self, budget=None):
        """Skrawanie od ostatniego miejsca do bieżącego, porcjami czasu (jak streaming w grach)."""
        m, tp = self.material, self.toolpath
        target = tp.travelled(self.index, self.s)
        if target < self._cut_d - 1e-6:
            m.reset()
            self._cut_d = 0.0
        if budget is None:
            budget = MATERIAL_CATCHUP if target - self._cut_d > 50 else MATERIAL_BUDGET
        start = time.perf_counter()
        while self._cut_d < target - 1e-6 and time.perf_counter() - start < budget:
            i, s = tp.seek(self._cut_d)
            if i >= len(tp):
                break
            move = tp.moves[i]
            end_d = min(target, float(tp.cum[i]) + move.length, self._cut_d + 2.0)
            if not move.rapid:
                p1 = move.at(end_d - float(tp.cum[i]))
                m.cut(self._cutter, tuple(move.at(s)), tuple(p1))
            self._cut_d = max(end_d, self._cut_d + 1e-6)
        return self._cut_d >= target - 1e-6

    def material_image(self, accent):
        key = (self.material.version, accent)
        if self._image[0] != key:
            m = self.material
            self._image = (key, bake_material(m.display(), m.cell, m.z_top, self.stock[2], accent))
        return self._image[1]

    def draw_material(self, p, project, offset, accent):
        """Warstwy tekstury materiału od najniższej, każda afinicznie na swoim Z."""
        m = self.material
        p.save()
        for z, image in self.material_image(accent):
            p.setTransform(image_transform(project, m.x0 + offset[0], m.y0 + offset[1],
                                           z + offset[2], m.cell))
            p.drawImage(QtCore.QPointF(0, 0), image)
        p.restore()

    # --- sterowanie podglądem (tylko offline) ---
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

    def projector(self, cx, cy, target=None):
        cyaw, syaw = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        t = self.target if target is None else np.asarray(target, dtype=float)
        s = self.scale

        def project(points):
            p = np.asarray(points, dtype=float) - t
            u = p[..., 0] * cyaw - p[..., 1] * syaw
            v = p[..., 0] * syaw + p[..., 1] * cyaw
            return np.stack((cx + u * s, cy - (p[..., 2] * cp + v * sp) * s), axis=-1)
        return project

    def toward(self):
        """Kierunek od sceny do obserwatora (do odrzucania ścian tylnych)."""
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        return np.array((-math.sin(self.yaw) * cp, -math.cos(self.yaw) * cp, sp))

    def key(self):
        return round(self.yaw, 4), round(self.pitch, 4), round(self.scale, 3)


class NeonPathView(QtWidgets.QWidget):
    """Jeden widok sceny: mode='detail' (zbliżenie, śledzi narzędzie) albo 'machine'."""

    settings_changed = QtCore.pyqtSignal(object)

    def __init__(self, scene: PathScene, mode="detail", palette=None, store=None, parent=None):
        super().__init__(parent)
        if mode not in ("detail", "machine"):
            raise ValueError(f"unknown neon view: {mode}")
        self.scene, self.mode = scene, mode
        self.bg = getattr(palette, "background", "#07050d")
        self.fg = getattr(palette, "text", "#f3eeff")
        self.muted = getattr(palette, "muted", "#ab9fcc")
        self.accent = getattr(palette, "accent", NEON["cyan"])
        self.store = store or MemoryStore()
        self.store_key = f"render/{mode}"
        self.settings = self.store.load(self.store_key, PRESETS[DEFAULT_PRESET[mode]])
        self.governor = QualityGovernor()
        self.follow = True
        if mode == "detail":
            self.camera = Camera(0.62, 0.62, 8.0, (60, 40, -10))
        else:
            self.camera = Camera(0.72, 0.5, 1.0, (0, 0, 0))
            self.zoom = 1.0
        self._aimed = False
        self._drag = None
        self._hitch = False
        self._active = None         # komplet warstw: tło, baza ścieżki, ukończone, ślad
        self._pending = None        # następny komplet wypiekany porcjami
        self._last_paint = 0.0
        self.paint_ms = 0.0
        self.frame_ms = 0.0
        self.setMinimumSize(80, 60)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.menu_button = QtWidgets.QToolButton(self)
        self.menu_button.setText("⚙")
        self.menu_button.setToolTip("Sposób renderowania tego widoku")
        self.menu_button.setAccessibleName("Sposób renderowania")
        self.menu_button.setFixedSize(44, 44)          # cel dotykowy z tokens.yaml
        self.menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.menu_button.setStyleSheet(
            f"QToolButton {{ background: {color(self.bg, 0.75).name(QtGui.QColor.HexArgb)};"
            f" color: {self.fg}; border: 1px solid {self.muted}; border-radius: 10px;"
            " font-size: 18px; } QToolButton::menu-indicator { image: none; }")
        self.menu = QtWidgets.QMenu(self.menu_button)
        self.menu.aboutToShow.connect(self._fill_menu)
        self.menu_button.setMenu(self.menu)
        if self.settings.material:
            scene.enable_material()
        scene.changed.connect(self._maybe_update)

    # --- ustawienia ---
    def set_settings(self, settings, persist=True):
        self.settings = settings
        if persist:
            self.store.save(self.store_key, settings)
        if settings.material:
            self.scene.enable_material()
        self.governor = QualityGovernor()
        self._active = self._pending = None
        self.settings_changed.emit(settings)
        self.update()

    def _fill_menu(self):
        from dataclasses import replace
        menu, s = self.menu, self.settings
        menu.clear()
        current = preset_name(s)
        menu.addSection("Jakość")
        for name, preset in PRESETS.items():
            act = menu.addAction(PRESET_LABELS[name])
            act.setCheckable(True)
            act.setChecked(name == current)
            act.triggered.connect(lambda _=False, p=preset: self.set_settings(p))
        menu.addSection("Styl")
        for style in STYLES:
            act = menu.addAction({"linie": "Linie (neon)", "cieniowany": "Cieniowany"}[style])
            act.setCheckable(True)
            act.setChecked(s.style == style)
            act.triggered.connect(lambda _=False, v=style: self.set_settings(replace(s, style=v)))
        menu.addSection("Efekty")
        for field, label in (("shadows", "Cienie rzucane"), ("glow", "Poświata ścieżki"),
                             ("material", "Materiał (skrawanie)"), ("antialias", "Wygładzanie"),
                             ("adaptive", "Automatyczna jakość")):
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(getattr(s, field))
            act.triggered.connect(
                lambda on, f=field: self.set_settings(replace(self.settings, **{f: bool(on)})))
        fps = menu.addMenu(f"Limit klatek: {s.fps} FPS")
        for value in FPS_CHOICES:
            act = fps.addAction(f"{value} FPS")
            act.setCheckable(True)
            act.setChecked(s.fps == value)
            act.triggered.connect(lambda _=False, v=value: self.set_settings(replace(s, fps=v)))

    # --- tempo odświeżania ---
    def _maybe_update(self):
        if not self.isVisible():
            return
        idle = not (self.scene.playing or self.scene.live) and self._drag is None
        fps = min(self.settings.fps, IDLE_FPS) if idle else self.settings.fps
        if time.monotonic() - self._last_paint >= 1.0 / fps - 0.004:
            self.update()

    def resizeEvent(self, event):
        self.menu_button.move(self.width() - self.menu_button.width() - 8, 8)
        self._active = self._pending = None
        super().resizeEvent(event)

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
        start = time.perf_counter()
        self._hitch = False
        eff = self.governor.effective(self.settings)
        w, h = self.width(), self.height()
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, eff.antialias)
        p.fillRect(self.rect(), QtGui.QColor(self.bg))
        if self.mode == "detail":
            self.paint_detail(p, w, h, eff)
        else:
            self.paint_machine(p, w, h, eff)
        p.end()
        now = time.monotonic()
        dt, self._last_paint = now - self._last_paint, now
        self.paint_ms = (time.perf_counter() - start) * 1000
        if not self._hitch:
            # HUD i regulator widzą klatki ustalone, bez jednorazowego wypiekania.
            self.frame_ms = self.paint_ms if not self.frame_ms else \
                self.frame_ms * 0.8 + self.paint_ms * 0.2
            if self.settings.adaptive:
                self.governor.record(self.paint_ms, frame_budget_ms(self.settings.fps),
                                     min(dt, 1.0))

    def _pixmap(self, w, h):
        dpr = self.devicePixelRatioF()
        pix = QtGui.QPixmap(max(1, int(w * dpr)), max(1, int(h * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(QtGui.QColor(self.bg))
        return pix

    def _bake(self, key, reference, w, h, margin, eff, glow, swept, offset3, draw_static):
        """Generator wypiekający komplet warstw krokami (strumieniowanie jak w grach)."""
        layers = {"key": key, "reference": np.array(reference, dtype=float),
                  "margin": margin, "done_upto": 0, "ready": False}
        project = self.camera.projector(w / 2 + margin, h / 2 + margin, reference)
        layers["project"] = project
        bg = self._pixmap(w + 2 * margin, h + 2 * margin)
        bp = QtGui.QPainter(bg)
        bp.setRenderHint(QtGui.QPainter.Antialiasing, eff.antialias)
        draw_static(bp, project)
        bp.end()
        layers["bg"] = bg
        yield layers
        layers["base"], layers["base_glow"] = self._build_base(project, offset3, w, h, margin,
                                                               eff, glow)
        layers["done"] = self._layer(w, h, margin)
        layers["done_glow"] = self._layer(w, h, margin, 0.5) if eff.glow else None
        layers["trail"] = self._layer(w, h, margin, 0.5) if swept else None
        yield layers
        target = self.scene.index
        while layers["done_upto"] < target:
            self._extend_done(layers, project, offset3, eff, glow, swept,
                              min(target, layers["done_upto"] + 24))
            yield layers
        layers["ready"] = True
        yield layers

    @staticmethod
    def _run(builder, budget):
        """Kroki wypiekania do gotowości albo do wyczerpania budżetu czasu (None = do końca)."""
        start = time.perf_counter()
        for layers in builder:
            if layers["ready"]:
                return layers
            if budget is not None and time.perf_counter() - start > budget:
                return None
        return None

    def _layers(self, w, h, margin, eff, glow, swept, offset3, draw_static):
        """Aktywny komplet warstw i jego przesunięcie na ekranie w tej klatce.

        Tło i ścieżka są wypiekane względem punktu odniesienia; przy podążaniu kamery są tylko
        przesuwane. Gdy zapas przesuwu kończy się (60 %), następny komplet piecze się w tle
        porcjami ≤ STREAM_BUDGET na klatkę i podmienia po ukończeniu.
        """
        cam, sc = self.camera, self.scene
        key = (cam.key(), w, h, margin, tuple(offset3), sc.zone_count, round(swept, 3),
               eff.style, eff.glow, eff.antialias, eff.material)

        def shift(layers):
            return cam.projector(w / 2, h / 2)(layers["reference"]) - (w / 2, h / 2)

        args = (w, h, margin, eff, glow, swept, offset3, draw_static)
        layers = self._active
        if layers is None or layers["key"] != key:
            self._pending = None
            self._hitch = True       # jednorazowe wypiekanie (start, obrót, zoom): poza budżetem
            layers = self._active = self._run(self._bake(key, cam.target, *args), None)
        elif margin:
            far = float(np.max(np.abs(shift(layers))))
            if far > margin * 0.6 and self._pending is None:
                self._pending = self._bake(key, cam.target.copy(), *args)
            if self._pending is not None:
                ready = self._run(self._pending, None if far > margin else STREAM_BUDGET)
                if ready is not None:
                    self._pending = None
                    layers = self._active = ready
        if sc.index < layers["done_upto"]:         # przewinięcie wstecz: ukończone od nowa
            layers["done"] = self._layer(w, h, margin)
            layers["done_glow"] = self._layer(w, h, margin, 0.5) if eff.glow else None
            layers["trail"] = self._layer(w, h, margin, 0.5) if swept else None
            layers["done_upto"] = 0
        if sc.index > layers["done_upto"]:
            self._extend_done(layers, layers["project"], offset3, eff, glow, swept, sc.index)
        return layers, shift(layers)

    def paint_detail(self, p, w, h, eff):
        sc = self.scene
        tool = sc.tool_position()
        sx, sy, sz = sc.stock
        cam = self.camera
        target = tool if self.follow else np.array((sx / 2, sy / 2, -sz / 2))
        # Pierwsza klatka ustawia kamerę od razu; dalej płynne dojście za narzędziem.
        cam.target = cam.target + (target - cam.target) * (0.25 if self._aimed else 1.0)
        self._aimed = True
        if not self.follow:
            cam.scale = min(w, h) / (max(sx, sy) * 1.25)
        scale = cam.scale
        material = eff.material and sc.material is not None
        toward = cam.toward()
        margin = int(max(w, h) * 0.3)    # zapas przesuwu tła przed ponownym wypieczeniem

        def draw_static(bp, project):
            shader = Shader(bp, project, toward, eff)
            self.grid(bp, project, (-60, 180), (-60, 140), -sz, 10, color(self.muted, 0.18))
            shader.box((0, 0, -sz), (sx, sy, 0), METAL if eff.style != "linie" else self.muted,
                       fill_alpha=0.05, solid_alpha=1.0)
            if not material:
                self.grid(bp, project, (0, sx), (0, sy), 0, 10, color(self.muted, 0.28),
                          inner=True)
            origin = project(np.zeros(3))
            for axis, col in ((0, NEON["red"]), (1, NEON["lime"]), (2, NEON["cyan"])):
                end = np.zeros(3)
                end[axis] = 12
                bp.setPen(QtGui.QPen(QtGui.QColor(col), 2))
                bp.drawLine(QtCore.QPointF(*origin), QtCore.QPointF(*project(end)))

        swept = scale if not material and eff.glow else 0     # ślad freza to efekt
        layers, offset = self._layers(w, h, margin, eff, 1.0, swept, np.zeros(3), draw_static)
        p.drawPixmap(QtCore.QPointF(offset[0] - margin, offset[1] - margin), layers["bg"])
        project = cam.projector(w / 2, h / 2)
        if material:
            sc.draw_material(p, project, np.zeros(3), self.accent)
        shader = Shader(p, project, toward, eff)
        if eff.shadows:
            plane = 0.0 if tool[2] >= 0 or not material else self._height_under(tool)
            shader.drop_shadow([np.vstack(cylinder_points(tool, 3, tool[2], tool[2] + 26)),
                                np.vstack(cylinder_points(tool, 11, tool[2] + 26,
                                                          tool[2] + 48))], plane)
        self.path(p, layers, offset, np.zeros(3), eff, 1.0, swept, cam, w, h)
        self.zone_labels(p, project, np.zeros(3))
        self.tool(shader, project, tool, glow=max(6.0, scale) if eff.glow else 0)
        self.next_marker(p, project, np.zeros(3), big=True)
        length = 10 * scale
        p.setPen(QtGui.QPen(QtGui.QColor(self.muted), 1.5))
        y = h - 14
        p.drawLine(QtCore.QPointF(w - 14 - length, y), QtCore.QPointF(w - 14, y))
        p.setFont(QtGui.QFont(MONO, 8))
        p.drawText(QtCore.QRectF(w - 120, y - 18, 106, 14), QtCore.Qt.AlignRight, "10 mm")
        self.hud(p, [f"ZBLIŻENIE · {scale:.1f} px/mm" + ("" if self.follow else " · cały detal"),
                     "DEMO offline" if not sc.live else "LinuxCNC · tylko odczyt",
                     self.quality_text()])

    def _height_under(self, tool):
        m = self.scene.material
        ix = int((tool[0] - m.x0) / m.cell)
        iy = int((tool[1] - m.y0) / m.cell)
        if 0 <= ix < m.nx and 0 <= iy < m.ny:
            return float(min(0.0, max(m.h[iy, ix], m.z_bottom)))
        return 0.0

    def paint_machine(self, p, w, h, eff):
        sc = self.scene
        g = sc.offset
        sx, sy, sz = sc.stock
        lo, hi = np.array((-40, -20, -300)), np.array((460, 340, 110))
        cam = self.camera
        cam.target = (lo + hi) / 2
        cam.scale = 1.0
        unit = cam.projector(0, 0)(box_corners(lo, hi))
        ex, ey = np.abs(unit).max(axis=0)
        cam.scale = min((w - 24) / (2 * ex), (h - 24) / (2 * ey)) * self.zoom
        project = cam.projector(w / 2, h / 2)
        toward = cam.toward()
        material = eff.material and sc.material is not None
        tool = sc.tool_position() + g
        table_z = -182.0

        def draw_static(bp, proj):
            shader = Shader(bp, proj, toward, eff)
            self.grid(bp, proj, (-100, 520), (-80, 400), -300, 40, color(self.muted, 0.12))
            shader.box((0, 0, -300), (420, 320, -200), NEON["violet"], 0.06)
            shader.box((10, 10, -200), (410, 310, table_z), self.muted, 0.08)
            bp.setPen(QtGui.QPen(color(self.muted, 0.5), 1))
            for yy in range(50, 310, 50):
                a, b = proj(np.array([(10, yy, table_z), (410, yy, table_z)]))
                bp.drawLine(QtCore.QPointF(*a), QtCore.QPointF(*b))
            for x in (-30, 440):
                shader.box((x - 8, 0, -200), (x + 8, 320, -188), self.muted, 0.1)
            shader.box((g[0], g[1], g[2] - sz), (g[0] + sx, g[1] + sy, g[2]),
                       METAL if eff.style != "linie" else self.fg, 0.08, solid_alpha=1.0)
            for cx, cy in ((g[0] - 18, g[1] + 20), (g[0] - 18, g[1] + sy - 20),
                           (g[0] + sx + 8, g[1] + 20), (g[0] + sx + 8, g[1] + sy - 20)):
                shader.box((cx, cy - 6, table_z), (cx + 10, cy + 6, g[2] - sz + 8),
                           NEON["orange"], 0.12)

        layers, offset = self._layers(w, h, 0, eff, 0.7, 0, tuple(g), draw_static)
        p.drawPixmap(QtCore.QPointF(offset[0], offset[1]), layers["bg"])
        if material:
            sc.draw_material(p, project, g, self.accent)
        self.path(p, layers, offset, g, eff, 0.7, 0, cam, w, h)
        self.zone_labels(p, project, g, labels=False)
        # Ruchome części bramy: sortowanie od najdalszej, cienie na stół przed bryłami.
        gy = tool[1] + 40
        parts = [((-46, gy - 25, -188), (-14, gy + 25, 70), self.accent),
                 ((424, gy - 25, -188), (456, gy + 25, 70), self.accent),
                 ((-46, gy - 10, 40), (456, gy + 25, 100), self.accent),
                 ((tool[0] - 35, gy - 26, 0), (tool[0] + 35, gy - 10, 110), NEON["magenta"]),
                 ((tool[0] - 22, tool[1] - 22, tool[2] + 48),
                  (tool[0] + 22, tool[1] + 22, tool[2] + 200), NEON["magenta"])]
        shader = Shader(p, project, toward, eff)
        if eff.shadows:
            groups = [box_corners(a, b) for a, b, _ in parts[2:]]
            groups.append(np.vstack(cylinder_points(tool, 11, tool[2], tool[2] + 48)))
            shader.drop_shadow(groups, table_z, alpha=0.3)
        forward = -toward
        parts.sort(key=lambda part: -float(np.dot((np.add(part[0], part[1])) / 2, forward)))
        for a, b, col in parts:
            shader.box(a, b, col, 0.07, solid_alpha=0.88)
        self.tool(shader, project, tool, glow=0)
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
                     f"G53 X{tool[0]:.3f} Y{tool[1]:.3f} Z{tool[2]:.3f}", self.quality_text()])

    # --- elementy ---
    def quality_text(self):
        text = (f"Render: {PRESET_LABELS[preset_name(self.settings)]} · "
                f"{self.settings.fps} FPS · {self.frame_ms:.1f} ms/klatkę")
        if self.governor.level:
            text += f" · auto ↓{self.governor.level}"
        return text

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

    def tool(self, shader, project, tip, glow):
        shader.cylinder(tip, 3, tip[2], tip[2] + 26, self.accent, 0.18)
        shader.cylinder(tip, 11, tip[2] + 26, tip[2] + 48, METAL, 0.1, solid_alpha=0.8)
        if self.mode == "detail":
            # Nos wrzeciona półprzezroczysty: w zbliżeniu nie może zasłaniać skrawania.
            shader.cylinder(tip, 20, tip[2] + 48, tip[2] + 110, self.muted, 0.06,
                            solid_alpha=0.35)
        if glow:
            p = shader.p
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

    def _stroke(self, p, polylines, col, width, alpha, dash=False):
        # Osobne polilinie zamiast jednej QPainterPath: Qt nie liczy wtedy obrysu sumy
        # nakładających się pętli dla półprzezroczystego pióra (~10× szybciej).
        pen = QtGui.QPen(color(col, alpha), width)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        if dash:
            pen.setDashPattern([4, 4])
        p.setPen(pen)
        for line in polylines:
            p.drawPolyline(line)

    def _layer(self, w, h, margin, scale=1.0):
        dpr = self.devicePixelRatioF() * scale
        pix = QtGui.QPixmap(max(1, int((w + 2 * margin) * dpr)),
                            max(1, int((h + 2 * margin) * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(QtCore.Qt.transparent)
        return pix

    def _paint_layer(self, pix, eff, draw, additive=False):
        lp = QtGui.QPainter(pix)
        lp.setRenderHint(QtGui.QPainter.Antialiasing, eff.antialias)
        lp.setBrush(QtCore.Qt.NoBrush)
        if additive:
            lp.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
        draw(lp)
        lp.end()

    def _build_base(self, project, offset, w, h, margin, eff, glow):
        """Warstwa bazowa: cała ścieżka jako „do wykonania” + strefy; zależy tylko od kamery."""
        sc = self.scene
        groups = {k: [] for k in ("todo", "rapid", "start", "end")}
        screen = sc.projected(project, offset)
        for i, m in enumerate(sc.toolpath.moves):
            zone = sc.zone(i)
            name = zone if zone != "mid" else ("rapid" if m.rapid else "todo")
            groups[name].append(polygon(screen[i]))

        def lines(lp):
            self._stroke(lp, groups["todo"], NEON["violet"], 1.2 * glow, 0.5)
            self._stroke(lp, groups["rapid"], NEON["orange"], 1.1 * glow, 0.55, dash=True)
            for name, col in (("start", NEON["lime"]), ("end", NEON["magenta"])):
                self._stroke(lp, groups[name], col, 2.0 * glow, 1.0)

        def halo(lp):
            for name, col in (("start", NEON["lime"]), ("end", NEON["magenta"])):
                self._stroke(lp, groups[name], col, 7 * glow, 0.18)

        base = self._layer(w, h, margin)
        self._paint_layer(base, eff, lines)
        glow_layer = None
        if eff.glow:            # poświata jest rozmyta — połowa rozdzielczości wystarcza
            glow_layer = self._layer(w, h, margin, 0.5)
            self._paint_layer(glow_layer, eff, halo, additive=True)
        return base, glow_layer

    def _extend_done(self, cache, project, offset, eff, glow, swept, upto):
        """Bufor akumulacyjny: dorysowuje tylko ruchy ukończone od ostatniej klatki."""
        sc = self.scene
        moves = [i for i in range(cache["done_upto"], upto)
                 if sc.zone(i) == "mid" and not sc.toolpath.moves[i].rapid]
        screen = sc.projected(project, offset) if len(moves) > 8 else None
        new = [polygon(screen[i] if screen is not None
                       else project(sc.toolpath.moves[i].points + offset)) for i in moves]
        cache["done_upto"] = upto
        if not new:
            return
        self._paint_layer(cache["done"], eff,
                          lambda lp: self._stroke(lp, new, self.accent, 1.6 * glow, 1.0))
        if cache["done_glow"] is not None:
            self._paint_layer(cache["done_glow"], eff, lambda lp: self._stroke(
                lp, new, self.accent, 6 * glow, 0.18), additive=True)
        if cache["trail"] is not None:
            self._paint_layer(cache["trail"], eff, lambda lp: self._stroke(
                lp, new, self.accent, 6 * swept, 0.07))    # szerokość freza Ø6

    def path(self, p, layers, offset2d, offset, eff, glow, swept, cam, w, h):
        """Ścieżka z warstw (baza + ukończone) i na żywo tylko bieżący ruch."""
        sc = self.scene
        margin = layers["margin"]
        corner = QtCore.QPointF(offset2d[0] - margin, offset2d[1] - margin)
        p.save()
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        if layers["trail"] is not None:
            p.drawPixmap(corner, layers["trail"])
        p.drawPixmap(corner, layers["base"])
        p.drawPixmap(corner, layers["done"])
        if eff.glow:
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
            for name in ("base_glow", "done_glow"):
                if layers[name] is not None:
                    p.drawPixmap(corner, layers[name])
        p.restore()
        if sc.done or sc.zone(sc.index) != "mid" or sc.next_move().rapid:
            return
        m = sc.next_move()
        project = cam.projector(w / 2, h / 2)
        q = project(m.points + offset)
        k = int(np.searchsorted(m.cum, sc.s))
        head = project(sc.tool_position() + offset)
        done = [polygon(np.vstack((q[:k], head[None])))]
        p.save()
        p.setBrush(QtCore.Qt.NoBrush)
        if swept:
            self._stroke(p, done, self.accent, 6 * swept, 0.07)
        if eff.glow:
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
            self._stroke(p, done, self.accent, 6 * glow, 0.18)
        self._stroke(p, done, self.accent, 1.6 * glow, 1.0)
        p.restore()

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

    def __init__(self, scene: PathScene, palette=None, store=None, parent=None):
        super().__init__(parent)
        self.scene = scene
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.view = NeonPathView(scene, "detail", palette, store)
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
