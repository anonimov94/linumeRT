"""User workflows and failure contracts of the headless CLI. Model-Author: Codex."""

import json
from pathlib import Path

import pytest
from linumert.cli import main, registry
from linumert.programs.lnx import LnxProgram, Step, save_lnx

ROOT = Path(__file__).resolve().parents[1]


def test_compile_versions_and_failure_preserves_existing_output(tmp_path, capsys):
    source, output = tmp_path / "part.lnx", tmp_path / "part.ngc"
    save_lnx(LnxProgram(name="test", steps=[Step(generator="drill_holes", version=1,
                                                params={"depth": 2})]), source)
    assert main(["compile", str(source), "--out", str(output)]) == 0
    assert output.read_text(encoding="utf-8").endswith("M2\n")
    previous = output.read_bytes()
    program = json.loads(source.read_text(encoding="utf-8"))
    program["steps"][0]["version"] = 999
    source.write_text(json.dumps(program), encoding="utf-8")
    assert main(["compile", str(source), "--out", str(output)]) == 2
    assert output.read_bytes() == previous
    assert "999" in capsys.readouterr().err


def test_registry_has_versions_one_and_two_without_stl():
    reg = registry()
    assert reg.get("pocket_rect", 1) and reg.get("pocket_rect", 2)
    assert not any("stl" in name or "relief" in name for name in reg.names())
    assert registry().names() == reg.names()


def test_material_simulation_writes_json(tmp_path):
    program = tmp_path / "part.ngc"
    program.write_text(';@STOCK BOX X40 Y40 Z10 ORIGIN=TOP_FRONT_LEFT OFFSET=G54\n'
                       'G21 G90\nT1 M6\nS12000 M3\nG0 X10 Y10 Z5\n'
                       'G1 Z-1 F200\nG1 X20 F600\nG0 Z5\nM2\n', encoding="utf-8")
    report = tmp_path / "report.json"
    assert main(["simulate", str(program), "--tool", "1:40:6", "--out", str(report)]) == 0
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["source"] == "subset"
    assert result["removed_mm3"] > 0 and result["time_s"] > 0


@pytest.mark.parametrize("command", ["compile", "machine", "simulate"])
def test_missing_input_is_a_readable_error(command, tmp_path, capsys):
    assert main([command, str(tmp_path / "missing")]) == 2
    assert "Błąd:" in capsys.readouterr().err


def test_bad_machine_has_no_traceback(tmp_path, capsys):
    path = tmp_path / "machine.yaml"
    path.write_text("machine: broken", encoding="utf-8")
    assert main(["machine", str(path)]) == 2
    assert "Błąd:" in capsys.readouterr().err


def test_headless_refuses_hardware_before_importing_linuxcnc(tmp_path, capsys):
    from linumert.cnc.headless import main as display

    ini = tmp_path / "machine.ini"
    ini.write_text("[LINUMERT]\nMACHINE_PROFILE = hardware\n", encoding="utf-8")
    assert display(["-ini", str(ini)]) == 2
    assert "sim/plant" in capsys.readouterr().err
