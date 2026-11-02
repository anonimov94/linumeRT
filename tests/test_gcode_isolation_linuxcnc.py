# SPDX-License-Identifier: GPL-2.0-or-later
"""Błędy z odbioru bety na `main`: `gcode.parse`, numer T, tabela maszyny, wysokość Z.

Model-Author: Claude · 2026-11-01. Wymaga LinuxCNC RIP; część z działającym LinuxCNC + Plant.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path

import plant_session
import pytest
from linumert.programs import linuxcnc_check
from linumert.programs.limits import analyze_ngc
from linumert.programs.linuxcnc_check import InterpreterUnavailable, run_interpreter
from linumert.programs.toolpath import TOOL_SKIPPED_NOTE, load_ngc
from linumert_sim.path import load_path, parse_rs274

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
PLANT_INI = ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini"
MACHINE = ROOT / "config/machines/mill_servo_table.yaml"
PORT = 47826
CRASHING = ["G43 H1", "G41 D3", "G10 L1 P1 Z5", "G10 L10 P1 Z5", "M61 Q1"]


@pytest.fixture
def program(tmp_path, monkeypatch):
    pytest.importorskip("gcode")
    # Prywatny HOME: brak ~/.tool.mmap także wtedy, gdy obok działa LinuxCNC.
    monkeypatch.setenv("HOME", str(tmp_path))

    def write(text: str) -> Path:
        target = tmp_path / "a.ngc"
        target.write_text(text, encoding="utf-8")
        return target
    return write


# --- 1. awaria i pętla bez działającego LinuxCNC

@pytest.mark.parametrize("word", ["T1", "T1 M6", *CRASHING])
def test_parse_rs274_przezywa_awarie_interpretera(program, word):
    file = program(f"G21\n{word}\nG1 X5 F100\nG40\nM2\n")
    if word in CRASHING:
        with pytest.raises(InterpreterUnavailable, match="kodem -11"):
            parse_rs274(file)
        assert load_path(file).source == "subset"
    else:
        assert parse_rs274(file).source == "rs274"


@pytest.mark.parametrize("word", CRASHING)
def test_load_ngc_przezywa_awarie_interpretera(program, word):
    with pytest.raises(InterpreterUnavailable, match="kodem -11"):
        load_ngc(program(f"G21\n{word}\nG1 X5 F100\nG40\nM2\n"))


def test_load_ngc_bez_linuxcnc_pomija_t_m6_z_notatka(program):
    path = load_ngc(program("G21\nG0 X1\nT1 M6\nG1 X5 F100\nM2\n"))
    assert TOOL_SKIPPED_NOTE in path.notes
    assert [move.line for move in path.moves] == [2, 4]
    assert path.moves[-1].feed == pytest.approx(100)


def test_numer_t_ze_zrodla_bez_dzialajacego_linuxcnc(program):
    moves = parse_rs274(program("G21\nT1 M6\nG1 X1 F100\nT7\nG1 X2\nM6\nG1 X3\nM2\n"))
    assert moves.source == "rs274" and moves.notes == ()
    assert [int(t) for t in moves.tool] == [1, 1, 7]


@pytest.mark.parametrize("load", [parse_rs274, load_ngc])
def test_petla_bez_konca_konczy_sie_limitem(program, monkeypatch, load):
    monkeypatch.setattr(linuxcnc_check, "PARSE_TIMEOUT", 3.0)
    with pytest.raises(ValueError, match="czas analizy"):
        load(program("o100 while [1]\nG0 X1\no100 endwhile\nM2\n"))


@pytest.mark.parametrize("load", [parse_rs274, load_ngc])
def test_blad_programu_to_wartosc_nie_awaria(program, load):
    with pytest.raises(ValueError, match="linia 2"):
        load(program("G21\nG1 X5\nM2\n"))


@pytest.mark.parametrize("module", ["linumert_sim._rs274_worker",
                                    "linumert.programs._toolpath_worker"])
def test_proces_potomny_konczy_sie_sam_po_smierci_rodzica(program, tmp_path, monkeypatch, module):
    """Ekran zabija wczytywanie po 20 s: pętla w procesie potomnym nie może zostać na zawsze."""
    file = program("o100 while [1]\nG0 X1\no100 endwhile\nM2\n")
    path = [str(ROOT / "core"), str(ROOT / "simulation")]
    monkeypatch.setenv("PYTHONPATH", ":".join([*path, *sys.path]))
    run = subprocess.run([sys.executable, "-m", module, str(file), "G21", "G17 G90 G94 G54",
                          str(tmp_path / "x.npz"), "2"], cwd=tmp_path, capture_output=True,
                         timeout=30, check=False)
    assert run.returncode == -signal.SIGALRM, run.stderr


# --- 3. tabela i zmiana narzędzia maszyny w analizie limitów

def _report(tmp_path, text, ini=PLANT_INI):
    path = tmp_path / "limit.ngc"
    path.write_text(text, encoding="utf-8")
    return analyze_ngc(path, ini).violations


def test_m6_nie_daje_falszywego_ruchu_z(tmp_path):
    assert _report(tmp_path, "G21 G90\nG53 G0 Z-5\nT1 M6\nG53 G0 Z-5\nM2\n") == []


def test_korekta_dlugosci_z_tabeli_maszyny(tmp_path):
    program = tmp_path / "tlo.ngc"
    program.write_text("G21 G90\nT1 M6\nG43 H1\nM2\n", encoding="utf-8")
    with_machine = run_interpreter(program, machine_ini=PLANT_INI, linear_units="mm")
    assert "USE_TOOL_LENGTH_OFFSET(0.0000 0.0000 75.0000" in with_machine.stdout
    # Bez INI maszyny nic się nie zmienia (kontrola składni: przykładowy sim.tbl).
    assert "75.0000" not in run_interpreter(program).stdout


def test_granice_licza_sie_z_dlugoscia_narzedzia_maszyny(tmp_path):
    # T1 ma w tabeli maszyny Z75: Z-70 w układzie programu to +5 w G53, ponad MAX_LIMIT -1.
    # Z przykładowym sim.tbl (Z 0,511 cala = 13 mm) naruszenia by nie było.
    found = _report(tmp_path, "G21 G90\nG53 G0 Z-5\nT1 M6\nG43 H1\nG0 Z-70\nM2\n")
    assert [(v.axis, v.side, round(v.value, 3)) for v in found] == [("Z", "max", 5.0)]


# --- 2. i 4. działający LinuxCNC + Plant: cały program generatora

DRIVER = r"""
root, ini = os.environ["LRT_ROOT"], os.environ["INI_FILE_NAME"]
sys.path[:0] = [root + "/core", root + "/simulation"]
import tempfile
from pathlib import Path
from linumert.generators import basic
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import compile_program
from linumert.programs.limits import analyze_ngc, safe_z_from_ini
from linumert.programs.lnx import LnxProgram, Step
from linumert.programs.toolpath import TOOL_SKIPPED_NOTE, load_ngc
from linumert_sim.offline import OfflineJob, simulate
from linumert_sim.path import parse_rs274

