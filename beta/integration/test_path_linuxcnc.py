"""Ścieżka z `gcode.parse` bez działającego LinuxCNC: proces wywołujący ma przeżyć awarię.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-01
"""

from __future__ import annotations

import pytest

from linumert_sim import path as path_module
from linumert_sim.path import InterpreterUnavailable, load_path, parse_rs274

pytest.importorskip("gcode")
pytestmark = pytest.mark.linuxcnc


@pytest.fixture
def program(tmp_path, monkeypatch):
    # Prywatny HOME: brak ~/.tool.mmap także wtedy, gdy obok działa LinuxCNC.
    monkeypatch.setenv("HOME", str(tmp_path))

    def write(text: str):
        target = tmp_path / "a.ngc"
        target.write_text(text, encoding="utf-8")
        return target
    return write


def test_numer_narzedzia_ze_zrodla_bez_mapowania_tablicy(program):
    moves = parse_rs274(program("G21\nT1 M6\nG1 X1 F100\nT7\nG1 X2\nM6\nG1 X3\nM2\n"))
    assert moves.source == "rs274"
    assert [int(t) for t in moves.tool] == [1, 1, 7]
    assert moves.notes == ()


@pytest.mark.parametrize("word", ["G43 H1", "G41 D3", "G10 L1 P1 Z5", "M61 Q1"])
def test_awaria_interpretera_nie_zabija_procesu(program, word):
    file = program(f"G21\n{word}\nG1 X5 F100\nG40\nM2\n")
    with pytest.raises(InterpreterUnavailable, match="kodem"):
        parse_rs274(file)
    assert load_path(file).source == "subset"


def test_blad_programu_to_wartosc_nie_awaria(program):
    with pytest.raises(ValueError, match="linia 2"):
        parse_rs274(program("G21\nG1 X5\nM2\n"))


def test_petla_bez_konca_konczy_sie_limitem(program, monkeypatch):
    monkeypatch.setattr(path_module, "RS274_TIMEOUT", 3.0)
    file = program("o100 while [1]\nG0 X1\no100 endwhile\nM2\n")
    with pytest.raises(ValueError, match="czas analizy"):
        parse_rs274(file)
