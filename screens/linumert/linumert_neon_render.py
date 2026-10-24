# SPDX-License-Identifier: GPL-2.0-or-later
"""Classic × Neon: ustawienia renderowania, automatyczna jakość i tanie cieniowanie QPainter.

Model-Author: Claude · 2026-10-24. Bez komend LinuxCNC, pinów HAL i sygnału życia.

Oszczędne techniki jak w grach sieciowych, bez GPU-shaderów i bez nowych zależności:
- presety jakości per widok + ręczne przełączniki, zapis w profilu operatora (QSettings),
- cieniowanie płaskie Lamberta per ściana z odrzucaniem ścian tylnych (bryły wypukłe nie
  potrzebują bufora głębokości), walce gradientem w poprzek sylwetki,
- cienie rzucane jako rzut bryły na płaszczyznę stołu wzdłuż światła — jeden wielokąt,
- materiał: mapa wysokości cieniowana do tekstury („wypiekanie”) najwyżej 10×/s, potem
  nakładana jednym afinicznym drawImage (rzut równoległy przenosi płaszczyznę afinicznie),
- regulator jakości: przy przekroczeniu budżetu klatki kolejno wyłącza drogie efekty.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import json
import math
from dataclasses import asdict, dataclass, fields, replace

import numpy as np
from PyQt5 import QtCore, QtGui

STYLES = ("linie", "cieniowany")
FPS_CHOICES = (15, 20, 30)          # maks. 30 FPS (CLAUDE.md §5)
IDLE_FPS = 10
LIGHT = np.array((-0.45, -0.55, 0.70))  # kierunek DO światła (z przodu z lewej, z góry)
LIGHT = LIGHT / np.linalg.norm(LIGHT)
AMBIENT, DIFFUSE = 0.38, 0.62
METAL = "#9aa7b4"                   # tokens.yaml kolory.fg2 — materiał przygotówki


@dataclass(frozen=True)
class RenderSettings:
    style: str = "cieniowany"
    shadows: bool = False
    glow: bool = True
    material: bool = True
    antialias: bool = True
    fps: int = 30
    adaptive: bool = True

    def __post_init__(self):
        if self.style not in STYLES:
            raise ValueError(f"nieznany styl renderowania: {self.style!r}")
        if self.fps not in FPS_CHOICES:
            raise ValueError(f"niedozwolony limit FPS: {self.fps!r}")
        for f in fields(self):
            if f.type in (bool, "bool") and type(getattr(self, f.name)) is not bool:
                raise ValueError(f"{f.name}: oczekiwano true/false")

    def to_json(self):
        return json.dumps({"version": 1, **asdict(self)}, sort_keys=True)

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        if not isinstance(data, dict) or data.pop("version", None) != 1:
            raise ValueError("nieobsługiwana wersja ustawień renderowania")
        known = {f.name for f in fields(cls)}
        if set(data) - known:
            raise ValueError("nieznane pola ustawień renderowania")
        return cls(**data)


PRESETS = {
    "ekonomiczny": RenderSettings("linie", shadows=False, glow=False, material=False, fps=20),
    "zrownowazony": RenderSettings(),
    "wysoki": RenderSettings("cieniowany", shadows=True, glow=True, material=True),
}
PRESET_LABELS = {"ekonomiczny": "Ekonomiczny", "zrownowazony": "Zrównoważony",
                 "wysoki": "Wysoki", "wlasny": "Własny"}
DEFAULT_PRESET = {"detail": "zrownowazony", "machine": "zrownowazony"}


def preset_name(settings):
    for name, preset in PRESETS.items():
        if preset == settings:
            return name
    return "wlasny"


class MemoryStore:
    """Ustawienia tylko w pamięci (testy, podgląd bez profilu)."""

    def __init__(self):
        self.data = {}

    def load(self, key, default):
        return self.data.get(key, default)

    def save(self, key, settings):
        self.data[key] = settings


class SettingsStore:
    """Profil operatora w QSettings; uszkodzony wpis = preset domyślny, bez wyjątku w GUI."""

    def __init__(self, qsettings=None):
        self.q = qsettings or QtCore.QSettings("linumeRT", "podglad-neon")

    def load(self, key, default):
        raw = self.q.value(key, "", type=str)
        if not raw:
            return default
        try:
            return RenderSettings.from_json(raw)
        except (ValueError, TypeError):
            return default

    def save(self, key, settings):
        self.q.setValue(key, settings.to_json())


class QualityGovernor:
    """Budżet klatki: przekroczenie wyłącza kolejno poświatę, cienie, wygładzanie."""

    STEPS = ("glow", "shadows", "antialias")

    def __init__(self):
        self.level, self.ema, self.calm = 0, 0.0, 0.0

    def effective(self, settings):
        if not settings.adaptive or self.level == 0:
            return settings
        return replace(settings, **{k: False for k in self.STEPS[:self.level]})

    def record(self, ms, budget_ms, dt):
        self.ema = ms if self.ema == 0 else self.ema * 0.85 + ms * 0.15
        if self.ema > budget_ms and self.level < len(self.STEPS):
            self.level += 1
            self.ema, self.calm = budget_ms * 0.7, 0.0
        elif self.ema < budget_ms * 0.35 and self.level > 0:
            self.calm += dt
            if self.calm > 2.0:            # histereza: 2 s zapasu przed powrotem efektu
                self.level -= 1
                self.calm = 0.0
        else:
            self.calm = 0.0


def frame_budget_ms(fps):
    """Część klatki dla jednego widoku: dwa widoki + reszta GUI."""
    return 1000.0 / fps * 0.35


# ------------------------------------------------------------------ geometria i cieniowanie

BOX_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
             (0, 4), (1, 5), (2, 6), (3, 7))
BOX_FACES = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
BOX_NORMALS = np.array(((0, 0, -1), (0, 0, 1), (0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)),
                       dtype=float)


def box_corners(a, b):
    return np.array([[a[0], a[1], a[2]], [b[0], a[1], a[2]], [b[0], b[1], a[2]],
                     [a[0], b[1], a[2]], [a[0], a[1], b[2]], [b[0], a[1], b[2]],
                     [b[0], b[1], b[2]], [a[0], b[1], b[2]]], dtype=float)


def polygon(points):
    return QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in np.asarray(points, float).tolist()])


def color(hex_value, alpha=1.0):
    c = QtGui.QColor(hex_value)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def shaded(hex_value, normal, alpha=1.0):
    """Kolor ściany: ambient + Lambert względem stałego światła warsztatu."""
    k = AMBIENT + DIFFUSE * max(0.0, float(np.dot(normal, LIGHT)))
    c = QtGui.QColor(hex_value)
    out = QtGui.QColor(min(255, int(c.red() * k)), min(255, int(c.green() * k)),
                       min(255, int(c.blue() * k)))
    out.setAlphaF(alpha)
    return out


def convex_hull(points):
    """Otoczka wypukła punktów 2D (łańcuch monotoniczny)."""
    pts = sorted({(round(float(x), 2), round(float(y), 2)) for x, y in points})
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for pt in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], pt) <= 0:
            lower.pop()
        lower.append(pt)
    for pt in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], pt) <= 0:
            upper.pop()
        upper.append(pt)
    return lower[:-1] + upper[:-1]


def shadow_points(points, plane_z):
    """Rzut punktów na płaszczyznę z = plane_z wzdłuż światła (punkty pod nią pomijane)."""
    p = np.asarray(points, dtype=float)
    p = p[p[:, 2] >= plane_z - 1e-6]
    if not len(p):
        return p
    t = (p[:, 2] - plane_z) / LIGHT[2]
    return p - LIGHT[None, :] * t[:, None]


def cylinder_points(center, radius, z0, z1, segments=16):
    a = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    ring = np.column_stack((center[0] + radius * np.cos(a), center[1] + radius * np.sin(a)))
    return (np.column_stack((ring, np.full(segments, z0))),
            np.column_stack((ring, np.full(segments, z1))))


class Shader:
    """Rysowanie brył w ustawionym stylu dla danej kamery (kierunek widzenia `toward`)."""

    def __init__(self, painter, project, toward, settings, edge_alpha=1.0):
        self.p, self.project, self.toward = painter, project, np.asarray(toward, dtype=float)
        self.settings = settings
        self.edge_alpha = edge_alpha

    def box(self, a, b, stroke, fill_alpha=0.06, solid_alpha=0.92, fill=None):
        p = self.p
        q = self.project(box_corners(a, b))
        if self.settings.style == "linie":
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(color(stroke, fill_alpha))
            for face in BOX_FACES:
                p.drawPolygon(polygon(q[list(face)]))
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(color(stroke, self.edge_alpha), 1))
            p.drawLines([QtCore.QLineF(*q[i], *q[j]) for i, j in BOX_EDGES])
            return
        pen = QtGui.QPen(color(stroke, 0.55 * self.edge_alpha), 1)
        for face, normal in zip(BOX_FACES, BOX_NORMALS, strict=True):
            if float(np.dot(normal, self.toward)) <= 1e-6:
                continue                       # ściana tylna — bryła wypukła, bez z-bufora
            p.setPen(pen)
            p.setBrush(shaded(fill or stroke, normal, solid_alpha))
            p.drawPolygon(polygon(q[list(face)]))
        p.setBrush(QtCore.Qt.NoBrush)

    def cylinder(self, center, radius, z0, z1, stroke, fill_alpha=0.15, solid_alpha=0.95):
        p = self.p
        bottom3, top3 = cylinder_points(center, radius, z0, z1, 20)
        bottom, top = self.project(bottom3), self.project(top3)
        li, ri = int(np.argmin(bottom[:, 0])), int(np.argmax(bottom[:, 0]))
        side = polygon([bottom[li], top[li], top[ri], bottom[ri]])
        if self.settings.style == "linie":
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(color(stroke, fill_alpha))
            p.drawPolygon(side)
            p.setPen(QtGui.QPen(QtGui.QColor(stroke), 1.2))
            p.drawPolygon(polygon(bottom))
            p.drawPolygon(polygon(top))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawLine(QtCore.QPointF(*bottom[li]), QtCore.QPointF(*top[li]))
            p.drawLine(QtCore.QPointF(*bottom[ri]), QtCore.QPointF(*top[ri]))
            return
        # Walec: gradient w poprzek sylwetki (blask od strony światła), jaśniejsza pokrywa.
        grad = QtGui.QLinearGradient(QtCore.QPointF(*bottom[li]), QtCore.QPointF(*bottom[ri]))
        grad.setColorAt(0.0, shaded(stroke, np.array((-1.0, 0, 0)), solid_alpha))
        grad.setColorAt(0.32, shaded(stroke, LIGHT, solid_alpha))
        grad.setColorAt(1.0, shaded(stroke, np.array((0.6, 0.6, -0.5)), solid_alpha))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(grad)
        p.drawPolygon(polygon(bottom))
        p.drawPolygon(side)
        cap_visible = self.toward[2] > 0
        p.setBrush(shaded(stroke, np.array((0, 0, 1.0 if cap_visible else -1.0)), solid_alpha))
        p.setPen(QtGui.QPen(color(stroke, 0.6), 1))
        p.drawPolygon(polygon(top if cap_visible else bottom))
        p.setBrush(QtCore.Qt.NoBrush)

    def drop_shadow(self, groups, plane_z, alpha=0.38):
        """Cień brył (listy punktów 3D) na płaszczyźnie z = plane_z."""
        p = self.p
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(0, 0, 0, int(255 * alpha)))
        for pts in groups:
            flat = shadow_points(pts, plane_z)
            if len(flat) < 3:
                continue
            hull = convex_hull(self.project(flat))
            if len(hull) >= 3:
                p.drawPolygon(polygon(hull))
        p.setBrush(QtCore.Qt.NoBrush)


MAX_LAYERS = 24


def bake_material(heights, cell, z_top, depth, accent, base=METAL, step=0.5):
    """Mapa wysokości → warstwy tekstur RGBA [(z, QImage)], od najniższej.

    Każdy poziom (kwantowany co `step`, przy wielu poziomach rzadziej) to osobny obraz
    rysowany afinicznie na swoim Z — tania „paralaksa”: dno kieszeni leży pod ścieżką,
    a wierzch zasłania je w kolejności malarza. Cieniowanie wzgórzowe z gradientu wysokości.
    """
    h = np.asarray(heights, dtype=np.float32)
    gy, gx = np.gradient(h, cell)
    n = np.dstack((-gx, -gy, np.ones_like(h)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    diffuse = np.clip(n @ LIGHT, 0.0, 1.0)
    cut = np.clip((z_top - h) / max(depth, 1e-6), 0.0, 1.0)
    base_rgb = np.array(QtGui.QColor(base).getRgb()[:3], dtype=np.float32)
    acc_rgb = np.array(QtGui.QColor(accent).getRgb()[:3], dtype=np.float32)
    mix = np.where(cut > 1e-3, 0.35 + 0.5 * cut, 0.0)[..., None]
    rgb = base_rgb * (1 - mix) + acc_rgb * mix * 0.55
    rgb *= (AMBIENT + DIFFUSE * diffuse)[..., None] * (1.0 - 0.35 * cut[..., None])
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    levels = np.round(h / step) * step
    unique = np.unique(levels)
    while len(unique) > MAX_LAYERS:
        step *= 2
        levels = np.round(h / step) * step
        unique = np.unique(levels)
    ny, nx = h.shape
    layers = []
    for z in unique:
        rgba = np.zeros((ny, nx, 4), dtype=np.uint8)
        mask = levels == z
        rgba[mask, :3] = rgb[mask]
        rgba[mask, 3] = 245
        rgba = np.ascontiguousarray(rgba)
        image = QtGui.QImage(rgba.data, nx, ny, nx * 4, QtGui.QImage.Format_RGBA8888).copy()
        layers.append((float(z), image))
    return layers


def image_transform(project, x0, y0, z, cell):
    """Afiniczne mapowanie pikseli tekstury (i, j) → ekran dla płaszczyzny z = const."""
    o, ex, ey = project(np.array(((x0, y0, z), (x0 + cell, y0, z), (x0, y0 + cell, z))))
    dx, dy = ex - o, ey - o
    return QtGui.QTransform(dx[0], dx[1], dy[0], dy[1], o[0], o[1])
