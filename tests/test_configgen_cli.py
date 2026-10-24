# SPDX-License-Identifier: GPL-2.0-or-later
"""linumert-config build: podgląd, zapis z kopią zapasową, pliki operatora, błędy (sesja 062).

Model-Author: Claude · 2026-10-24. Uruchomienie wygenerowanej konfiguracji: marker linuxcnc.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest
import yaml
from linumert.machine.config_build import main

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
ROUTER = ROOT / "config/machines/router_gantry_steppers.yaml"


def test_preview_then_write_with_backup(tmp_path, capsys):
    out = tmp_path / "plant_cfg"
    args = ["build", str(MILL), "--target", "plant", "--out", str(out)]
    assert main(args) == 1                                  # podgląd: są zmiany, nic nie zapisane
    assert "+[KINS]" in capsys.readouterr().out and not out.exists()
    assert main([*args, "--write"]) == 0
    ini = out / "mill_servo_table.ini"
    assert ini.is_file() and (out / "linumert_plant.hal").is_file()
    assert main(args) == 0 and "Bez zmian" in capsys.readouterr().out
    # Plik operatora zostaje; zmiana generatora (port) robi kopię zapasową całego katalogu.
    (out / "tool.tbl").write_text("T1 P1 Z40 D6\n", encoding="utf-8")
    assert main([*args, "--write", "--port", "47800"]) == 0
    assert "PORT = 47800" in ini.read_text(encoding="utf-8")
    assert (out / "tool.tbl").read_text(encoding="utf-8") == "T1 P1 Z40 D6\n"
    backups = list(tmp_path.glob("plant_cfg.backup-*/plant_cfg"))
    assert len(backups) == 1
    assert "PORT = 47700" in (backups[0] / "mill_servo_table.ini").read_text(encoding="utf-8")
    assert (backups[0] / "tool.tbl").is_file()


def test_invalid_machine_is_refused(tmp_path, capsys):
    data = yaml.safe_load(MILL.read_text(encoding="utf-8"))
    data["axes"][0]["soft_limits"] = [700, 800]             # poza travel
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(data), encoding="utf-8")
    out = tmp_path / "cfg"
    assert main(["build", str(bad), "--target", "sim", "--out", str(out), "--write"]) == 2
    assert "błąd:" in capsys.readouterr().err and not out.exists()


DRIVER = r"""
import json, sys, time
import linuxcnc
s, c = linuxcnc.stat(), linuxcnc.command()
def wait(cond, timeout):
    end = time.time() + timeout
    while time.time() < end:
        s.poll()
        if cond():
            return True
        time.sleep(0.05)
    return False
ok = wait(lambda: s.task_state != 0, 30)
c.state(linuxcnc.STATE_ESTOP_RESET); c.wait_complete()
c.state(linuxcnc.STATE_ON); c.wait_complete()
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.home(-1)
homed = wait(lambda: all(s.homed[j] for j in range(s.joints)), 180)
s.poll()
print("RESULT " + json.dumps({"on": s.task_state == linuxcnc.STATE_ON, "homed": homed,
      "joints": s.joints, "pos": [round(v, 3) for v in s.joint_actual_position[:s.joints]]}))
"""


@pytest.mark.linuxcnc
def test_generated_sim_config_runs_and_homes_in_linuxcnc(tmp_path):
    """Wygenerowany sim dla bramy (Y1/Y2): LinuxCNC startuje, włącza się i bazuje wszystkie osie."""
    import rip_support as rip
    from linumert.machine.configgen import Options, render
    from linumert.machine.schema import load_machine

    root = rip.rip_root()
    if rip.leftovers():
        # start_linuxcnc sprząta procesy LinuxCNC użytkownika — nie przerywaj cudzego przebiegu
        # (np. równoległej serii M1 na tej samej maszynie).
        pytest.skip(f"działa inny LinuxCNC: {rip.leftovers()}")
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    opt = Options(hal_dir=str(ROOT / "config/hal"),
                  program_prefix=str(ROOT / "config/sim/nc_files"),
                  tool_table=str(ROOT / "config/sim/linumert_xyz/tool.tbl"), postgui="",
                  subroutine_path=str(ROOT / "config/sim/linumert_xyz/macros"))
    cfg = load_machine(ROUTER)
    for name, text in render(cfg, "sim", opt).items():
        if name.endswith(".ini"):
            # Bez ekranu: zastępczy proces DISPLAY i jawne obejście grzyba HMI (tylko w teście).
            text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
            text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
        (cfg_dir / name).write_text(text, encoding="utf-8")
    shutil.copy(ROOT / "config/sim/linumert_xyz/linumert.var.default", cfg_dir / "linumert.var")
    script = cfg_dir / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    (tmp_path / "driver.py").write_text(DRIVER, encoding="utf-8")
    ini = cfg_dir / f"{cfg.machine.name}.ini"
    env = {**__import__("os").environ, "PATH": f"{cfg_dir}:{__import__('os').environ['PATH']}"}
    cnc = rip.start_linuxcnc(root, ini, env)
    try:
        for _ in range(120):
            time.sleep(0.5)
            probe = rip.rip_run(root, "halcmd getp joint.0.home-sw-in", cfg_dir, env=env)
            if probe.returncode == 0 or cnc.poll() is not None:
                break
        assert cnc.poll() is None, cnc.stdout.read() if cnc.stdout else "LinuxCNC zakończony"
        run = rip.rip_run(root, f"python3 {tmp_path / 'driver.py'}", cfg_dir, timeout=300,
                          env=env)
        line = next((x for x in run.stdout.splitlines() if x.startswith("RESULT ")), None)
        assert line, run.stdout + run.stderr
        result = json.loads(line[7:])
    finally:
        rip.stop_linuxcnc(cnc, root, cfg_dir)
    assert result["on"] and result["homed"], result
    assert result["joints"] == 4
    # Po bazowaniu jointy w HOME z generatora: X/Y soft min + 4 mm, Z soft max − 4 mm.
    assert result["pos"] == pytest.approx([5.0, 5.0, 5.0, -5.0], abs=0.01)
