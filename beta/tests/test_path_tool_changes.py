"""Numer narzędzia ze źródła programu (`gcode.parse` go nie podaje).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-01
"""

from __future__ import annotations

from types import SimpleNamespace

from linumert_sim.path import TOOL_UNKNOWN_NOTE, PathCanon, tool_changes


def test_t_wybiera_a_m6_zmienia():
    assert tool_changes("T1 M6\nG0 X1\nT7\nG0 X2\nM06\nT0 M6\n") == ([(1, 1), (5, 7), (6, 0)], [])


def test_komentarze_i_nazwy_nie_sa_slowem_t():
    text = "(T5 M6)\n; T6 M6\n#<_cut>=1\nG0 X1 (M6)\n"
    assert tool_changes(text) == ([], [])


def test_wyrazenie_t_i_podprogram_daja_notatke():
    assert tool_changes("T#1 M6\n")[1] == [TOOL_UNKNOWN_NOTE]
    assert tool_changes("T[1+1]\n")[1] == [TOOL_UNKNOWN_NOTE]
    assert tool_changes("o<zmiana> call [1]\n")[1] == [TOOL_UNKNOWN_NOTE]


def test_ruch_dostaje_narzedzie_z_numeru_linii():
    canon = PathCanon(tool_changes=[(2, 1), (5, 7)])
    tools = []
    for line in (1, 2, 4, 5, 9):
        canon.next_line(SimpleNamespace(sequence_number=line))
        tools.append(canon.tool)
    assert tools == [0, 1, 1, 7, 7]
