"""Nominalna geometria przygotówki i odlewu obrotowego. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
Profil odlewu: pary (Z, R) w mm, jedna strona osi Z, obrót o pełne 360 stopni.
"""

from dataclasses import asdict, dataclass
from math import isfinite

import numpy as np

ANCHOR_TITLES = {
    "top-center": "Środek górnej powierzchni", "bottom-center": "Środek dolnej powierzchni",
    "top-front-left": "Lewy przedni narożnik na górze",
    "top-front-right": "Prawy przedni narożnik na górze",
    "top-back-left": "Lewy tylny narożnik na górze",
    "top-back-right": "Prawy tylny narożnik na górze",
    "bottom-front-left": "Lewy przedni narożnik na dole",
    "bottom-front-right": "Prawy przedni narożnik na dole",
    "bottom-back-left": "Lewy tylny narożnik na dole",
    "bottom-back-right": "Prawy tylny narożnik na dole",
}
ANCHOR_NAMES = tuple(ANCHOR_TITLES)


def anchor_name(face, fx, fy):
    """Nazwa punktu zera: face top/bottom, fx -1/0/1 (lewo/środek/prawo), fy -1/0/1 (przód/tył)."""
    if fx == 0 and fy == 0:
        return f"{face}-center"
    if fx == 0 or fy == 0:
        raise ValueError("Zero na przygotówce: narożnik albo środek")
    return f"{face}-{'front' if fy < 0 else 'back'}-{'left' if fx < 0 else 'right'}"


@dataclass(frozen=True)
class Workpiece:
    shape: str = "box"
    x: float = 100.0
    y: float = 80.0
    height: float = 30.0
    diameter: float = 80.0
    bore: float = 40.0
    profile: tuple = ((0.0, 25.0), (15.0, 40.0), (40.0, 30.0))
    position: tuple = (100.0, 100.0, -100.0)
    anchor: str = "top-center"
    offset: str = "G54"
    material: str = "aluminium"

    def __post_init__(self):
        if self.shape not in ("box", "cylinder", "tube", "casting"):
            raise ValueError("Nieznany kształt przygotówki")
        dims = (self.x, self.y, self.height, self.diameter, self.bore)
        if not all(isfinite(v) and 0 < v <= 100000 for v in dims):
            raise ValueError("Wymiary muszą być dodatnimi liczbami do 100000 mm")
        if self.shape == "tube" and self.bore >= self.diameter:
            raise ValueError("Otwór rury musi być mniejszy niż średnica zewnętrzna")
        if self.anchor not in ANCHOR_NAMES:
            raise ValueError("Nieznany punkt zerowy przygotówki")
        if self.offset not in ("G54", "G55", "G56", "G57", "G58", "G59"):
            raise ValueError("Wybierz układ od G54 do G59")
        if len(self.position) != 3 or not all(isfinite(v) and abs(v) <= 100000
                                             for v in self.position):
            raise ValueError("Położenie wymaga trzech skończonych współrzędnych")
        if not 2 <= len(self.profile) <= 32:
            raise ValueError("Profil odlewu wymaga od 2 do 32 punktów (Z, R)")
        if any(len(p) != 2 or not all(isfinite(v) and abs(v) <= 100000 for v in p) or p[1] < 0
               for p in self.profile):
            raise ValueError("Punkty profilu: skończone Z i promień R ≥ 0")
        if any(a[0] >= b[0] for a, b in zip(self.profile, self.profile[1:], strict=False)):
            raise ValueError("Współrzędne Z profilu muszą rosnąć")
        if not any(p[1] > 0 for p in self.profile):
            raise ValueError("Profil musi mieć dodatni promień")
        if not isinstance(self.material, str) or not 1 <= len(self.material) <= 60:
            raise ValueError("Nazwa materiału wymaga od 1 do 60 znaków")

    def to_dict(self):
        return asdict(self)

    def mesh(self, segments=48):
        if not 8 <= segments <= 128:
            raise ValueError("Liczba segmentów obrotu: 8–128")
        if self.shape == "box":
            vertices = np.array([(x, y, z) for z in (0, self.height)
                                 for y in (-self.y / 2, self.y / 2)
                                 for x in (-self.x / 2, self.x / 2)], dtype=float)
            faces = np.array([(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6),
                              (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7),
                              (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)])
        else:
            radius = self.diameter / 2
            if self.shape == "tube":
                profile = [(radius, 0), (radius, self.height),
                           (self.bore / 2, self.height), (self.bore / 2, 0)]
            else:
                outer = ([(r, z) for z, r in self.profile] if self.shape == "casting" else
                         [(radius, 0), (radius, self.height)])
                profile = [(0, outer[0][1]), *outer, (0, outer[-1][1])]
            vertices, faces = revolve(profile, segments)
        low, high = vertices.min(axis=0), vertices.max(axis=0)
        face, _, rest = self.anchor.partition("-")
        pick_x = {"left": low[0], "right": high[0]}
        pick_y = {"front": low[1], "back": high[1]}
        parts = rest.split("-")
        anchor = np.array([pick_x.get(parts[-1], 0.0) if len(parts) == 2 else 0.0,
                           pick_y.get(parts[0], 0.0) if len(parts) == 2 else 0.0,
                           high[2] if face == "top" else low[2]])
        return vertices - anchor + np.asarray(self.position), faces

    def bounds(self):
        """Najmniejszy i największy punkt przygotówki w G53 (mm): ((x, y, z), (x, y, z))."""
        vertices, _faces = self.mesh()
        return tuple(vertices.min(axis=0)), tuple(vertices.max(axis=0))

    def fit_issues(self, limits):
        """Komunikaty, gdy przygotówka lub jej zero wychodzą poza zakresy osi {oś: (min, max)}."""
        low, high = self.bounds()
        issues = []
        for i, axis in enumerate("XYZ"):
            if axis not in limits:
                continue
            lo, hi = limits[axis]
            if low[i] < lo - 1e-6 or high[i] > hi + 1e-6:
                issues.append(f"Przygotówka wychodzi poza zakres osi {axis} "
                              f"({low[i]:.1f}…{high[i]:.1f} mm przy limitach {lo:.1f}…{hi:.1f})")
            elif not lo - 1e-6 <= self.position[i] <= hi + 1e-6:
                issues.append(f"Zero {axis} = {self.position[i]:.1f} mm jest poza zakresem osi")
        return issues


def revolve(profile, segments):
    vertices, rings, faces = [], [], []
    for radius, z in profile:
        if rings and radius == 0 and profile[len(rings) - 1] == (radius, z):
            continue
        ring = []
        for angle in np.linspace(0, 2 * np.pi, segments, endpoint=False) if radius else [0]:
            ring.append(len(vertices))
            vertices.append((radius * np.cos(angle), radius * np.sin(angle), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:] + rings[:1], strict=True):
        if len(a) == len(b) == 1:
            continue
        for j in range(segments):
            k = (j + 1) % segments
            if len(a) == 1:
                faces.append((a[0], b[k], b[j]))
            elif len(b) == 1:
                faces.append((a[j], a[k], b[0]))
            else:
                faces.extend(((a[j], a[k], b[k]), (a[j], b[k], b[j])))
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int)


def offset_command(workpiece, metric=True):
    scale = 1.0 if metric else 25.4
    xyz = " ".join(f"{axis}{value / scale:.6f}" for axis, value in
                   zip("XYZ", workpiece.position, strict=True))
    return f"G10 L2 P{int(workpiece.offset[1:]) - 53} {xyz}"
