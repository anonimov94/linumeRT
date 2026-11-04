# SPDX-License-Identifier: GPL-2.0-or-later
"""Wysokość Z z INI, numer T ze źródła i tabela maszyny: bez LinuxCNC.

Model-Author: Claude · 2026-11-01. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from linumert.generators import basic
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import compile_program
from linumert.programs.limits import safe_z_from_ini
from linumert.programs.linuxcnc_check import _machine_tool_table, _without_sample_tool_change
from linumert.programs.lnx import LnxProgram, Step
from linumert_sim.path import TOOL_UNKNOWN_NOTE, PathCanon, tool_changes

ROOT = Path(__file__).resolve().parents[1]


def _program(units="mm", header="G21"):
    registry = GeneratorRegistry()
    for cls in (basic.Header, basic.ToolChange, basic.ProgramEnd):
        registry.register(cls)
    program = LnxProgram(name="a", units=units, steps=[
        Step(generator="header", version=1, params={"units": header}),
        Step(generator="tool_change", version=1, params={"tool": 1}),
        Step(generator="program_end", version=1, params={})])
    return program, registry


def _z_moves(text):
    return [line for line in text.splitlines() if line.startswith("G53 G0 Z")]


def test_bez_safe_z_tekst_bez_zmian():
    assert _z_moves(compile_program(*_program())) == ["G53 G0 Z0"] * 3


def test_safe_z_zamienia_wszystkie_wycofania():
    assert _z_moves(compile_program(*_program(), safe_z=-1.0)) == ["G53 G0 Z-1"] * 3


def test_safe_z_w_calach_nie_przekracza_limitu():
    # -1 mm = -0,03937 cala: zaokrąglenie w górę dałoby ruch ponad MAX_LIMIT.
    lines = _z_moves(compile_program(*_program("inch", "G20"), safe_z=-1.0))
    assert lines == ["G53 G0 Z-0.0394"] * 3


def test_jednostki_z_naglowka_maja_pierwszenstwo():
    text = compile_program(*_program("mm", "G20"), safe_z=-1.0)
    assert _z_moves(text) == ["G53 G0 Z-0.0394"] * 3


def test_safe_z_z_ini(tmp_path):
    assert safe_z_from_ini(ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini") == -1.0
    assert safe_z_from_ini(ROOT / "config/sim/linumert_xyz/linumert_xyz.ini") == 0.0
    assert safe_z_from_ini(tmp_path / "brak.ini") is None
    assert safe_z_from_ini("") is None
    broken = tmp_path / "zly.ini"
    broken.write_text("bez sekcji\n", encoding="utf-8")
    assert safe_z_from_ini(broken) is None
    inch = tmp_path / "cale.ini"
    inch.write_text("[TRAJ]\nLINEAR_UNITS = inch\n[AXIS_Z]\nMIN_LIMIT = -4\nMAX_LIMIT = 1\n",
                    encoding="utf-8")
    assert safe_z_from_ini(inch) == pytest.approx(25.4)


def test_tabela_maszyny_wzgledem_ini(tmp_path):
    (tmp_path / "cfg").mkdir()
    (tmp_path / "t.tbl").write_text("T1 P1 Z75\n", encoding="utf-8")
    ini = tmp_path / "cfg/m.ini"
    ini.write_text("[EMCIO]\nTOOL_TABLE = ../t.tbl\n", encoding="utf-8")
    assert _machine_tool_table(ini).resolve() == (tmp_path / "t.tbl").resolve()
    ini.write_text("[EMCIO]\nTOOL_TABLE = brak.tbl\n", encoding="utf-8")
    assert _machine_tool_table(ini) is None
    ini.write_text("[EMC]\nVERSION = 1\n", encoding="utf-8")
    assert _machine_tool_table(ini) is None


def test_przykladowe_ustawienia_zmiany_narzedzia_usuniete():
    config = ("[EMCIO]\nTOOL_CHANGE_POSITION = 0 0 0\nTOOL_CHANGE_QUILL_UP = 1\n"
              "TOOL_CHANGE_WITH_SPINDLE_ON = 1\nTOOL_TABLE = sim.tbl\n")
    assert _without_sample_tool_change(config) == "[EMCIO]\nTOOL_TABLE = sim.tbl\n"


def test_t_wybiera_a_m6_zmienia():
    assert tool_changes("T1 M6\nG0 X1\nT7\nG0 X2\nM06\nT0 M6\n") == ([(1, 1), (5, 7), (6, 0)], [])


def test_m61_ustawia_narzedzie_bez_wymiany():
    assert tool_changes("M61 Q4\nG0 X1\nT7\nG0 X2\n") == ([(1, 4)], [])


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


def _goto_sensor(mdi_result):
    """Metoda handlera bez QtVCP: atrapy INFO, STATUS i ACTION."""
    source = (ROOT / "screens/linumert/linumert_handler.py").read_text(encoding="utf-8")
    cls = next(n for n in ast.parse(source).body
               if isinstance(n, ast.ClassDef) and n.name == "HandlerClass")
    method = next(n for n in cls.body if getattr(n, "name", "") == "btn_goto_sensor_clicked")
    calls, status = [], []

    def field(text):
        return SimpleNamespace(text=lambda: text)

    def mdi_wait(command, *_):
        calls.append(command)
        return mdi_result

    upstream = SimpleNamespace(
        INFO=SimpleNamespace(convert_machine_to_metric=lambda v: v,
                             convert_machine_to_imperial=lambda v: v / 25.4,
                             get_error_safe_setting=lambda *a: "-1.0"),
        STATUS=SimpleNamespace(is_metric_mode=lambda: True),
        ACTION=SimpleNamespace(CALL_MDI=calls.append, CALL_MDI_WAIT=mdi_wait),
        WARNING=1)
    scope = {"_upstream": upstream, "math": math}
    exec(compile(ast.Module([method], []), "handler", "exec"), scope)
    screen = SimpleNamespace(w=SimpleNamespace(lineEdit_sensor_x=field("50"),
                                               lineEdit_sensor_y=field("60")),
                             add_status=lambda text, level: status.append(text))
    scope["btn_goto_sensor_clicked"](screen)
    return calls, status


def test_dojazd_do_czujnika_wycofuje_do_limitu_maszyny():
    calls, status = _goto_sensor(0)
    assert calls == ["G90", "G53 G0 Z-1.0000", "G53 G0 X50.0000 Y60.0000"] and not status


def test_dojazd_do_czujnika_bez_xy_gdy_wycofanie_odrzucone():
    calls, status = _goto_sensor(-1)
    assert calls == ["G90", "G53 G0 Z-1.0000"] and status
