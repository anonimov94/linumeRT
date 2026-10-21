"""Geometria podglądu powrotu D38, bez komend do LinuxCNC.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-21

Pierwsza porcja: zmierzona ścieżka XY na jednej głębokości, zakładka, helisa
i łuk styczny. Wynik jest wyłącznie podglądem w układzie maszyny. Nie odtwarza
stanu modalnego ani reszty programu i nie nadaje się do automatycznego wykonania.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class ResumeRefused(ValueError):
    """Brak danych albo geometria poza obsługiwaną pierwszą porcją D38."""


@dataclass(frozen=True)
class ResumeSettings:
    overlap: float = 2.0
    clearance: float = 1.0
    pitch: float = 1.0
    feed: float = 200.0


@dataclass(frozen=True)
class ResumePlan:
    # (x, y, z, rodzaj ruchu). Wszystkie liczby w mm, układ maszyny.
    points: tuple[tuple[float, float, float, str], ...]
    entry: tuple[float, float, float]
    tangent: tuple[float, float]
    overlap: float


def plan_reentry(path, tool_d: float, stock_top: float,
                 settings: ResumeSettings | None = None, *, side=1, radius_scale=0.4):
    """Zejście w helisie → ćwierćokrąg styczny → powtórzenie zakładki.

    Ścieżka wejściowa jest próbkowanym śladem wykonania, nie interpretacją G-code.
    Styczność dotyczy odcinka śladu. Mapa materiału musi osobno zatwierdzić całość.
    """
    settings = settings or ResumeSettings()
    numbers = [tool_d, stock_top, settings.overlap, settings.clearance, settings.pitch,
               settings.feed, radius_scale]
    if not all(math.isfinite(x) for x in numbers) or min(
            tool_d, settings.overlap, settings.clearance, settings.pitch, settings.feed) <= 0:
        raise ResumeRefused("Parametry powrotu muszą być skończone i dodatnie.")
    if side not in (-1, 1) or not 0 < radius_scale <= 0.5:
        raise ResumeRefused("Niepoprawna strona lub promień helisy.")
    if len(path) < 2 or len(path) > 5000:
        raise ResumeRefused("Brak ciągłej historii ruchu roboczego (2–5000 punktów).")
    xyz = [tuple(p[:3]) for p in path]
    if any(len(p) != 3 or not all(math.isfinite(c) for c in p) for p in xyz):
        raise ResumeRefused("Niepoprawny ślad ruchu.")
    left = max(settings.overlap, 0.2 * tool_d)
    overlap = left
    tail = [xyz[-1]]
    for a, b in zip(reversed(xyz[:-1]), reversed(xyz[1:]), strict=True):
        if abs(a[2] - xyz[-1][2]) > 0.001 or abs(b[2] - xyz[-1][2]) > 0.001:
            raise ResumeRefused("Pierwsza porcja obsługuje ścieżkę na stałej głębokości XY.")
        length = math.dist(a, b)
        if length <= 1e-9:
            continue
        if length >= left:
            entry = tuple(b[i] + (a[i] - b[i]) * left / length for i in range(3))
            tangent = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
            break
        tail.append(a)
        left -= length
    else:
        raise ResumeRefused("Historia jest krótsza niż wymagana zakładka.")
    tx, ty = tangent
    nx, ny = -ty, tx
    lead, radius = tool_d / 2, tool_d * radius_scale
    center = (entry[0] + side * nx * lead, entry[1] + side * ny * lead)
    h = (center[0] - tx * lead, center[1] - ty * lead)
    hc = (h[0] + tx * radius, h[1] + ty * radius)
    safe = max(stock_top, xyz[-1][2]) + settings.clearance
    turns = math.ceil((safe - entry[2]) / settings.pitch)
    if turns * 64 + len(tail) + 68 > 20000:
        raise ResumeRefused("Podgląd przekracza 20 000 punktów; zwiększ skok helisy.")
    points = [(*xyz[-1], "feed"), (xyz[-1][0], xyz[-1][1], safe, "rapid"),
              (*h, safe, "rapid")]
    angle = math.atan2(h[1] - hc[1], h[0] - hc[0])
    for k in range(1, turns * 64 + 1):
        fraction = k / (turns * 64)
        a = angle + side * math.tau * turns * fraction
        points.append((hc[0] + radius * math.cos(a), hc[1] + radius * math.sin(a),
                       safe + (entry[2] - safe) * fraction, "feed"))
    angle = math.atan2(h[1] - center[1], h[0] - center[0])
    for k in range(1, 65):
        a = angle + side * math.pi / 2 * k / 64
        points.append((center[0] + lead * math.cos(a), center[1] + lead * math.sin(a),
                       entry[2], "feed"))
    points += [(*p, "feed") for p in reversed(tail)]
    return ResumePlan(tuple(points), entry, tangent, overlap)
