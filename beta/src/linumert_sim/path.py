"""Ścieżka z programu: lista ruchów (MoveList) do podglądu i symulacji (sesja 051).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

Dwa źródła ruchów, ten sam wynik:
- `PathCanon` — odbiornik `gcode.parse` z LinuxCNC 2.9 (interpreter rs274: o-word, korekcja,
  pełne cykle); używany zawsze, gdy moduł `gcode` jest dostępny;
- `SubsetInterpreter` — zapasowy interpreter podzbioru G-code dla CI i maszyn bez LinuxCNC:
  G0/G1/G2/G3 (płaszczyzny G17/G18/G19, IJK lub R, linia śrubowa), G20/G21, G90/G91, G90.1/G91.1,
  F, T…M6, G81/G82/G83/G73 z G98/G99 i Q, G80. Czego nie zna (o-word call, korekcja G41/G42,
  G28/G30, G53, układy G5x), zapisuje w `notes` i pomija, zamiast zgadywać.

Współrzędne w mm w układzie programu (bez G5x/G92, jak podgląd LinuxCNC). Łuki rozbite na
cięciwy z błędem ≤ `CHORD_TOL` (0,01 mm). Numer linii = linia pliku (1 = pierwsza), jak
`stat.motion_line`. Ruch nie jest pozycją maszyny ani dowodem bezkolizyjności.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
import re
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

INCH = 25.4
CHORD_TOL = 0.01            # [mm] maks. odległość cięciwy od łuku
KIND_RAPID, KIND_FEED, KIND_ARC = 0, 1, 2
KIND_NAMES = ("G0", "G1", "łuk")
PECK_CLEARANCE = 0.010 * INCH   # [mm] odstęp nad dnem po wycofaniu w G73/G83 (LinuxCNC)


class InterpreterUnavailable(RuntimeError):
    """Brak modułu `gcode` z LinuxCNC."""


# --------------------------------------------------------------------------- MoveList

@dataclass(frozen=True, eq=False)
class MoveList:
    """Odcinki ścieżki w tablicach: start/end (n, 3) float32 [mm], line/tool int32,
    kind int8 (0 G0, 1 G1, 2 cięciwa łuku), feed float32 [mm/min] (0 dla G0), spindle float32
    [obr/min] ze znakiem (> 0 M3, < 0 M4, 0 stoi)."""

    start: np.ndarray
    end: np.ndarray
    line: np.ndarray
    tool: np.ndarray
    kind: np.ndarray
    feed: np.ndarray
    spindle: np.ndarray
    notes: tuple[str, ...] = ()
    source: str = "subset"          # "rs274" albo "subset"

    def __len__(self) -> int:
        return len(self.line)

    @property
    def lengths(self) -> np.ndarray:
        return np.linalg.norm(self.end.astype(float) - self.start.astype(float), axis=1)

    def length(self, kind: int | None = None) -> float:
        lengths = self.lengths
        return float(lengths.sum() if kind is None else lengths[self.kind == kind].sum())

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        if not len(self):
            return np.zeros(3), np.zeros(3)
        pts = np.vstack((self.start, self.end)).astype(float)
        return pts.min(axis=0), pts.max(axis=0)

    def lines(self) -> np.ndarray:
        """Numery linii programu, które dają ruch (rosnąco, bez powtórzeń)."""
        return np.unique(self.line)

    def segments_of(self, line: int) -> np.ndarray:
        return np.flatnonzero(self.line == line)

    def points(self) -> np.ndarray:
        """Polilinia: start pierwszego odcinka i końce kolejnych (n + 1, 3)."""
        if not len(self):
            return np.zeros((0, 3), dtype=np.float32)
        return np.vstack((self.start[:1], self.end))


class MoveListBuilder:
    def __init__(self):
        self._rows: list[tuple] = []
        self.notes: list[str] = []

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def add(self, start, end, line: int, tool: int, kind: int, feed: float,
            spindle: float = 0.0) -> None:
        if not (np.all(np.isfinite(start)) and np.all(np.isfinite(end))):
            raise ValueError(f"linia {line}: współrzędne ruchu nie są skończone")
        self._rows.append((tuple(start), tuple(end), line, tool, kind, feed, spindle))

    def add_polyline(self, pts: np.ndarray, line: int, tool: int, kind: int,
                     feed: float, spindle: float = 0.0) -> None:
        for a, b in zip(pts[:-1], pts[1:], strict=True):
            self.add(a, b, line, tool, kind, feed, spindle)

    def build(self, source: str) -> MoveList:
        n = len(self._rows)
        start = np.zeros((n, 3), dtype=np.float32)
        end = np.zeros((n, 3), dtype=np.float32)
        line = np.zeros(n, dtype=np.int32)
        tool = np.zeros(n, dtype=np.int32)
        kind = np.zeros(n, dtype=np.int8)
        feed = np.zeros(n, dtype=np.float32)
        spindle = np.zeros(n, dtype=np.float32)
        for i, (s, e, ln, t, k, f, sp) in enumerate(self._rows):
            start[i], end[i], line[i], tool[i], kind[i], feed[i], spindle[i] = (
                s, e, ln, t, k, f, sp)
        return MoveList(start, end, line, tool, kind, feed, spindle, tuple(self.notes), source)


# --------------------------------------------------------------------------- łuki

def chord_count(radius: float, sweep: float, tol: float = CHORD_TOL) -> int:
    """Liczba cięciw łuku o promieniu `radius` i kącie `sweep` z błędem ≤ `tol`."""
    if radius <= tol:
        return 1
    max_angle = 2.0 * math.acos(1.0 - tol / radius)
    return max(1, math.ceil(abs(sweep) / max_angle - 1e-9))


def arc_points(start: Sequence[float], end: Sequence[float], center: Sequence[float],
               rotation: int, axes: tuple[int, int, int] = (0, 1, 2),
               tol: float = CHORD_TOL) -> np.ndarray:
    """Punkty łuku (z linią śrubową) w płaszczyźnie `axes` = (oś 1, oś 2, oś liniowa).

    rotation > 0 = CCW patrząc od dodatniej osi liniowej (G3), < 0 = CW (G2), |rotation| = obroty.
    `center` = (oś 1, oś 2). Promień może się zmieniać liniowo (koniec z tolerancją interpretera).
    """
    if rotation == 0:
        raise ValueError("łuk bez kierunku (rotation = 0)")
    a1, a2, ax = axes
    s, e = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    c1, c2 = center
    r0 = math.hypot(s[a1] - c1, s[a2] - c2)
    r1 = math.hypot(e[a1] - c1, e[a2] - c2)
    t0 = math.atan2(s[a2] - c2, s[a1] - c1)
    t1 = math.atan2(e[a2] - c2, e[a1] - c1)
    sweep = (t1 - t0) % math.tau if rotation > 0 else (t0 - t1) % math.tau
    if sweep < 1e-9:
        sweep = math.tau                       # pełny okrąg: początek = koniec
    sweep = math.copysign(sweep + math.tau * (abs(int(rotation)) - 1), rotation)
    n = chord_count(max(r0, r1), sweep, tol)
    t = np.linspace(0.0, 1.0, n + 1)
    ang = t0 + sweep * t
    r = r0 + (r1 - r0) * t
    pts = np.repeat(s[None, :], n + 1, axis=0)
    pts[:, a1] = c1 + r * np.cos(ang)
    pts[:, a2] = c2 + r * np.sin(ang)
    pts[:, ax] = s[ax] + (e[ax] - s[ax]) * t
    pts[-1] = e
    return pts


PLANE_AXES = {1: (0, 1, 2), 2: (2, 0, 1), 3: (1, 2, 0)}   # G17 XY, G18 ZX, G19 YZ


# --------------------------------------------------------------------------- rs274 (LinuxCNC)

class PathCanon:
    """Odbiornik `gcode.parse` z LinuxCNC 2.9 → MoveList.

    Interpreter podaje współrzędne w calach (jednostki wewnętrzne), bez G5x/G92; offsety
    trafiają do `set_g5x_offset`/`set_g92_offset` i są tylko zapamiętywane (`offset`).
    """

    # gcodemodule czyta ten atrybut jako tekst; bez niego __getattr__ zwraca funkcję
    # i parse() kończy się TypeError. parse_rs274 ustawia plik w katalogu tymczasowym.
    parameter_file = ""

    def __init__(self, axis_mask: int = 0x7):
        self.out = MoveListBuilder()
        self.lineno = 0
        self.pos: np.ndarray | None = None
        self.feed = 0.0
        self.plane = 1
        self.tool = 0
        self.pending_tool = 0
        self.rpm = 0.0
        self.g5x = np.zeros(3)
        self.g92 = np.zeros(3)
        self.axis_mask = axis_mask

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
        # Stan modalny wrzeciona (M3/M4/M5) i S z interpretera; gcodemodule nie woła
        # osobnych metod wrzeciona.
        direction = {3: 1.0, 4: -1.0}.get(int(getattr(state, "spindle", 5)), 0.0)
        self.rpm = direction * float(getattr(state, "speed", 0.0))

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
            self.out.note("Obrót układu (G10 L2 R) nie jest uwzględniony w ścieżce.")

    def select_tool(self, tool, *rest):
        self.pending_tool = int(tool)

    def change_tool(self, *rest):
        self.tool = self.pending_tool

    def __getattr__(self, name):
        # Pozostałe wywołania (komentarze, wrzeciono, chłodziwo, M-funkcje) nie zmieniają ścieżki.
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None

    @property
    def offset(self) -> np.ndarray:
        return self.g5x + self.g92

    # --- ruch ---
    def _to(self, kind, end):
        end = np.asarray(end, dtype=float) * INCH
        start = end if self.pos is None else self.pos
        self.out.add(start, end, self.lineno, self.tool, kind,
                     0.0 if kind == KIND_RAPID else self.feed, self.rpm)
        self.pos = end

    def straight_traverse(self, x, y, z, *rest):
        self._to(KIND_RAPID, (x, y, z))

    def straight_feed(self, x, y, z, *rest):
        self._to(KIND_FEED, (x, y, z))

    straight_probe = straight_feed

    def rigid_tap(self, x, y, z, *rest):
        back = self.pos
        self._to(KIND_FEED, (x, y, z))
        if back is not None:
            self._to(KIND_FEED, back / INCH)

    def arc_feed(self, first_end, second_end, first_axis, second_axis, rotation,
                 axis_end_point, *rest):
        a1, a2, ax = PLANE_AXES.get(self.plane, PLANE_AXES[1])
        end = np.zeros(3)
        end[a1], end[a2], end[ax] = first_end, second_end, axis_end_point
        end *= INCH
        start = end if self.pos is None else self.pos
        pts = arc_points(start, end, (first_axis * INCH, second_axis * INCH), int(rotation),
                         (a1, a2, ax))
        self.out.add_polyline(pts, self.lineno, self.tool, KIND_ARC, self.feed, self.rpm)
        self.pos = end

    def movelist(self) -> MoveList:
        return self.out.build("rs274")


def parse_rs274(path: Path | str, unitcode: str = "G21",
                initcode: str = "G17 G90 G94 G54") -> MoveList:
    """Ścieżka z interpretera LinuxCNC; bez LinuxCNC: InterpreterUnavailable."""
    try:
        import gcode  # type: ignore[import-not-found]
    except ImportError as exc:
        raise InterpreterUnavailable("Brak modułu gcode z LinuxCNC 2.9.") from exc
    canon = PathCanon()
    # Zapisy parametrów interpretera zostają w analizie, z dala od stanu operatora
    # (jak load_ngc po poprawce N1 Codex, PR #123).
    with tempfile.TemporaryDirectory(prefix="linumert-path-") as directory:
        canon.parameter_file = str(Path(directory) / "path.var")
        result, seq = gcode.parse(str(path), canon, unitcode, initcode)
    if result > gcode.MIN_ERROR:
        raise ValueError(f"linia {seq}: {gcode.strerror(result)}")
    return canon.movelist()


# --------------------------------------------------------------------------- podzbiór (CI)

_COMMENT = re.compile(r"\([^)]*\)")
_WORD = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
_OWORD = re.compile(r"^O\s*(<[^>]*>|\d+)\s*(\w+)", re.IGNORECASE)
MOTION = {"0", "1", "2", "3", "73", "81", "82", "83"}
IGNORED_G = {"4", "17.1", "18.1", "19.1", "43", "43.1", "49", "54", "55", "56", "57", "58",
             "59", "59.1", "59.2", "59.3", "61", "61.1", "64", "93", "94", "95", "96", "97",
             "40"}


@dataclass
class _State:
    pos: np.ndarray = field(default_factory=lambda: np.zeros(3))
    motion: str | None = None
    absolute: bool = True
    arc_absolute: bool = False
    scale: float = 1.0
    feed: float = 0.0
    plane: int = 1
    tool: int = 0
    pending_tool: int = 0
    speed: float = 0.0
    direction: float = 0.0
    retract: str = "98"
    cycle_initial_z: float | None = None
    cycle: dict = field(default_factory=dict)


class SubsetInterpreter:
    """Zapasowy interpreter podzbioru G-code (opis w nagłówku modułu)."""

    def __init__(self, start: Sequence[float] = (0.0, 0.0, 0.0), metric: bool = True):
        self.s = _State(pos=np.asarray(start, dtype=float), scale=1.0 if metric else INCH)
        self.out = MoveListBuilder()
        self.ended = False

    def run(self, lines: Iterable[str]) -> MoveList:
        skip_sub = None
        for number, raw in enumerate(lines, start=1):
            if self.ended:
                break
            text = _COMMENT.sub("", raw.split(";", 1)[0]).strip().upper()
            if not text or text.startswith("%"):
                continue
            oword = _OWORD.match(text)
            if oword:
                name, keyword = oword.group(1), oword.group(2).lower()
                if skip_sub is None and keyword == "sub":
                    skip_sub = name
                elif skip_sub == name and keyword == "endsub":
                    skip_sub = None
                elif skip_sub is None:
                    self.out.note(f"Linia {number}: o-word {keyword} pominięte "
                                  "(tylko interpreter LinuxCNC).")
                continue
            if skip_sub is None:
                self._block(number, text)
        return self.out.build("subset")

    # --- blok ---
    def _block(self, number: int, text: str) -> None:
        s = self.s
        words = [(k, v) for k, v in _WORD.findall(text.replace(" ", ""))]
        g = [_norm(v) for k, v in words if k == "G"]
        m = [_norm(v) for k, v in words if k == "M"]
        val = {k: float(v) for k, v in words if k not in "GMNO"}
        skip = False
        for code in g:
            if code == "20":
                s.scale = INCH
            elif code == "21":
                s.scale = 1.0
            elif code == "90":
                s.absolute = True
            elif code == "91":
                s.absolute = False
            elif code == "90.1":
                s.arc_absolute = True
            elif code == "91.1":
                s.arc_absolute = False
            elif code in ("17", "18", "19"):
                s.plane = int(code) - 16
            elif code in ("98", "99"):
                s.retract = code
            elif code == "80":
                s.motion, s.cycle, s.cycle_initial_z = None, {}, None
            elif code in ("41", "42", "41.1", "42.1"):
                self.out.note(f"Linia {number}: korekcja promienia G{code} pominięta — tor środka "
                              "narzędzia bez korekcji (pełny tor: interpreter LinuxCNC).")
            elif code in ("28", "30", "53", "92", "10"):
                self.out.note(f"Linia {number}: G{code} pominięte w ścieżce.")
                skip = True
            elif code in MOTION:
                if code in ("73", "81", "82", "83") and s.motion != code:
                    s.cycle_initial_z = None
                s.motion = code
            elif code not in IGNORED_G:
                self.out.note(f"Linia {number}: G{code} nieobsługiwane — pominięte.")
                skip = True
        if "F" in val:
            s.feed = val["F"] * s.scale
        if "T" in val:
            s.pending_tool = int(val["T"])
        if "6" in m:
            s.tool = s.pending_tool
        if "S" in val:
            s.speed = val["S"]
        for code, direction in (("3", 1.0), ("4", -1.0), ("5", 0.0)):
            if code in m:
                s.direction = direction
        if not skip and (any(k in val for k in "XYZ") or (s.motion in ("2", "3") and any(
                k in val for k in "IJKR"))):
            self._motion(number, val)
        if "2" in m or "30" in m:
            self.ended = True

    @property
    def rpm(self) -> float:
        return self.s.direction * self.s.speed

    def _target(self, val: dict) -> np.ndarray:
        s = self.s
        end = s.pos.copy()
        for i, axis in enumerate("XYZ"):
            if axis in val:
                v = val[axis] * s.scale
                end[i] = v if s.absolute else end[i] + v
        return end

    def _motion(self, number: int, val: dict) -> None:
        s = self.s
        if s.motion is None:
            self.out.note(f"Linia {number}: współrzędne bez trybu ruchu — pominięte.")
            return
        if s.motion in ("73", "81", "82", "83"):
            self._cycle(number, val)
            return
        end = self._target(val)
        if s.motion in ("0", "1"):
            kind = KIND_RAPID if s.motion == "0" else KIND_FEED
            self.out.add(s.pos, end, number, s.tool, kind,
                         0.0 if kind == KIND_RAPID else s.feed, self.rpm)
        else:
            a1, a2, ax = PLANE_AXES[s.plane]
            center = self._center(number, val, end, (a1, a2))
            turns = int(val.get("P", 1))
            rotation = turns if s.motion == "3" else -turns
            pts = arc_points(s.pos, end, center, rotation, (a1, a2, ax))
            self.out.add_polyline(pts, number, s.tool, KIND_ARC, s.feed, self.rpm)
        s.pos = end

    def _center(self, number, val, end, axes) -> tuple[float, float]:
        s = self.s
        a1, a2 = axes
        letters = "IJK"
        if "R" in val:
            r = val["R"] * s.scale
            p, q = s.pos[[a1, a2]], end[[a1, a2]]
            d = float(np.linalg.norm(q - p))
            if d < 1e-12 or d > 2 * abs(r) + 1e-6:
                raise ValueError(f"linia {number}: łuk R — promień {abs(r):g} za mały")
            h = math.sqrt(max(r * r - d * d / 4.0, 0.0))
            mid = (p + q) / 2.0
            perp = np.array((-(q - p)[1], (q - p)[0])) / d
            # G2 z R > 0: krótszy łuk (środek po prawej), R < 0: dłuższy; G3 odwrotnie.
            side = 1.0 if (s.motion == "3") == (r > 0) else -1.0
            c = mid + side * h * perp
            return float(c[0]), float(c[1])
        off = []
        for axis in (a1, a2):
            key = letters[axis]
            v = val.get(key, 0.0) * s.scale
            off.append(v if s.arc_absolute else s.pos[axis] + v)
        return off[0], off[1]

    def _cycle(self, number: int, val: dict) -> None:
        """G81/G82/G83/G73 jak LinuxCNC: G0 do XY, G0 do R, wiercenie, wycofanie G98/G99."""
        s = self.s
        if s.plane != 1:
            self.out.note(f"Linia {number}: cykl wiercenia poza G17 pominięty.")
            return
        cyc = s.cycle
        for key in "ZRQ":
            if key in val:
                cyc[key] = val[key] * s.scale
        if "R" not in cyc or "Z" not in cyc:
            raise ValueError(f"linia {number}: cykl G{s.motion} bez R lub Z")
        if s.cycle_initial_z is None:
            s.cycle_initial_z = float(s.pos[2])
        r, bottom = cyc["R"], cyc["Z"]
        if not s.absolute:
            self.out.note(f"Linia {number}: cykl w G91 — R i Z traktowane jak w G90.")
        xy = s.pos.copy()
        for i, axis in enumerate("XY"):
            if axis in val:
                v = val[axis] * s.scale
                xy[i] = v if s.absolute else xy[i] + v

        def go(kind, point):
            point = np.asarray(point, dtype=float)
            self.out.add(s.pos, point, number, s.tool, kind,
                         0.0 if kind == KIND_RAPID else s.feed, self.rpm)
            s.pos = point

        if s.pos[2] < r:
            go(KIND_RAPID, (s.pos[0], s.pos[1], r))
        go(KIND_RAPID, (xy[0], xy[1], s.pos[2]))
        go(KIND_RAPID, (xy[0], xy[1], r))
        q = cyc.get("Q", 0.0)
        if s.motion in ("83", "73") and q > 0:
            depth = r
            while depth > bottom + 1e-9:
                target = max(bottom, depth - q)
                go(KIND_FEED, (xy[0], xy[1], target))
                if target > bottom:
                    if s.motion == "83":           # pełne wycofanie do R i powrót nad dno
                        go(KIND_RAPID, (xy[0], xy[1], r))
                    go(KIND_RAPID, (xy[0], xy[1], target + PECK_CLEARANCE))
                depth = target
        else:
            go(KIND_FEED, (xy[0], xy[1], bottom))
        # G98: do Z początkowego (nie niżej niż R), G99: do R.
        clear = max(s.cycle_initial_z, r) if s.retract == "98" else r
        go(KIND_RAPID, (xy[0], xy[1], clear))


def _norm(value: str) -> str:
    """'01' → '1', '91.10' → '91.1'."""
    f = float(value)
    return str(int(f)) if f == int(f) else f"{f:g}"


def parse_subset(text: str | Sequence[str], start: Sequence[float] = (0.0, 0.0, 0.0),
                 metric: bool = True) -> MoveList:
    lines = text.splitlines() if isinstance(text, str) else list(text)
    return SubsetInterpreter(start, metric).run(lines)


def load_path(path: Path | str, prefer: str = "auto") -> MoveList:
    """MoveList z pliku: `auto` = rs274, gdy dostępny, inaczej podzbiór; `rs274`; `subset`."""
    if prefer not in ("auto", "rs274", "subset"):
        raise ValueError(f"nieznane źródło ścieżki: {prefer}")
    if prefer != "subset":
        try:
            return parse_rs274(path)
        except InterpreterUnavailable:
            if prefer == "rs274":
                raise
    return parse_subset(Path(path).read_text(encoding="utf-8", errors="replace"))
