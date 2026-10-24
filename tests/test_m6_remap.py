"""Automatyczne G43 po M6 (remap w INI): sim i Plant mają ten sam podprogram."""

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INIS = [ROOT / "config/sim/linumert_xyz/linumert_xyz.ini",
        ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini",
        ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz_vfd.ini"]
MACRO = ROOT / "config/sim/linumert_xyz/macros/lrt_m6.ngc"
PLANT_MACRO = ROOT / "config/plant/linumert_plant_xyz/macros/lrt_m6.ngc"


@pytest.mark.parametrize("ini", INIS, ids=lambda p: p.parent.name + "/" + p.name)
def test_ini_remaps_m6_to_the_shared_macro(ini):
    text = ini.read_text(encoding="utf-8")
    assert re.search(r"(?m)^REMAP = M6 modalgroup=6 ngc=lrt_m6$", text)
    path = re.search(r"(?m)^SUBROUTINE_PATH = (.*)$", text).group(1).split(":")
    assert any((ini.parent / p / "lrt_m6.ngc").is_file() for p in path)


def test_plant_macro_is_identical_to_the_sim_macro():
    assert PLANT_MACRO.read_bytes() == MACRO.read_bytes()


def test_macro_names_its_own_sub_and_calls_builtin_m6():
    text = MACRO.read_text(encoding="utf-8")
    assert "o<lrt_m6> sub" in text and "o<lrt_m6> endsub" in text
    assert re.search(r"(?m)^M6$", text) and "G43 H#<lrt_tool>" in text and "G49" in text


@pytest.mark.linuxcnc
def test_t_m6_applies_tool_length_in_the_real_interpreter(tmp_path):
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "bin/rs274").exists():
        pytest.skip(f"brak rs274 w {root}")
    var = tmp_path / "m6.var"
    var.touch()
    text = INIS[0].read_text(encoding="utf-8")
    for key, value in (("SUBROUTINE_PATH", MACRO.parent), ("PARAMETER_FILE", var)):
        text = re.sub(rf"(?m)^{key} = .*$", f"{key} = {value}", text)
    ini = tmp_path / "m6.ini"
    ini.write_text(text, encoding="utf-8")
    program = tmp_path / "m6.ngc"
    program.write_text("G21 G90 G54\nT2 M6\nG0 Z-10\nT0 M6\nG0 Z-20\nM2\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    table = ROOT / "config/sim/linumert_xyz/tool.tbl"
    command = (f"source {shlex.quote(str(root / 'scripts/rip-environment'))} >/dev/null && "
               f"rs274 -i {shlex.quote(str(ini))} -t {shlex.quote(str(table))} "
               f"-v {shlex.quote(str(var))} -n 0 {shlex.quote(str(program))}")
    run = subprocess.run(["bash", "-c", command], cwd=tmp_path, stdin=subprocess.DEVNULL,
                         env=dict(os.environ, HOME=str(home), LC_ALL="C"),
                         capture_output=True, text=True, timeout=60, check=False)
    offsets = re.findall(r"USE_TOOL_LENGTH_OFFSET\(([^)]*)\)", run.stdout)
    assert [o.split()[2].rstrip(",") for o in offsets[:2]] == ["80.0000", "0.0000"], run.stdout
