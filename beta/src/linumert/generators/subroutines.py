"""Generatory jako podprogramy LinuxCNC `o<lrt_...>` (sesja 048).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-20

Każdy podprogram to osobny plik `<nazwa>.ngc` (nazwa pliku = nazwa podprogramu) do katalogu
z `[RS274NGC]SUBROUTINE_PATH`, zwykle `~/linuxcnc/nc_files/user_macros/`. Nagłówek w układzie
NgcGui (zakładka NgcGui w QtDragon): pierwsza linia `(info: ...)`, potem po jednej linii na
parametr `#<nazwa> = #n (=domyślna opis)`. Ruch jest ten sam co w generatorach Pythona
(`FaceMill`, `DrillHoles`, `PocketRect`, `PocketCircle`, `SlotLinear`) — sprawdza to test
porównujący wyjście interpretera rs274.
Wywołanie: `o<lrt_face_mill> call [0] [0] [100] [50] ...` (docs/user/PODPROGRAMY.md).
Teksty w ASCII (NgcGui i starsze edytory). Tylko tekst G-code (CLAUDE.md §6, §8).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Param:
    name: str
    default: float
    label: str


@dataclass(frozen=True)
class Subroutine:
    name: str
    info: str
    params: tuple[Param, ...]
    body: str
    generator: str

    def text(self) -> str:
        head = [f"(info: {self.info})", f"o<{self.name}> sub"]
        for i, p in enumerate(self.params, start=1):
            head.append(f"#<{p.name}> = #{i} (={_num(p.default)} {p.label})")
        return "\n".join(head) + "\n" + self.body.strip("\n") + f"\no<{self.name}> endsub\n"

    def call(self, **values: float) -> str:
        """Linia wywołania z parametrami w kolejności nagłówka (brakujące = domyślne)."""
        unknown = set(values) - {p.name for p in self.params}
        if unknown:
            raise ValueError(f"{self.name}: nieznane parametry {sorted(unknown)}")
        args = " ".join(f"[{_num(values.get(p.name, p.default))}]" for p in self.params)
        return f"o<{self.name}> call {args}"


def _num(value: float) -> str:
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


FACE_MILL = Subroutine(
    "lrt_face_mill", "linumeRT planowanie zygzakiem lub jednokierunkowo, generator face_mill v1",
    (Param("x0", 0, "X min"), Param("y0", 0, "Y min"), Param("x1", 100, "X max"),
     Param("y1", 50, "Y max"), Param("z_top", 0, "Z powierzchni"),
     Param("depth", 1, "glebokosc calkowita"), Param("step_down", 1, "glebokosc przejscia"),
     Param("tool_d", 10, "srednica narzedzia"), Param("stepover", 70, "krok boczny proc. D"),
     Param("overrun", 2, "wybieg poza krawedz"), Param("one_way", 0, "1 = jednokierunkowo"),
     Param("feed", 800, "posuw F"), Param("plunge", 200, "posuw wglebny"),
     Param("safe_z", 5, "bezpieczna Z")),
    """