out = {"on": on, "homed": homed}
errors = linuxcnc.error_channel()
def drain():
    found = []
    while True:
        item = errors.poll()
        if not item:
            return found
        found.append(item[1])

assert mdi("G53 G0 Z-5")
drain()
out["z0_mdi"] = mdi("G53 G0 Z0", 15)
out["z0_errors"] = drain()
s.poll()
out["z_after_z0"] = round(s.position[2], 3)
c.abort(); c.wait_complete()

registry = GeneratorRegistry()
for cls in (basic.Header, basic.ToolChange, basic.ProgramEnd):
    registry.register(cls)
stock = ";@STOCK BOX X40 Y40 Z20 ORIGIN=TOP_FRONT_LEFT OFFSET=G54"
program = LnxProgram(name="odbior", steps=[
    Step(generator="header", version=1, params={"stock": stock}),
    Step(generator="tool_change", version=1, params={"tool": 1, "rpm": 3000}),
    Step(generator="program_end", version=1, params={})])
safe = safe_z_from_ini(ini)
text = compile_program(program, registry, safe_z=safe)
# Układ detalu w programie (analiza offline nie zna MDI), by T1 (Z75) był poniżej MAX_LIMIT.
body = text.replace("( krok 2", "G10 L2 P1 X100 Y100 Z-110\n( krok 2")
body = body.replace("M5\nM9\n", "G0 X10 Y10\nG1 Z-2 F300\nG1 X30 F600\nG0 Z10\nM5\nM9\n")
ngc = Path(tempfile.mkdtemp()) / "odbior.ngc"
ngc.write_text(body, encoding="utf-8")
out["safe_z"] = safe
out["text"] = body
out["violations"] = [[v.axis, v.side, v.value] for v in analyze_ngc(ngc, ini).violations]

