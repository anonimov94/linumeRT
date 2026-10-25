"""Ścieżka programu do podglądu: ruchy z liniami źródła, strefy START/KONIEC i DTG.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

Model bez UI dla renderera skórki Classic × Neon. Ruch to polilinia w mm w układzie detalu
(łuki rozbite na odcinki), z numerem linii programu — tym samym, który LinuxCNC podaje
w `stat.motion_line`. Ruch pochodzi z interpretera LinuxCNC (`gcode.parse` i `PreviewCanon`);
moduł nie interpretuje G-code samodzielnie. `demo_toolpath()` buduje równolegle tekst programu
demonstracyjnego i jego ruchy, aby podgląd działał bez LinuxCNC.

Strefy: pierwsze i ostatnie `count` ruchów programu są wyróżniane w podglądzie.
Następny punkt to koniec bieżącego ruchu; DTG to długość pozostała do niego wzdłuż ścieżki.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
import os
import re
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .linuxcnc_check import InterpreterUnavailable

INCH = 25.4
ARC_STEP = math.pi / 24   # maks. kąt odcinka łuku [rad]
RAPID_FEED = 0.0          # G0: prędkość z limitów maszyny, nie z F


@dataclass(frozen=True, eq=False)
class Move:
    line: int              # linia programu (1 = pierwsza), jak stat.motion_line
    rapid: bool
    feed: float            # mm/min; 0 dla G0
    points: np.ndarray     # (n, 3) mm, points[0] = początek ruchu
    cum: np.ndarray        # (n,) długość od początku ruchu

    @property
    def length(self) -> float:
        return float(self.cum[-1])

    @property
    def end(self) -> np.ndarray:
        return self.points[-1]

    def at(self, s: float) -> np.ndarray:
        """Punkt w odległości `s` od początku ruchu (przycięte do [0, length])."""
        if s <= 0 or len(self.points) == 1:
            return self.points[0].copy()
        if s >= self.length:
            return self.points[-1].copy()
        i = int(np.searchsorted(self.cum, s))
        span = self.cum[i] - self.cum[i - 1]
        t = (s - self.cum[i - 1]) / span if span else 0.0
        return self.points[i - 1] + (self.points[i] - self.points[i - 1]) * t

    def project(self, pos: Sequence[float]) -> tuple[float, float]:
        """(s, odległość) najbliższego punktu ruchu do `pos`."""
        p = np.asarray(pos, dtype=float)
        if len(self.points) == 1:
            return 0.0, float(np.linalg.norm(p - self.points[0]))
        a, b = self.points[:-1], self.points[1:]
        d = b - a
        dd = np.einsum("ij,ij->i", d, d)
        t = np.where(dd > 0, np.einsum("ij,ij->i", p - a, d) / np.where(dd > 0, dd, 1), 0)
        t = np.clip(t, 0, 1)
        dist = np.linalg.norm(a + d * t[:, None] - p, axis=1)
        k = int(np.argmin(dist))
        return float(self.cum[k] + t[k] * math.sqrt(dd[k])), float(dist[k])


def make_move(line: int, rapid: bool, feed: float, points: Iterable[Sequence[float]]) -> Move:
    pts = np.asarray(list(points), dtype=float).reshape(-1, 3)
    if not np.all(np.isfinite(pts)):
        raise ValueError(f"linia {line}: współrzędne ruchu nie są skończone")
    steps = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate(([0.0], np.cumsum(steps)))
    return Move(int(line), bool(rapid), float(feed), pts, cum)


def arc_points(start: Sequence[float], end: Sequence[float], center: Sequence[float],
               rotation: int) -> np.ndarray:
    """Łuk w XY jak ARC_FEED: rotation > 0 = CCW (G3), < 0 = CW (G2), |rotation| = obroty."""
    if rotation == 0:
        raise ValueError("łuk bez kierunku (rotation = 0)")
    sx, sy, sz = start
    ex, ey, ez = end
    cx, cy = center
    r0 = math.hypot(sx - cx, sy - cy)
    r1 = math.hypot(ex - cx, ey - cy)
    a0 = math.atan2(sy - cy, sx - cx)
    a1 = math.atan2(ey - cy, ex - cx)
    sweep = (a1 - a0) % (2 * math.pi) if rotation > 0 else (a0 - a1) % (2 * math.pi)
    if sweep < 1e-9:
        sweep = 2 * math.pi                      # pełny okrąg: początek = koniec
    sweep = math.copysign(sweep + 2 * math.pi * (abs(int(rotation)) - 1), rotation)
    n = max(2, math.ceil(abs(sweep) / ARC_STEP))
    t = np.linspace(0.0, 1.0, n + 1)
    a = a0 + sweep * t
    r = r0 + (r1 - r0) * t
    pts = np.column_stack((cx + r * np.cos(a), cy + r * np.sin(a), sz + (ez - sz) * t))
    pts[-1] = (ex, ey, ez)
    return pts


class Toolpath:
    """Niezmienna lista ruchów programu z odległościami skumulowanymi."""

    def __init__(self, moves: Iterable[Move], source: Sequence[str] = (),
                 offset: Sequence[float] = (0.0, 0.0, 0.0), notes: Sequence[str] = ()):
        self.moves: tuple[Move, ...] = tuple(moves)
        self.source = tuple(source)                       # tekst programu (linie od 1)
        self.offset = np.asarray(offset, dtype=float)     # G5x + G92 [mm]: detal + offset = G53
        self.notes = tuple(notes)                         # uproszczenia podglądu, dla operatora
        lengths = [m.length for m in self.moves]
        self.cum = np.concatenate(([0.0], np.cumsum(lengths))) if lengths else np.zeros(1)

    def __len__(self) -> int:
        return len(self.moves)

    @property
    def length(self) -> float:
        return float(self.cum[-1])

    def zone(self, index: int, count: int) -> str:
        """'start' dla pierwszych `count` ruchów, 'end' dla ostatnich, inaczej 'mid'."""
        if index < count:
            return "start"
        if index >= len(self.moves) - count:
            return "end"
        return "mid"

    def position(self, index: int, s: float) -> np.ndarray:
        if not self.moves:
            return np.zeros(3)
        if index >= len(self.moves):
            return self.moves[-1].end.copy()
        return self.moves[index].at(s)

    def travelled(self, index: int, s: float) -> float:
        if index >= len(self.moves):
            return self.length
        return float(self.cum[index]) + min(max(s, 0.0), self.moves[index].length)

    def seek(self, distance: float) -> tuple[int, float]:
        """(ruch, s) dla drogi `distance` od początku; ruchy zerowe są przeskakiwane."""
        if not self.moves:
            return 0, 0.0
        d = min(max(distance, 0.0), self.length)
        i = int(np.searchsorted(self.cum, d, side="right")) - 1
        i = min(max(i, 0), len(self.moves))
        while i < len(self.moves) and self.moves[i].length == 0 and self.cum[i] <= d:
            i += 1
        if i >= len(self.moves):
            return len(self.moves), 0.0
        return i, d - float(self.cum[i])

    def dtg(self, index: int, s: float) -> float:
        """Droga pozostała do następnego punktu (końca ruchu `index`)."""
        if index >= len(self.moves):
            return 0.0
        return max(0.0, self.moves[index].length - s)

    def locate(self, line: int, pos: Sequence[float], hint: int = 0) -> tuple[int, float]:
        """Ruch i s dla linii z `stat.motion_line` i pozycji w układzie detalu.

        Kilka ruchów w jednej linii (łuk wieloobrotowy, cykl wiercenia, podprogram w pętli)
        rozstrzyga najbliższa geometria, a przy remisie pierwszy ruch nie wcześniejszy niż `hint`.
        Linia bez ruchu (np. M6) wskazuje następny ruch po niej.
        """
        if not self.moves:
            return 0, 0.0
        best = None
        for i, m in enumerate(self.moves):
            if m.line != line:
                continue
            s, dist = m.project(pos)
            key = (round(dist, 6), i < hint, i)
            if best is None or key < best[0]:
                best = (key, i, s)
        if best is not None:
            return best[1], best[2]
        for i, m in enumerate(self.moves):
            if m.line > line:
                return i, 0.0
        return len(self.moves), 0.0

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.moves:
            return np.zeros(3), np.zeros(3)
        pts = np.concatenate([m.points for m in self.moves])
        return pts.min(axis=0), pts.max(axis=0)

    def seconds(self, rapid_feed: float) -> np.ndarray:
        """Skumulowany czas [s] przy stałej prędkości (bez przyspieszeń), G0 z `rapid_feed`."""
        times = [m.length / ((m.feed if not m.rapid and m.feed > 0 else rapid_feed) / 60.0)
                 for m in self.moves]
        return np.concatenate(([0.0], np.cumsum(times)))


class PreviewCanon:
    """Odbiornik `gcode.parse` z LinuxCNC 2.9: zbiera ruchy z numerami linii.

    Interpreter przekazuje współrzędne programu w calach (jednostki wewnętrzne),
    bez G5x/G92 — tak jak podgląd LinuxCNC; offsety trafiają do `set_g5x_offset`.
    Łuki poza płaszczyzną G17 i obrót G10 L2 R są pokazywane uproszczenie (`notes`).
    Współrzędne i set_feed_rate z gcode 2.9 używają cali i cali/min;
    odbiornik przelicza je do mm oraz mm/min. Model-Author: Codex (weryfikacja N1).
    """

    def __init__(self, axis_mask: int = 0x7):
        self.moves: list[Move] = []
        self.notes: list[str] = []
        self.lineno = 0
        self.pos: np.ndarray | None = None
        self.feed = 0.0
        self.plane = 1
        self.g5x = np.zeros(3)
        self.g92 = np.zeros(3)
        self.axis_mask = axis_mask
        self.parameter_file = ""

    # --- zapytania interpretera ---
    def check_abort(self):
        return False

    def get_external_length_units(self):
        return 1 / INCH          # maszyna w mm

    def get_external_angular_units(self):
        return 1.0

    def get_axis_mask(self):
        return self.axis_mask

    def get_block_delete(self):
        return False

    def get_tool(self, tool):
        return (tool,) + (0.0,) * 12 + (0,)

    # --- stan ---
    def next_line(self, state):
        self.lineno = int(state.sequence_number)

    def set_plane(self, plane):
        self.plane = plane

    def set_feed_rate(self, rate):
        self.feed = rate * INCH

    def set_g5x_offset(self, index, x, y, z, *rest):
        self.g5x = np.array((x, y, z)) * INCH

    def set_g92_offset(self, x, y, z, *rest):
        self.g92 = np.array((x, y, z)) * INCH

    def set_xy_rotation(self, theta):
        if theta:
            self._note("Obrót układu (G10 L2 R) nie jest uwzględniony w podglądzie ścieżki.")

    def __getattr__(self, name):
        # Pozostałe wywołania (komentarze, wrzeciono, chłodziwo, M-funkcje) nie zmieniają ścieżki.
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None

    # --- ruch ---
    def _note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def _to(self, rapid, end, points=None):
        end = np.asarray(end, dtype=float) * INCH
        start = end if self.pos is None else self.pos
        pts = [start, end] if points is None else points
        self.moves.append(make_move(self.lineno, rapid, 0.0 if rapid else self.feed, pts))
        self.pos = end

    def straight_traverse(self, x, y, z, *rest):
        self._to(True, (x, y, z))

    def straight_feed(self, x, y, z, *rest):
        self._to(False, (x, y, z))

    straight_probe = straight_feed

    def rigid_tap(self, x, y, z, *rest):
        back = self.pos
        self._to(False, (x, y, z))
        if back is not None:
            self._to(False, back / INCH)

    def arc_feed(self, first_end, second_end, first_axis, second_axis, rotation,
                 axis_end_point, *rest):
        if self.plane != 1:
            self._note("Łuki G18/G19 są pokazywane jako odcinki prostej.")
            if self.plane == 2:    # XZ: (z, x, ..., y)
                end = (second_end, axis_end_point, first_end)
            else:                  # YZ: (y, z, ..., x)
                end = (axis_end_point, first_end, second_end)
            self._to(False, end)
            return
        end = np.array((first_end, second_end, axis_end_point)) * INCH
        start = end if self.pos is None else self.pos
        pts = arc_points(start, end, (first_axis * INCH, second_axis * INCH), int(rotation))
        self.moves.append(make_move(self.lineno, False, self.feed, pts))
        self.pos = end

    def toolpath(self, source: Sequence[str] = ()) -> Toolpath:
        return Toolpath(self.moves, source, self.g5x + self.g92, self.notes)


TOOL_MMAP = ".tool.mmap"
_COMMENT = re.compile(r"\([^)]*\)|;.*$")
_TOOL_WORDS = re.compile(
    r"(?<![A-Za-z0-9.])(?:[Tt]\s*(?:\d+|#<[^>]*>|#\d+|\[[^\]]*\])|[Mm]\s*0*6(?!\d))")
TOOL_SKIPPED_NOTE = "Zmiany narzędzi (T, M6) pominięte w podglądzie: LinuxCNC nie działa."


def tool_data_available() -> bool:
    """Czy interpreter może czytać dane narzędzi (LinuxCNC utworzył ~/.tool.mmap).

    `gcode.parse` bez zmapowanej tablicy narzędzi kończy się SIGSEGV przy słowie T/M6
    (tool_mmap_mutex_get; potwierdzone gdb na LinuxCNC 2.9).
    Mapowanie robi `linuxcnc.stat().poll()`.
    """
    if not (Path(os.environ.get("HOME", "/tmp")) / TOOL_MMAP).exists():
        return False
    try:
        import linuxcnc  # type: ignore[import-not-found]

        linuxcnc.stat().poll()    # to poll() woła tool_mmap_user() (libtooldata jest współdzielona)
    except Exception:  # noqa: BLE001 - brak NML/modułu = brak danych narzędzi
        return False
    return True


def strip_tool_words(text: str) -> tuple[str, bool]:
    """Wycina słowa T i M6 poza komentarzami; liczba i numeracja linii bez zmian."""
    changed = False
    out = []
    for line in text.splitlines(keepends=True):
        parts, last = [], 0
        for m in _COMMENT.finditer(line):
            parts.append(_TOOL_WORDS.sub("", line[last:m.start()]))
            parts.append(m.group(0))
            last = m.end()
        parts.append(_TOOL_WORDS.sub("", line[last:]))
        new = "".join(parts)
        changed = changed or new != line
        out.append(new)
    return "".join(out), changed


def load_ngc(path: Path | str, unitcode: str = "G21",
             initcode: str = "G17 G90 G94 G54") -> Toolpath:
    """Ścieżka z interpretera LinuxCNC (moduł `gcode`); bez LinuxCNC: InterpreterUnavailable.

    Bez działającego LinuxCNC (brak mapowania narzędzi) słowa T/M6 są wycinane z tymczasowej kopii
    (te same numery linii) i podgląd dostaje notatkę.
    """
    try:
        import gcode  # type: ignore[import-not-found]
    except ImportError as exc:
        raise InterpreterUnavailable("Brak modułu gcode z LinuxCNC 2.9.") from exc
    path = Path(path)
    source_text = path.read_text(encoding="utf-8", errors="replace")
    canon = PreviewCanon()
    skipped = False
    # gcode reads this attribute as a string, not a callback. Keep interpreter
    # parameter writes private to this analysis, away from the operator's state.
    with tempfile.TemporaryDirectory(prefix="linumert-preview-") as directory:
        var = Path(directory) / "preview.var"
        var.write_text("", encoding="utf-8")  # brak pliku: "link (updating variable file)"
        canon.parameter_file = str(var)
        parse_path = path
        if not tool_data_available():
            stripped, skipped = strip_tool_words(source_text)
            if skipped:
                parse_path = Path(directory) / path.name
                parse_path.write_text(stripped, encoding="utf-8")
        # Interpreter czyta INI z INI_FILE_NAME (REMAP, SUBROUTINE_PATH względem cwd): podgląd ma
        # być niezależny od katalogu uruchomienia, więc analizuje program bez INI maszyny.
        saved = os.environ.pop("INI_FILE_NAME", None)
        try:
            result, seq = gcode.parse(str(parse_path), canon, unitcode, initcode)
        finally:
            if saved is not None:
                os.environ["INI_FILE_NAME"] = saved
    if result > gcode.MIN_ERROR:
        raise ValueError(f"linia {seq}: {gcode.strerror(result)}")
    toolpath = canon.toolpath(source_text.splitlines())
    if skipped:
        toolpath.notes = (*toolpath.notes, TOOL_SKIPPED_NOTE)
    return toolpath


# --------------------------------------------------------------------------- program demo

DEMO_STOCK = (120.0, 80.0, 30.0)
DEMO_START = (-20.0, -20.0, 25.0)


class _DemoWriter:
    def __init__(self):
        self.text: list[str] = []
        self.moves: list[Move] = []
        self.pos = np.array(DEMO_START)
        self.feed = 0.0

    def meta(self, code):
        self.text.append(code)

    def _code(self, code):
        self.text.append(code)
        return len(self.text)

    def lin(self, g, x=None, y=None, z=None, f=None):
        end = np.array([self.pos[0] if x is None else x, self.pos[1] if y is None else y,
                        self.pos[2] if z is None else z], dtype=float)
        code = f"G{g}" + "".join(f" {a}{v:.3f}" for a, v, old in zip("XYZ", end, self.pos,
                                                                      strict=True) if v != old)
        if g == 1 and f and f != self.feed:
            code += f" F{f:g}"
            self.feed = f
        line = self._code(code)
        self.moves.append(make_move(line, g == 0, 0.0 if g == 0 else self.feed, [self.pos, end]))
        self.pos = end

    def arc(self, g, cx, cy, ex, ey, ez, f=None, full=False):
        end = np.array((ex, ey, ez))
        code = f"G{g} X{ex:.3f} Y{ey:.3f}" + (f" Z{ez:.3f}" if ez != self.pos[2] else "")
        code += f" I{cx - self.pos[0]:.3f} J{cy - self.pos[1]:.3f}"
        if f and f != self.feed:
            code += f" F{f:g}"
            self.feed = f
        line = self._code(code)
        pts = arc_points(self.pos, end, (cx, cy), 1 if g == 3 else -1)
        self.moves.append(make_move(line, False, self.feed, pts))
        self.pos = end


def demo_toolpath() -> Toolpath:
    """Program demonstracyjny Classic × Neon: kieszeń, helisa, kontur R10, wiercenie."""
    w = _DemoWriter()
    w.meta("(linumeRT - KORPUS NEON - 120x80x30)")
    w.meta(";@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54")
    w.meta("G21 G90 G54 G17 G40 G49 G94")
    w.meta("T1 M6 (FREZ PALCOWY D6)")
    w.meta("S12000 M3")
    w.meta("M8")
    w.meta(f"G0 X{DEMO_START[0]:.3f} Y{DEMO_START[1]:.3f} Z{DEMO_START[2]:.3f}")
    w.lin(0, 10, 10)
    w.lin(0, z=5)
    for depth in (-3, -6):
        w.meta(f"(KIESZEN Z{depth})")
        w.lin(0, 49, 39)
        w.lin(0, z=2)
        w.lin(1, z=depth, f=300)
        for k in range(4, -1, -1):
            x0, x1, y0, y1 = 33 + 4 * k, 87 - 4 * k, 23 + 4 * k, 57 - 4 * k
            w.lin(1, x0, y0, f=1200)
            w.lin(1, x1, y0)
            w.lin(1, x1, y1)
            w.lin(1, x0, y1)
            w.lin(1, x0, y0)
        w.lin(0, z=5)
    w.meta("(OTWOR HELIKALNY D20)")
    w.lin(0, 67, 40)
    w.lin(0, z=2)
    w.lin(1, z=-6, f=300)
    w.arc(2, 60, 40, 67, 40, -9, f=600)
    w.arc(2, 60, 40, 67, 40, -12)
    w.arc(2, 60, 40, 67, 40, -12)
    w.lin(1, 60, 40)
    w.lin(0, z=5)
    w.meta("(KONTUR ZEWNETRZNY R10 Z-8)")
    w.lin(0, -6, 13)
    w.lin(1, z=-8, f=300)
    w.lin(1, 3, 13, f=1000)
    w.arc(3, 13, 13, 13, 3, -8)
    w.lin(1, 107, 3)
    w.arc(3, 107, 13, 117, 13, -8)
    w.lin(1, 117, 67)
    w.arc(3, 107, 67, 107, 77, -8)
    w.lin(1, 13, 77)
    w.arc(3, 13, 67, 3, 67, -8)
    w.lin(1, 3, 13)
    w.lin(1, -6, 13)
    w.lin(0, z=5)
    w.meta("(WIERCENIE 4x)")
    for hx, hy in ((15, 15), (105, 15), (105, 65), (15, 65)):
        w.lin(0, hx, hy)
        w.lin(0, z=2)
        w.lin(1, z=-14, f=250)
        w.lin(0, z=2)
    w.lin(0, z=25)
    w.lin(0, -20, 100)
    w.meta("M9")
    w.meta("M5")
    w.meta("M30")
    return Toolpath(w.moves, w.text)
