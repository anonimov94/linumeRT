"""Makro sondowania jednej osi ``o<lrt_probe>`` i budowa jego wywołania.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Sondowanie to jedno polecenie MDI ``o<lrt_probe> call [...]`` (CLAUDE.md §8): LinuxCNC
wykonuje G38.2, zapisuje offset przez G10 L20 i odjeżdża — bez czekania aplikacji na koniec
każdego kroku. Po G38.2 maszyna stoi kawałek za punktem styku (hamowanie), więc wartość
dla G10 L20 liczymy względem punktu styku: ``#<_x> - #5061 + wartość`` (różnica pozycji
bieżącej i punktu styku nie zależy od układu, więc wzór działa dla dowolnego P).

Plik makra leży w katalogu ``SUBROUTINE_PATH`` konfiguracji (``macros/lrt_probe.ngc``);
generator konfiguracji dokłada go do wygenerowanych plików. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

PROBE_AXES = ("X", "Y", "Z")
WORK_OFFSETS = ("G54", "G55", "G56", "G57", "G58", "G59", "G59.1", "G59.2", "G59.3")

_AXIS_BLOCK = """\
  G91
  G38.2 {a}#<dist> F#4
  G90
  G10 L20 P#5 {a}[#<_{l}> - #{param} + #6]
  G91
  G0 {a}#<back>"""


def _branch(index: int) -> str:
    axis = PROBE_AXES[index]
    return _AXIS_BLOCK.format(a=axis, l=axis.lower(), param=5061 + index)


PROBE_MACRO = f"""\
; SPDX-License-Identifier: GPL-2.0-or-later
; Model-Author: Claude
; linumeRT - sondowanie jednej osi (operacja offset.probe_run). Wywolanie:
;   o<lrt_probe> call [os] [kierunek] [droga] [posuw] [P] [wartosc] [odjazd]
; os: 0=X 1=Y 2=Z; kierunek +1/-1; droga i odjazd > 0 [mm]; P: 1..9 = G54..G59.3;
; wartosc: wspolrzedna punktu styku w ukladzie P (juz z poprawka kalibracji sondy).
; G38.2 konczy sie bledem, gdy sonda nie zadziala na drodze - offset nie jest wtedy zapisany.
o<lrt_probe> sub
#<abs> = #<_absolute>
#<dist> = [#2 * #3]
#<back> = [0 - #2 * #7]
o10 if [#1 EQ 0]
{_branch(0)}
o10 elseif [#1 EQ 1]
{_branch(1)}
o10 else
{_branch(2)}
o10 endif
o20 if [#<abs> EQ 1]
  G90
o20 endif
o<lrt_probe> endsub
M2
"""


def probe_call(axis: str, direction: int, distance: float, feed: float, offset: str,
               value: float, retract: float) -> str:
    """Wywołanie makra; walidację zakresów robi warstwa usługi, tu tylko kształt."""
    index = PROBE_AXES.index(axis.upper())
    p = WORK_OFFSETS.index(offset) + 1
    args = (index, direction, distance, feed, p, value, retract)
    return "o<lrt_probe> call " + " ".join(f"[{_num(v)}]" for v in args)


def _num(value: float) -> str:
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


__all__ = ["PROBE_AXES", "PROBE_MACRO", "WORK_OFFSETS", "probe_call"]
