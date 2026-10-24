"""Generatory konturowe: rowki, czopy i kontur z korekcją promienia (sesja 043).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

- `slot_linear` — rowek prosty między dwoma punktami (szerokość ≥ D: przejście po osi + obwiednie).
- `slot_arc` — rowek łukowy wokół środka (promień osi, kąt początkowy, rozwarcie).
- `stud_rect`, `stud_circle` — czop (wysepka) obrabiany z zewnątrz, od marginesu do ściany.
- `contour` — kontur z odcinków i łuków (tekst), opcjonalna korekcja G41.1/G42.1 z D frezu,
  styczny dojazd i odjazd; nieciągłość = P-5010 z numerem segmentu.

Ścieżki to tor środka narzędzia (poza `contour` z korekcją, gdzie LinuxCNC przesuwa tor sam).
Łuki jako G2/G3 z I/J przyrostowymi (G91.1). Wejście w materiał: zagłębienie pionowe albo rampa
po osi rowka. UWAGA: przed obróbką sprawdzić w symulacji LinuxCNC/Plant.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
import re

from .base import BaseMacroGenerator, Field, Issue, Polyline, fmt

EPS = 0.001
MAX_BLOCKS = 20000

COMMON = (
    Field("z_top", "float", "Powierzchnia Z", "mm", default=0.0),
    Field("depth", "float", "Głębokość", "mm", minimum=0.0001, maximum=100),
    Field("step_down", "float", "Krok Z", "mm", default=1.0, minimum=0.0001),
    Field("tool_d", "float", "Średnica frezu", "mm", minimum=0.001),
    Field("feed", "float", "Posuw", "mm/min", default=400.0, minimum=0, exclusive_minimum=True),
    Field("plunge", "float", "Posuw zagłębiania", "mm/min", default=100.0, minimum=0,
          exclusive_minimum=True),
    Field("safe_z", "float", "Bezpieczna Z", "mm", default=5.0),
)
STEPOVER = Field("stepover", "float", "Krok boczny", "% D", default=50.0, minimum=5, maximum=90)
ENTRY = (Field("entry", "choice", "Wejście", default="plunge", choices=("plunge", "ramp")),
         Field("entry_angle", "float", "Kąt rampy", "°", default=3.0, minimum=0.1, maximum=15.0))

# Ścieżka: [(x, y, None, None)] start, potem (x, y, środek|None, ccw) — tor środka narzędzia.


def _levels(v):
    count = math.ceil(v["depth"] / v["step_down"] - 1e-9)
    return [v["z_top"] - min(v["depth"], k * v["step_down"]) for k in range(1, count + 1)]


def _common_check(v) -> list[Issue]:
    issues = []
    if round(v["safe_z"], 4) <= round(v["z_top"], 4):
        issues.append(Issue("P-5003", {"name": "safe_z", "value": fmt(v["safe_z"]),
                                      "limit": f"> {fmt(v['z_top'])}"}, "safe_z"))
    return issues


def _blocks(v, per_layer: int) -> list[Issue]:
    blocks = len(_levels(v)) * per_layer
    if blocks > MAX_BLOCKS:
        return [Issue("P-5003", {"name": "liczba bloków", "value": str(blocks),
                                "limit": f"<= {MAX_BLOCKS}"}, "step_down")]
    return []


def _offsets(total: float, stride: float) -> list[float]:
    """0 < o_1 < … < o_n = total co najwyżej co `stride` (pusta lista dla total ≈ 0)."""
    if total <= EPS:
        return []
    count = max(1, math.ceil(total / stride - 1e-9))
    return [total * k / count for k in range(1, count + 1)]


def _emit(path, feed: float) -> list[str]:
    lines = []
    px, py = path[0][:2]
    for x, y, center, ccw in path[1:]:
        if center is None:
            lines.append(f"G1 X{fmt(x)} Y{fmt(y)} F{fmt(feed)}")
        else:
            lines.append(f"{'G3' if ccw else 'G2'} X{fmt(x)} Y{fmt(y)} "
                         f"I{fmt(center[0] - px)} J{fmt(center[1] - py)} F{fmt(feed)}")
        px, py = x, y
    return lines


def _arc_samples(start, end, center, ccw, n=48):
    r = math.hypot(start[0] - center[0], start[1] - center[1])
    a = math.atan2(start[1] - center[1], start[0] - center[0])
    b = math.atan2(end[1] - center[1], end[0] - center[0])
    sign = 1 if ccw else -1
    sweep = ((sign * (b - a)) % math.tau or math.tau) * sign
    return [(center[0] + r * math.cos(a + sweep * k / n),
             center[1] + r * math.sin(a + sweep * k / n)) for k in range(1, n + 1)]


def _preview(path) -> Polyline:
    points = [tuple(path[0][:2])]
    for x, y, center, ccw in path[1:]:
        if center is None:
            points.append((x, y))
        else:
            points.extend(_arc_samples(points[-1], (x, y), center, ccw))
    return points


def _reverse(path):
    """Ta sama ścieżka w przeciwnym kierunku (łuki zmieniają kierunek)."""
    out = [(path[-1][0], path[-1][1], None, None)]
    for i in range(len(path) - 1, 0, -1):
        _x, _y, center, ccw = path[i]
        out.append((path[i - 1][0], path[i - 1][1], center, None if center is None else not ccw))
    return out


def _ramp(v, start_z, z, centerline) -> list[str]:
    """Rampa tam i z powrotem po osi rowka (`centerline` = jeden ruch od punktu wejścia)."""
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) if b[2] is None else
                 abs(_sweep(a, b)) * math.hypot(a[0] - b[2][0], a[1] - b[2][1])
                 for a, b in zip(centerline, centerline[1:], strict=False))
    drop = length * math.tan(math.radians(v["entry_angle"]))
    passes = max(1, math.ceil((start_z - z) / drop - 1e-9))
    lines, forward = [], True
    for k in range(1, passes + 1):
        target = start_z + (z - start_z) * k / passes
        path = centerline if forward else _reverse(centerline)
        moves = _emit(path, v["plunge"])
        moves[-1] = moves[-1].replace(" F", f" Z{fmt(target)} F", 1)
        lines += moves
        forward = not forward
    if not forward:                     # wróć do punktu wejścia na pełnej głębokości
        lines += _emit(_reverse(centerline), v["feed"])
    return lines


def _sweep(a, b) -> float:
    center, ccw = b[2], b[3]
    s = math.atan2(a[1] - center[1], a[0] - center[0])
    e = math.atan2(b[1] - center[1], b[0] - center[0])
    sign = 1 if ccw else -1
    return ((sign * (e - s)) % math.tau or math.tau) * sign


class _Layered(BaseMacroGenerator):
    """Wspólny przebieg warstw: wejście w punkcie startu, ścieżki, powrót do startu."""

    comment = ""          # nazwa w komentarzu G-code (ASCII)

    def _passes(self, v) -> list[list]:
        raise NotImplementedError

    def _entry_line(self, v):
        """Ścieżka do rampy (od punktu wejścia) albo None."""
        return None

    def generate(self, v):
        passes = self._passes(v)
        start = passes[0][0]
        lines = [f"( {self.comment}: tor srodka narzedzia, symulacja wymagana )",
                 "G17 G90 G91.1 G94 G40 G80", f"G0 Z{fmt(v['safe_z'])}",
                 f"G0 X{fmt(start[0])} Y{fmt(start[1])}"]
        top = v["z_top"]
        lines.append(f"G0 Z{fmt(top + min(1.0, v['safe_z'] - top))}")
        for z in _levels(v):
            ramp = self._entry_line(v) if v.get("entry") == "ramp" else None
            if ramp is not None:
                lines.append(f"G1 Z{fmt(top)} F{fmt(v['plunge'])}")
                lines += _ramp(v, top, z, ramp)
            else:
                lines.append(f"G1 Z{fmt(z)} F{fmt(v['plunge'])}")
            position = start
            for path in passes:
                if (path[0][0], path[0][1]) != (position[0], position[1]):
                    lines.append(f"G1 X{fmt(path[0][0])} Y{fmt(path[0][1])} F{fmt(v['feed'])}")
                lines += _emit(path, v["feed"])
                position = path[-1]
            if (position[0], position[1]) != (start[0], start[1]):
                lines += self._back_to_start(v, position, start)
            top = z
        return lines + [f"G0 Z{fmt(v['safe_z'])}"]

    def _back_to_start(self, v, position, start):
        return [f"G1 X{fmt(start[0])} Y{fmt(start[1])} F{fmt(v['feed'])}"]

    def preview_2d(self, v):
        return [_preview(p) for p in self._passes(v)]


# --------------------------------------------------------------------------- rowki

class SlotLinear(_Layered):
    name = "slot_linear"
    version = 1
    title = "Rowek prosty"
    comment = "Rowek prosty"
    fields = COMMON + (STEPOVER,) + ENTRY + (
        Field("x1", "float", "Początek X", "mm", default=0.0),
        Field("y1", "float", "Początek Y", "mm", default=0.0),
        Field("x2", "float", "Koniec X", "mm"),
        Field("y2", "float", "Koniec Y", "mm", default=0.0),
        Field("width", "float", "Szerokość rowka", "mm", minimum=0.001, maximum=1000),
        Field("direction", "choice", "Kierunek obwiedni", default="ccw", choices=("ccw", "cw")),
    )

    def check(self, v, step):
        issues = _common_check(v)
        length = math.hypot(v["x2"] - v["x1"], v["y2"] - v["y1"])
        if length < EPS:
            issues.append(Issue("P-5003", {"name": "długość rowka", "value": fmt(length),
                                          "limit": f">= {fmt(EPS)}"}, "x2"))
        if v["width"] < v["tool_d"] - 1e-9:
            issues.append(Issue("P-5007", {"tool": 0, "what": "frez szerszy niż rowek"}, "tool_d"))
        if not issues:
            issues += _blocks(v, 6 * len(self._passes(v)) + 40)
        return issues

    def _geometry(self, v):
        p1, p2 = (v["x1"], v["y1"]), (v["x2"], v["y2"])
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        u = ((p2[0] - p1[0]) / length, (p2[1] - p1[1]) / length)
        return p1, p2, u, (-u[1], u[0])

    def _passes(self, v):
        p1, p2, _u, n = self._geometry(v)
        out = [[(p1[0], p1[1], None, None), (p2[0], p2[1], None, None)]]
        stride = v["tool_d"] * v["stepover"] / 100
        for h in _offsets((v["width"] - v["tool_d"]) / 2, stride):
            a = (p1[0] - n[0] * h, p1[1] - n[1] * h)
            b = (p2[0] - n[0] * h, p2[1] - n[1] * h)
            c = (p2[0] + n[0] * h, p2[1] + n[1] * h)
            d = (p1[0] + n[0] * h, p1[1] + n[1] * h)
            ring = [(a[0], a[1], None, None), (b[0], b[1], None, None), (c[0], c[1], p2, True),
                    (d[0], d[1], None, None), (a[0], a[1], p1, True)]
            out.append(ring if v["direction"] == "ccw" else _reverse(ring))
        return out

    def _entry_line(self, v):
        p1, p2, _u, _n = self._geometry(v)
        return [(p1[0], p1[1], None, None), (p2[0], p2[1], None, None)]


class SlotArc(_Layered):
    name = "slot_arc"
    version = 1
    title = "Rowek łukowy"
    comment = "Rowek lukowy"
    fields = COMMON + (STEPOVER,) + ENTRY + (
        Field("cx", "float", "Środek X", "mm", default=0.0),
        Field("cy", "float", "Środek Y", "mm", default=0.0),
        Field("radius", "float", "Promień osi rowka", "mm", minimum=0.001, maximum=5000),
        Field("start_angle", "float", "Kąt początkowy", "°", default=0.0, minimum=-360,
              maximum=360),
        Field("sweep", "float", "Rozwarcie (CCW)", "°", minimum=0.1, maximum=359.9),
        Field("width", "float", "Szerokość rowka", "mm", minimum=0.001, maximum=1000),
    )

    def check(self, v, step):
        issues = _common_check(v)
        if v["width"] < v["tool_d"] - 1e-9:
            issues.append(Issue("P-5007", {"tool": 0, "what": "frez szerszy niż rowek"}, "tool_d"))
        inner = v["radius"] - (v["width"] - v["tool_d"]) / 2
        if inner < EPS:
            issues.append(Issue("P-5003", {"name": "radius", "value": fmt(v["radius"]),
                                          "limit": f"> {fmt((v['width'] - v['tool_d']) / 2)}"},
                                "radius"))
        if not issues:
            issues += _blocks(v, 6 * len(self._passes(v)) + 40)
        return issues

    def _point(self, v, r, angle):
        a = math.radians(angle)
        return (v["cx"] + r * math.cos(a), v["cy"] + r * math.sin(a))

    def _passes(self, v):
        a0, a1, c = v["start_angle"], v["start_angle"] + v["sweep"], (v["cx"], v["cy"])
        s, e = self._point(v, v["radius"], a0), self._point(v, v["radius"], a1)
        # Oś tam i z powrotem: powrót po łuku, nigdy po cięciwie (cięciwa wychodzi z rowka).
        out = [[(s[0], s[1], None, None), (e[0], e[1], c, True), (s[0], s[1], c, False)]]
        stride = v["tool_d"] * v["stepover"] / 100
        for h in _offsets((v["width"] - v["tool_d"]) / 2, stride):
            o0, o1 = self._point(v, v["radius"] + h, a0), self._point(v, v["radius"] + h, a1)
            i0, i1 = self._point(v, v["radius"] - h, a0), self._point(v, v["radius"] - h, a1)
            out.append([(o0[0], o0[1], None, None), (o1[0], o1[1], c, True),
                        (i1[0], i1[1], e, True), (i0[0], i0[1], c, False),
                        (o0[0], o0[1], s, True)])
        return out

    def _back_to_start(self, v, position, start):
        # Ostatnia obwiednia kończy się na zewnętrznym końcu przy kącie startu: promieniowo do osi.
        return [f"G1 X{fmt(start[0])} Y{fmt(start[1])} F{fmt(v['feed'])}"]

    def _entry_line(self, v):
        return self._passes(v)[0][:2]


# --------------------------------------------------------------------------- czopy

STUD = COMMON + (STEPOVER,) + (
    Field("cx", "float", "Środek X", "mm", default=0.0),
    Field("cy", "float", "Środek Y", "mm", default=0.0),
    Field("margin", "float", "Margines materiału wokół czopu", "mm", default=5.0, minimum=0,
          maximum=1000),
    Field("wall_allowance", "float", "Naddatek ściany", "mm", default=0.0, minimum=0),
    Field("milling", "choice", "Frezowanie", default="climb", choices=("climb", "conventional")),
)


class _Stud(_Layered):
    def _ring(self, v, offset):
        raise NotImplementedError

    def _passes(self, v):
        # Od zewnętrznego marginesu do ściany: pierwsza ścieżka najdalej od czopu.
        base = v["tool_d"] / 2 + v["wall_allowance"]
        stride = v["tool_d"] * v["stepover"] / 100
        extra = [v["margin"] - o for o in [0.0] + _offsets(v["margin"], stride)]
        out = []
        for o in sorted(set(round(e, 6) for e in extra), reverse=True):
            ring = self._ring(v, base + max(0.0, o))
            # Z zewnątrz przy M3: współbieżne = zgodnie z ruchem wskazówek zegara (CW).
            out.append(_reverse(ring) if v["milling"] == "climb" else ring)
        return out

    def _back_to_start(self, v, position, start):
        # Ostatni pierścień kończy się przy ścianie; na zewnątrz po normalnej do punktu wejścia.
        return [f"G1 X{fmt(start[0])} Y{fmt(start[1])} F{fmt(v['feed'])}"]

    def check(self, v, step):
        issues = _common_check(v)
        if not issues:
            issues += _blocks(v, 8 * len(self._passes(v)) + 20)
        return issues


class StudRect(_Stud):
    name = "stud_rect"
    version = 1
    title = "Czop prostokątny"
    comment = "Czop prostokatny"
    fields = STUD + (
        Field("width", "float", "Szerokość X", "mm", minimum=0.001, maximum=10000),
        Field("height", "float", "Długość Y", "mm", minimum=0.001, maximum=10000),
        Field("corner_radius", "float", "Promień naroża czopu", "mm", default=0.0, minimum=0),
        Field("rotation", "float", "Obrót XY", "°", default=0.0, minimum=-360, maximum=360),
    )

    def check(self, v, step):
        issues = super().check(v, step)
        if v["corner_radius"] > min(v["width"], v["height"]) / 2 + 1e-9:
            issues.append(Issue("P-5003", {"name": "corner_radius",
                                          "value": fmt(v["corner_radius"]),
                                          "limit": "<= min(X, Y)/2"}, "corner_radius"))
        return issues

    def _ring(self, v, offset):
        hx, hy = v["width"] / 2, v["height"] / 2
        r = v["corner_radius"]
        # Zewnętrzny offset prostokąta o promieniu r: odcinki przesunięte, naroża o promieniu r+o.
        ax, ay, ro = hx - r, hy - r, r + offset
        a = math.radians(v["rotation"])
        ca, sa = math.cos(a), math.sin(a)

        def p(x, y):
            return (v["cx"] + ca * x - sa * y, v["cy"] + sa * x + ca * y)

        pts = [((ax, -ay - ro), None), ((ax + ro, -ay), (ax, -ay)), ((ax + ro, ay), None),
               ((ax, ay + ro), (ax, ay)), ((-ax, ay + ro), None), ((-ax - ro, ay), (-ax, ay)),
               ((-ax - ro, -ay), None), ((-ax, -ay - ro), (-ax, -ay))]
        start = p(-ax, -ay - ro)
        ring = [(start[0], start[1], None, None)]
        for (x, y), center in pts:
            q = p(x, y)
            if ring[-1][:2] == q and center is None:
                continue
            ring.append((q[0], q[1], None if center is None else p(*center),
                         None if center is None else True))
        return ring


class StudCircle(_Stud):
    name = "stud_circle"
    version = 1
    title = "Czop okrągły"
    comment = "Czop okragly"
    fields = STUD + (Field("diameter", "float", "Średnica czopu", "mm", minimum=0.001,
                           maximum=10000),)

    def _ring(self, v, offset):
        r = v["diameter"] / 2 + offset
        s = (v["cx"] + r, v["cy"])
        return [(s[0], s[1], None, None), (s[0], s[1], (v["cx"], v["cy"]), True)]


# --------------------------------------------------------------------------- kontur

_NUM = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
_PT = rf"({_NUM})\s*,\s*({_NUM})"
_LINE = re.compile(rf"^\s*L\s+{_PT}\s+{_PT}\s*$", re.I)
_ARC = re.compile(rf"^\s*A\s+{_PT}\s+{_PT}\s+{_PT}\s+(CW|CCW)\s*$", re.I)


def parse_segments(text: str):
    """„L x0,y0 x1,y1; A x0,y0 x1,y1 cx,cy CCW; …” → [(start, end, środek|None, ccw)].

    ValueError z numerem segmentu przy błędnym zapisie.
    """
    out = []
    for i, part in enumerate(p for p in re.split(r"[;\n]", text) if p.strip()):
        m = _LINE.match(part)
        if m:
            g = [float(x) for x in m.groups()]
            out.append(((g[0], g[1]), (g[2], g[3]), None, None))
            continue
        m = _ARC.match(part)
        if m:
            g = [float(x) for x in m.groups()[:6]]
            out.append(((g[0], g[1]), (g[2], g[3]), (g[4], g[5]), m.group(7).upper() == "CCW"))
            continue
        raise ValueError(f"segment {i + 1}: oczekiwano „L x,y x,y” albo „A x,y x,y cx,cy CW|CCW”")
    return out


def _tangent(segment, at_end: bool):
    start, end, center, ccw = segment
    if center is None:
        d = (end[0] - start[0], end[1] - start[1])
    else:
        p = end if at_end else start
        r = (p[0] - center[0], p[1] - center[1])
        d = (-r[1], r[0]) if ccw else (r[1], -r[0])
    n = math.hypot(*d)
    return (d[0] / n, d[1] / n)


class Contour(BaseMacroGenerator):
    name = "contour"
    version = 1
    title = "Kontur"
    fields = COMMON + (
        Field("segments", "text", "Segmenty (L x,y x,y; A x,y x,y cx,cy CW|CCW)"),
        Field("compensation", "choice", "Korekcja promienia", default="none",
              choices=("none", "left", "right")),
        Field("lead", "float", "Dojazd/odjazd styczny", "mm", default=5.0, minimum=0),
    )

    def check(self, v, step):
        issues = _common_check(v)
        try:
            segments = parse_segments(v["segments"])
        except ValueError as exc:
            return issues + [Issue("P-5015", {"step": step, "field": "segments",
                                             "expected": str(exc)}, "segments")]
        if not segments:
            return issues + [Issue("P-5014", {"step": step, "field": "segments"}, "segments")]
        for k, (start, end, center, _ccw) in enumerate(segments, start=1):
            if k > 1:
                gap = math.dist(segments[k - 2][1], start)
                if gap > EPS:
                    issues.append(Issue("P-5010", {"segment": k, "gap": fmt(gap, 3)}, "segments"))
            if center is None and math.dist(start, end) < EPS:
                issues.append(Issue("P-5003", {"name": f"długość segmentu {k}", "value": "0",
                                              "limit": f">= {fmt(EPS)}"}, "segments"))
            if center is not None:
                r0, r1 = math.dist(start, center), math.dist(end, center)
                if r0 < EPS or abs(r0 - r1) > EPS:
                    issues.append(Issue("P-5003", {"name": f"promień łuku segmentu {k}",
                                                  "value": f"{fmt(r0, 3)}/{fmt(r1, 3)}",
                                                  "limit": "równe promienie początku i końca"},
                                        "segments"))
        if v["compensation"] != "none" and v["lead"] <= v["tool_d"] / 2 + EPS:
            # LinuxCNC: ruch wejścia z korekcją musi być dłuższy niż promień narzędzia.
            issues.append(Issue("P-5003", {"name": "lead", "value": fmt(v["lead"]),
                                          "limit": f"> {fmt(v['tool_d'] / 2 + EPS)} (D/2)"},
                                "lead"))
        if not issues:
            issues += _blocks(v, len(segments) + 10)
        return issues

    def _path(self, v):
        segments = parse_segments(v["segments"])
        t0, t1 = _tangent(segments[0], False), _tangent(segments[-1], True)
        s, e = segments[0][0], segments[-1][1]
        lead_in = (s[0] - t0[0] * v["lead"], s[1] - t0[1] * v["lead"])
        lead_out = (e[0] + t1[0] * v["lead"], e[1] + t1[1] * v["lead"])
        path = [(s[0], s[1], None, None)] + [(b[0], b[1], c, ccw) for _a, b, c, ccw in segments]
        return lead_in, path, lead_out

    def generate(self, v):
        lead_in, path, lead_out = self._path(v)
        comp = {"none": None, "left": "G41.1", "right": "G42.1"}[v["compensation"]]
        lines = ["( Kontur: korekcja " + v["compensation"] + ", symulacja wymagana )",
                 "G17 G90 G91.1 G94 G40 G80", f"G0 Z{fmt(v['safe_z'])}"]
        for z in _levels(v):
            lines += [f"G0 X{fmt(lead_in[0])} Y{fmt(lead_in[1])}",
                      f"G1 Z{fmt(z)} F{fmt(v['plunge'])}"]
            if comp:
                lines.append(f"{comp} D{fmt(v['tool_d'])}")
            lines.append(f"G1 X{fmt(path[0][0])} Y{fmt(path[0][1])} F{fmt(v['feed'])}")
            lines += _emit(path, v["feed"])
            if v["lead"] > 0:
                lines.append(f"G1 X{fmt(lead_out[0])} Y{fmt(lead_out[1])} F{fmt(v['feed'])}")
            if comp:
                lines.append("G40")
            lines.append(f"G0 Z{fmt(v['safe_z'])}")
        return lines

    def preview_2d(self, v):
        lead_in, path, lead_out = self._path(v)
        contour = _preview(path)
        return [[lead_in, contour[0]], contour, [contour[-1], lead_out]]


def register(registry=None) -> None:
    from .registry import DEFAULT_REGISTRY

    registry = registry or DEFAULT_REGISTRY
    for cls in (SlotLinear, SlotArc, StudRect, StudCircle, Contour):
        if registry.get(cls.name, cls.version) is None:
            registry.register(cls)
