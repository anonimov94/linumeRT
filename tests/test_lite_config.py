"""Portable configuration and unchanged shared scales. Model-Author: Codex."""

import configparser
from pathlib import Path

import pytest
from linumert.machine.configgen import plant_scales, render
from linumert.machine.drives.machine_drives import load_machine_drives
from linumert.machine.lite_config import build, render_lite
from linumert_plant.build_machine import build_model

ROOT = Path(__file__).resolve().parents[1]
MACHINES = sorted((ROOT / "config/machines").glob("*.yaml"))


@pytest.mark.parametrize("machine", MACHINES, ids=lambda p: p.stem)
def test_shared_scales_equal_plant_model(machine):
    cfg, drives = load_machine_drives(machine)
    assert plant_scales(cfg) == build_model(cfg, drives).counts_per_unit


@pytest.mark.parametrize("target", ["sim", "plant"])
def test_export_has_no_gui_and_all_file_references_exist(target):
    cfg, _ = load_machine_drives(MACHINES[0])
    files = render_lite(cfg, target)
    ini = files[f"{cfg.machine.name}.ini"]
    assert "DISPLAY = linumert-headless" in ini
    assert "POSTGUI_HALFILE" not in ini and "qtvcp" not in ini
    assert "HMI_ESTOP_BYPASS = 0" in ini
    for line in ini.splitlines():
        if line.startswith("HALFILE = "):
            assert line.removeprefix("HALFILE = ") in files
    for name in ("tool.tbl", "macros/lrt_m6.ngc", "nc_files/.keep"):
        assert name in files
    assert "HMI_ESTOP_BYPASS = 1" in render_lite(cfg, target, test_mode=True)[
        f"{cfg.machine.name}.ini"]


def test_hardware_target_and_atc_are_explicitly_refused():
    cfg, _ = load_machine_drives(MACHINES[0])
    from linumert.machine.configgen import Options

    with pytest.raises(ValueError):
        render_lite(cfg, "hardware", test_mode=True)
    with pytest.raises(ValueError):
        render(cfg, "hardware")
    with pytest.raises(ValueError, match="ATC"):
        render(cfg, "plant", Options(atc=True))


def test_config_preview_backup_and_repeatability(tmp_path):
    out = tmp_path / "machine"
    diff, backup = build(MACHINES[0], "sim", out)
    assert diff and backup is None and not out.exists()
    build(MACHINES[0], "sim", out, write=True)
    (out / "operator.ngc").write_text("M2\n", encoding="utf-8")
    (out / "tool.tbl").write_text("T42 P42 D6 Z40 ; operator\n", encoding="utf-8")
    assert build(MACHINES[0], "sim", out) == ("", None)
    _, backup = build(MACHINES[0], "sim", out, write=True, test_mode=True)
    assert backup and (backup / "operator.ngc").read_text(encoding="utf-8") == "M2\n"
    assert (out / "tool.tbl").read_text(encoding="utf-8") == "T42 P42 D6 Z40 ; operator\n"
    cp = configparser.ConfigParser(strict=False)
    cp.read(next(out.glob("*.ini")), encoding="utf-8")
    assert cp["LINUMERT"]["MACHINE_PROFILE"] == "sim"