moves = parse_rs274(ngc)
out["rs274_source"] = moves.source
out["rs274_tools"] = sorted({int(t) for t in moves.tool[moves.kind != 0]})
preview = load_ngc(ngc)
out["preview_note"] = TOOL_SKIPPED_NOTE in preview.notes
out["preview_moves"] = len(preview)
sim = simulate(OfflineJob(program=body, tools=((1, 75.0, 6.0),)))
out["sim_source"] = sim["source"]
out["removed_mm3"] = sim["removed_mm3"]

# Bez ekranu nie ma postgui: te same połączenia potwierdzenia M6 co linumert_postgui.hal.
import subprocess
for net in ("linumert.io.tool-change iocontrol.0.tool-change sim_toolchange.in",
            "linumert.io.tool-changed sim_toolchange.out iocontrol.0.tool-changed"):
    subprocess.run(["halcmd", "net", *net.split()], check=True)
drain()
c.mode(linuxcnc.MODE_AUTO); c.wait_complete()
c.program_open(str(ngc)); c.wait_complete()
c.auto(linuxcnc.AUTO_RUN, 0)
started = wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 30)
tools, z_min = set(), [0.0]
def finished():
    tools.add(s.tool_in_spindle)
    z_min[0] = min(z_min[0], s.position[2])
    return s.interp_state == linuxcnc.INTERP_IDLE
done = wait(finished, 180)
s.poll()
out.update(started=started, done=done, tools=sorted(tools), z_min=round(z_min[0], 3),
           tool=s.tool_in_spindle, z=round(s.position[2], 3), errors=drain())
print("RESULT " + json.dumps(out), flush=True)
"""


@pytest.fixture(scope="module")
def plant(tmp_path_factory):
    """Jedna sesja LinuxCNC + Plant dla kilku asercji (ok. 2 min)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LRT_ROOT", str(ROOT))
        result, _log, _out = plant_session.run_generated_plant(
            tmp_path_factory.mktemp("gcode_plant"), MACHINE, DRIVER, port=PORT)
    assert result["on"] and result["homed"], result
    return result


def test_plant_odrzuca_g53_z0_przy_limicie_ponizej_zera(plant):
    assert plant["z_after_z0"] < -1, plant
    assert any("limit" in message.lower() for message in plant["z0_errors"]), plant


def test_plant_program_generatora_przechodzi_z_wysokoscia_z_ini(plant):
    assert plant["safe_z"] == pytest.approx(-1.0)
    assert "G53 G0 Z0\n" not in plant["text"] and "G53 G0 Z-1\n" in plant["text"], plant["text"]
    assert plant["violations"] == [], plant
    assert plant["started"] and plant["done"], plant
    assert plant["errors"] == [], plant
    summary = {key: plant.get(key) for key in ("tools", "z_min", "tool", "z", "started", "done")}
    assert plant["tool"] == 1 and plant["z"] == pytest.approx(-1.0, abs=0.05), str(summary)


def test_plant_numer_t_i_material_przy_dzialajacym_linuxcnc(plant):
    assert plant["rs274_source"] == "rs274" and plant["rs274_tools"] == [1], plant
    assert plant["sim_source"] == "rs274" and plant["removed_mm3"] > 0, plant


def test_plant_podglad_przy_dzialajacym_linuxcnc_bez_pomijania(plant):
    assert plant["preview_moves"] > 3 and not plant["preview_note"], plant
