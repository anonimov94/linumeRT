"""Generatory jako podprogramy LinuxCNC `o<lrt_...>` (sesja 048).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-20

Każdy podprogram to osobny plik `<nazwa>.ngc` (nazwa pliku = nazwa podprogramu) do katalogu
z `[RS274NGC]SUBROUTINE_PATH`, zwykle `~/linuxcnc/nc_files/user_macros/`. Nagłówek w układzie
NgcGui (zakładka NgcGui w QtDragon): pierwsza linia `(info: ...)`, potem po jednej linii na
parametr `#<nazwa> = #n (=domyślna opis)`. Ruch jest ten sam co w generatorach Pythona
(`FaceMill`, `DrillHoles`) — sprawdza to test porównujący wyjście interpretera rs274.
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

SUBROUTINES = (FACE_MILL, DRILL_GRID, DRILL_CIRCLE)


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