o100 if [#<x1> LE #<x0> OR #<y1> LE #<y0> OR #<depth> LE 0 OR #<step_down> LE 0 OR #<tool_d> LE 0]
  (abort, lrt_face_mill: niepoprawne wymiary)
o100 endif
o101 if [#<safe_z> LE #<z_top>]
  (abort, lrt_face_mill: bezpieczna Z musi byc nad powierzchnia)
o101 endif
#<step> = [#<tool_d> * #<stepover> / 100]
#<xa> = [#<x0> - #<tool_d> / 2 - #<overrun>]
#<xb> = [#<x1> + #<tool_d> / 2 + #<overrun>]
#<n> = [FUP[[#<y1> - #<y0>] / #<step>] + 1]
#<layers> = FUP[#<depth> / #<step_down> - 0.000000001]
o102 if [#<layers> LT 1]
  #<layers> = 1
o102 endif
#<k> = 1
o110 while [#<k> LE #<layers>]
  #<z> = [#<z_top> - #<k> * #<step_down>]
  o111 if [#<z> LT #<z_top> - #<depth>]
    #<z> = [#<z_top> - #<depth>]
  o111 endif
  #<i> = 0
  o120 while [#<i> LT #<n>]
    #<y> = [#<y0> + #<i> * #<step>]
    o121 if [#<y> GT #<y1>]
      #<y> = #<y1>
    o121 endif
    #<xs> = #<xa>
    #<xe> = #<xb>
    o122 if [#<one_way> EQ 0 AND [#<i> MOD 2] EQ 1]
      #<xs> = #<xb>
      #<xe> = #<xa>
    o122 endif
    o123 if [#<i> EQ 0 OR #<one_way> NE 0]
      G0 Z#<safe_z>
      G0 X#<xs> Y#<y>
      G1 Z#<z> F#<plunge>
    o123 else
      G1 Y#<y> F#<feed>
    o123 endif
    G1 X#<xe> F#<feed>
    #<i> = [#<i> + 1]
  o120 endwhile
  #<k> = [#<k> + 1]
o110 endwhile
G0 Z#<safe_z>
""", "face_mill")

_DRILL_PARAMS = (
    Param("cycle", 81, "cykl 81 82 83 73"), Param("z_top", 0, "Z powierzchni"),
    Param("depth", 5, "glebokosc"), Param("r_plane", 2, "plaszczyzna R nad powierzchnia"),
    Param("peck", 2, "krok Q dla 83 i 73"), Param("dwell", 0.5, "postoj P dla 82 s"),
    Param("feed", 100, "posuw F"), Param("retract", 98, "powrot 98 lub 99"))

_DRILL_HOLE = """
  o210 if [#<cycle> EQ 81]
    G81 X#<px> Y#<py> Z#<zb> R#<r> F#<feed>
  o210 elseif [#<cycle> EQ 82]
    G82 X#<px> Y#<py> Z#<zb> R#<r> P#<dwell> F#<feed>
  o210 elseif [#<cycle> EQ 83]
    G83 X#<px> Y#<py> Z#<zb> R#<r> Q#<peck> F#<feed>
  o210 else
    G73 X#<px> Y#<py> Z#<zb> R#<r> Q#<peck> F#<feed>
  o210 endif
"""

_DRILL_HEAD = """
o200 if [#<cycle> NE 81 AND #<cycle> NE 82 AND #<cycle> NE 83 AND #<cycle> NE 73]
  (abort, lrt_drill: cykl musi byc 81, 82, 83 albo 73)
o200 endif
o201 if [#<depth> LE 0]
  (abort, lrt_drill: glebokosc musi byc dodatnia)
o201 endif
#<zb> = [#<z_top> - #<depth>]
#<r> = [#<z_top> + #<r_plane>]
G90
G0 Z#<r>
o202 if [#<retract> EQ 99]
  G99
o202 else
  G98
o202 endif
"""

DRILL_GRID = Subroutine(
    "lrt_drill_grid", "linumeRT otwory w siatce lub rzedzie, generator drill_holes v1",
    (Param("x", 0, "X pierwszego otworu"), Param("y", 0, "Y pierwszego otworu"),
     Param("count", 3, "otworow w rzedzie"), Param("rows", 1, "rzedow"),
     Param("dx", 10, "krok X"), Param("dy", 10, "krok Y")) + _DRILL_PARAMS,
    _DRILL_HEAD + """
#<j> = 0
o220 while [#<j> LT #<rows>]
  #<i> = 0
  o221 while [#<i> LT #<count>]
    #<px> = [#<x> + #<i> * #<dx>]
    #<py> = [#<y> + #<j> * #<dy>]
""" + _DRILL_HOLE.replace("\n  ", "\n      ") + """
    #<i> = [#<i> + 1]
  o221 endwhile
  #<j> = [#<j> + 1]
o220 endwhile
G80
""", "drill_holes")

DRILL_CIRCLE = Subroutine(
    "lrt_drill_circle", "linumeRT otwory na okregu lub luku, generator drill_holes v1",
    (Param("x", 0, "X srodka"), Param("y", 0, "Y srodka"), Param("radius", 20, "promien"),
     Param("count", 6, "liczba otworow"), Param("angle", 0, "kat pierwszego otworu"),
     Param("sweep", 360, "zakres 360 = pelny okrag")) + _DRILL_PARAMS,
    _DRILL_HEAD + """
o230 if [#<count> LT 2]
  (abort, lrt_drill_circle: co najmniej 2 otwory)
o230 endif
o231 if [ABS[#<sweep>] GE 360]
  #<da> = [360 / #<count>]
o231 else
  #<da> = [#<sweep> / [#<count> - 1]]
o231 endif
#<i> = 0
o240 while [#<i> LT #<count>]
  #<px> = [#<x> + #<radius> * COS[#<angle> + #<i> * #<da>]]
  #<py> = [#<y> + #<radius> * SIN[#<angle> + #<i> * #<da>]]
""" + _DRILL_HOLE.replace("\n  ", "\n    ") + """
  #<i> = [#<i> + 1]
o240 endwhile
G80
""", "drill_holes")

# ---- kieszenie i rowki (Claude, 2026-10-24) -----------------------------------------------
# Ruch jak w generatorach `pocket_rect` v2, `pocket_circle` v2 (wejście pionowe, bez naddatków
# i wykańczania) oraz `slot_linear` v1. Zgodność ruchu: tests/test_subroutines.py (rs274).

_POCKET_COMMON = (
    Param("z_top", 0, "Z powierzchni"), Param("depth", 2, "glebokosc"),
    Param("step_down", 1, "krok Z"), Param("tool_d", 8, "srednica frezu"),
    Param("stepover", 50, "krok boczny proc. D"), Param("feed", 400, "posuw F"),
    Param("plunge", 100, "posuw wglebny"), Param("safe_z", 5, "bezpieczna Z"),
    Param("ccw", 1, "1 = CCW G3, 0 = CW G2"))

_LAYER_LOOP = """
#<layers> = FUP[#<depth> / #<step_down>]
#<k> = 1
o{n}0 while [#<k> LE #<layers>]
  #<z> = [#<z_top> - #<k> * #<step_down>]
  o{n}1 if [#<z> LT #<z_top> - #<depth>]
    #<z> = [#<z_top> - #<depth>]
  o{n}1 endif
"""


def _guard(n: int, name: str, condition: str, text: str) -> str:
    return f"o{n} if [{condition}]\n  (abort, {name}: {text})\no{n} endif\n"


POCKET_CIRCLE = Subroutine(
    "lrt_pocket_circle", "linumeRT kieszen okragla, wejscie pionowe, generator pocket_circle v2",
    (Param("cx", 0, "X srodka"), Param("cy", 0, "Y srodka"), Param("diameter", 40, "srednica"))
    + _POCKET_COMMON,
    _guard(400, "lrt_pocket_circle", "#<depth> LE 0 OR #<step_down> LE 0 OR #<tool_d> LE 0",
           "niepoprawne wymiary")
    + _guard(401, "lrt_pocket_circle", "#<diameter> LE #<tool_d>", "frez nie miesci sie")
    + _guard(402, "lrt_pocket_circle", "#<safe_z> LE #<z_top>",
             "bezpieczna Z musi byc nad powierzchnia") + """
#<rmax> = [[#<diameter> - #<tool_d>] / 2]
#<stride> = [#<tool_d> * #<stepover> / 100]
#<rings> = FUP[#<rmax> / #<stride>]
o403 if [#<rings> LT 1]
  #<rings> = 1
o403 endif
G17 G90 G91.1 G94 G40 G80
""" + _LAYER_LOOP.format(n=41) + """
  G0 Z#<safe_z>
  G0 X#<cx> Y#<cy>
  G1 Z#<z> F#<plunge>
  #<i> = 1
  o420 while [#<i> LE #<rings>]
    #<r> = [#<i> * #<stride>]
    o421 if [#<r> GT #<rmax>]
      #<r> = #<rmax>
    o421 endif
    G1 X[#<cx> + #<r>] Y#<cy> F#<feed>
    o422 if [#<ccw> NE 0]
      G3 X[#<cx> + #<r>] Y#<cy> I[0 - #<r>] J0 F#<feed>
    o422 else
      G2 X[#<cx> + #<r>] Y#<cy> I[0 - #<r>] J0 F#<feed>
    o422 endif
    #<i> = [#<i> + 1]
  o420 endwhile
  #<k> = [#<k> + 1]
o410 endwhile
G0 Z#<safe_z>
""", "pocket_circle")


def _rect_point(name: str, x: str, y: str) -> str:
    """#<name_x>, #<name_y> = obrót (x, y) o #<rot> + środek (jak `pockets._point`)."""
    return (f"    #<{name}x> = [#<cx> + #<ca> * [{x}] - #<sa> * [{y}]]\n"
            f"    #<{name}y> = [#<cy> + #<sa> * [{x}] + #<ca> * [{y}]]\n")


def _rect_moves(points, label: int) -> str:
    """Ruchy ringu: punkty (nazwa, x, y, środek|None, łuk) — G1 z pominięciem zerowych odcinków."""
    out = []
    prev = None
    for k, (name, x, y, center, arc) in enumerate(points):
        out.append(_rect_point(name, x, y))
        if center is None:
            if prev is None:
                out.append(f"    G1 X#<{name}x> Y#<{name}y> F#<feed>\n")
            else:
                n = label * 10 + k
                out.append(f"    o{n} if [ABS[#<{name}x> - #<{prev}x>] GT 0.00001 OR "
                           f"ABS[#<{name}y> - #<{prev}y>] GT 0.00001]\n"
                           f"      G1 X#<{name}x> Y#<{name}y> F#<feed>\n    o{n} endif\n")
        else:
            cx, cy = center
            out.append(f"    #<di> = [[{cx}] - [{_local(prev, 'x', points)}]]\n"
                       f"    #<dj> = [[{cy}] - [{_local(prev, 'y', points)}]]\n"
                       f"    {arc} X#<{name}x> Y#<{name}y> I[#<ca> * #<di> - #<sa> * #<dj>] "
                       f"J[#<sa> * #<di> + #<ca> * #<dj>] F#<feed>\n")
        prev = name
    return "".join(out)


def _local(name, axis, points):
    for n, x, y, _c, _a in points:
        if n == name:
            return x if axis == "x" else y
    raise KeyError(name)


# Lokalne punkty ringu (jak `pockets._rect_path`), #<hx> #<hy> #<rr> bieżącego ringu.
_P = {0: ("0 - #<hx> + #<rr>", "0 - #<hy>"), 1: ("#<hx> - #<rr>", "0 - #<hy>"),
      2: ("#<hx>", "0 - #<hy> + #<rr>"), 3: ("#<hx>", "#<hy> - #<rr>"),
      4: ("#<hx> - #<rr>", "#<hy>"), 5: ("0 - #<hx> + #<rr>", "#<hy>"),
      6: ("0 - #<hx>", "#<hy> - #<rr>"), 7: ("0 - #<hx>", "0 - #<hy> + #<rr>"),
      8: ("0 - #<hx> + #<rr>", "0 - #<hy>")}
_C = {2: ("#<hx> - #<rr>", "0 - #<hy> + #<rr>"), 4: ("#<hx> - #<rr>", "#<hy> - #<rr>"),
      6: ("0 - #<hx> + #<rr>", "#<hy> - #<rr>"), 8: ("0 - #<hx> + #<rr>", "0 - #<hy> + #<rr>")}
_CCW = [(f"p{i}", *_P[i], _C.get(i), "G3") for i in range(9)]
_CW = [("q0", *_P[0], None, None)] + [
    (f"q{9 - i}", *_P[i - 1], _C.get(i), "G2") for i in range(8, 0, -1)]
_SQ = {0: ("0 - #<hx>", "0 - #<hy>"), 1: ("#<hx>", "0 - #<hy>"), 2: ("#<hx>", "#<hy>"),
       3: ("0 - #<hx>", "#<hy>"), 4: ("0 - #<hx>", "0 - #<hy>")}
_SQ_CCW = [(f"s{i}", *_SQ[i], None, None) for i in range(5)]
_SQ_CW = [("t0", *_SQ[0], None, None)] + [(f"t{5 - i}", *_SQ[i - 1], None, None)
                                          for i in range(4, 0, -1)]

POCKET_RECT = Subroutine(
    "lrt_pocket_rect", "linumeRT kieszen prostokatna, wejscie pionowe, generator pocket_rect v2",
    (Param("cx", 0, "X srodka"), Param("cy", 0, "Y srodka"), Param("width", 40, "szerokosc X"),
     Param("height", 30, "dlugosc Y"), Param("rotation", 0, "obrot XY stopnie"),
     Param("corner_radius", 0, "promien naroza 0 = D/2")) + _POCKET_COMMON,
    _guard(500, "lrt_pocket_rect", "#<depth> LE 0 OR #<step_down> LE 0 OR #<tool_d> LE 0",
           "niepoprawne wymiary")
    + _guard(501, "lrt_pocket_rect", "#<width> LE #<tool_d> OR #<height> LE #<tool_d>",
             "frez nie miesci sie")
    + _guard(502, "lrt_pocket_rect", "#<safe_z> LE #<z_top>",
             "bezpieczna Z musi byc nad powierzchnia") + """
#<ca> = COS[#<rotation>]
#<sa> = SIN[#<rotation>]
#<radius> = #<corner_radius>
o503 if [#<radius> EQ 0]
  #<radius> = [#<tool_d> / 2]
o503 endif
o504 if [#<radius> LT #<tool_d> / 2 OR #<radius> GT #<width> / 2 OR #<radius> GT #<height> / 2]
  (abort, lrt_pocket_rect: promien naroza poza zakresem D/2 ... min[X,Y]/2)
o504 endif
#<r> = [#<radius> - #<tool_d> / 2]
#<hxm> = [[#<width> - #<tool_d>] / 2]
#<hym> = [[#<height> - #<tool_d>] / 2]
#<stride> = [#<tool_d> * #<stepover> / [100 * SQRT[2]]]
#<hbig> = #<hxm>
o506 if [#<hym> GT #<hxm>]
  #<hbig> = #<hym>
o506 endif
#<rings> = FUP[#<hbig> / #<stride>]
o505 if [#<rings> LT 1]
  #<rings> = 1
o505 endif
G17 G90 G91.1 G94 G40 G80
""" + _LAYER_LOOP.format(n=51) + """
  G0 Z#<safe_z>
  G0 X#<cx> Y#<cy>
  G1 Z#<z> F#<plunge>
  #<i> = 1
  o520 while [#<i> LE #<rings>]
    #<hx> = [#<i> * #<stride>]
    o524 if [#<hx> GT #<hxm>]
      #<hx> = #<hxm>
    o524 endif
    #<hy> = [#<i> * #<stride>]
    o525 if [#<hy> GT #<hym>]
      #<hy> = #<hym>
    o525 endif
    #<rr> = #<r>
    o526 if [#<hx> LT #<rr>]
      #<rr> = #<hx>
    o526 endif
    o527 if [#<hy> LT #<rr>]
      #<rr> = #<hy>
    o527 endif
    o521 if [#<rr> LE 0]
      o522 if [#<ccw> NE 0]
""" + _rect_moves(_SQ_CCW, 53) + """      o522 else
""" + _rect_moves(_SQ_CW, 54) + """      o522 endif
    o521 else
      o523 if [#<ccw> NE 0]
""" + _rect_moves(_CCW, 55) + """      o523 else
""" + _rect_moves(_CW, 56) + """      o523 endif
    o521 endif
    #<i> = [#<i> + 1]
  o520 endwhile
  #<k> = [#<k> + 1]
o510 endwhile
G0 Z#<safe_z>
""", "pocket_rect")

SLOT_LINEAR = Subroutine(
    "lrt_slot_linear", "linumeRT rowek prosty, wejscie pionowe, generator slot_linear v1",
    (Param("x1", 0, "X poczatku"), Param("y1", 0, "Y poczatku"), Param("x2", 50, "X konca"),
     Param("y2", 0, "Y konca"), Param("width", 10, "szerokosc rowka")) + _POCKET_COMMON,
    _guard(300, "lrt_slot_linear", "#<depth> LE 0 OR #<step_down> LE 0 OR #<tool_d> LE 0",
           "niepoprawne wymiary")
    + _guard(301, "lrt_slot_linear", "#<width> LT #<tool_d>", "frez szerszy niz rowek")
    + _guard(302, "lrt_slot_linear", "#<safe_z> LE #<z_top>",
             "bezpieczna Z musi byc nad powierzchnia") + """
#<len> = SQRT[[#<x2> - #<x1>] ** 2 + [#<y2> - #<y1>] ** 2]
o303 if [#<len> LT 0.001]
  (abort, lrt_slot_linear: dlugosc rowka musi byc dodatnia)
o303 endif
#<nx> = [[#<y1> - #<y2>] / #<len>]
#<ny> = [[#<x2> - #<x1>] / #<len>]
#<hmax> = [[#<width> - #<tool_d>] / 2]
#<stride> = [#<tool_d> * #<stepover> / 100]
#<rings> = 0
o304 if [#<hmax> GT 0.001]
  #<rings> = FUP[#<hmax> / #<stride> - 0.000000001]
  o305 if [#<rings> LT 1]
    #<rings> = 1
  o305 endif
o304 endif
#<zs> = [#<z_top> + 1]
o306 if [#<safe_z> - #<z_top> LT 1]
  #<zs> = #<safe_z>
o306 endif
G17 G90 G91.1 G94 G40 G80
G0 Z#<safe_z>
G0 X#<x1> Y#<y1>
G0 Z#<zs>
#<layers> = FUP[#<depth> / #<step_down> - 0.000000001]
#<k> = 1
o310 while [#<k> LE #<layers>]
  #<z> = [#<z_top> - #<k> * #<step_down>]
  o311 if [#<z> LT #<z_top> - #<depth>]
    #<z> = [#<z_top> - #<depth>]
  o311 endif
  G1 Z#<z> F#<plunge>
  G1 X#<x2> Y#<y2> F#<feed>
  #<j> = 1
  o320 while [#<j> LE #<rings>]
    #<h> = [#<hmax> * #<j> / #<rings>]
    #<ax> = [#<x1> - #<nx> * #<h>]
    #<ay> = [#<y1> - #<ny> * #<h>]
    #<bx> = [#<x2> - #<nx> * #<h>]
    #<by> = [#<y2> - #<ny> * #<h>]
    #<qx> = [#<x2> + #<nx> * #<h>]
    #<qy> = [#<y2> + #<ny> * #<h>]
    #<dx> = [#<x1> + #<nx> * #<h>]
    #<dy> = [#<y1> + #<ny> * #<h>]
    G1 X#<ax> Y#<ay> F#<feed>
    o321 if [#<ccw> NE 0]
      G1 X#<bx> Y#<by> F#<feed>
      G3 X#<qx> Y#<qy> I[#<x2> - #<bx>] J[#<y2> - #<by>] F#<feed>
      G1 X#<dx> Y#<dy> F#<feed>
      G3 X#<ax> Y#<ay> I[#<x1> - #<dx>] J[#<y1> - #<dy>] F#<feed>
    o321 else
      G2 X#<dx> Y#<dy> I[#<x1> - #<ax>] J[#<y1> - #<ay>] F#<feed>
      G1 X#<qx> Y#<qy> F#<feed>
      G2 X#<bx> Y#<by> I[#<x2> - #<qx>] J[#<y2> - #<qy>] F#<feed>
      G1 X#<ax> Y#<ay> F#<feed>
    o321 endif
    #<j> = [#<j> + 1]
  o320 endwhile
  G1 X#<x1> Y#<y1> F#<feed>
  #<k> = [#<k> + 1]
o310 endwhile
G0 Z#<safe_z>
""", "slot_linear")

SUBROUTINES = (FACE_MILL, DRILL_GRID, DRILL_CIRCLE, POCKET_RECT, POCKET_CIRCLE, SLOT_LINEAR)


def export(directory: Path | str) -> list[Path]:
    """Zapis podprogramów do katalogu (np. user_macros/); zwraca ścieżki plików."""
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    out = []
    for sub in SUBROUTINES:
        path = directory / f"{sub.name}.ngc"
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(sub.text(), encoding="ascii")
        tmp.replace(path)
        out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Eksport podprogramów linumeRT o<lrt_...>")
    ap.add_argument("directory", help="katalog z SUBROUTINE_PATH, np. "
                    "~/linuxcnc/nc_files/user_macros")
    args = ap.parse_args(argv)
    for path in export(args.directory):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
