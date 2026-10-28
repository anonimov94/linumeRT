# SPDX-License-Identifier: GPL-2.0-or-later
"""D38 on real LinuxCNC, with both loopback and Plant drives. Model-Author: Codex."""

import contextlib
import json
import os
import re
import shlex
import shutil
import time
from pathlib import Path

import pytest
from linumert.programs.pause_retract import RETURN_TOLERANCE_MM
from rip_support import (
    installed_modules,
    plant_server,
    rip_root,
    rip_run,
    start_linuxcnc,
    stop_linuxcnc,
)

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.linuxcnc


@pytest.mark.parametrize("plant", [False, True], ids=["sim", "plant"])
def test_retract_returns_to_compensated_path(tmp_path, plant, request):
    root = rip_root()
    source = ROOT / "config" / ("plant/linumert_plant_xyz" if plant else "sim/linumert_xyz")
    work = tmp_path / "cfg"
    shutil.copytree(source, work, symlinks=True)
    ini = work / ("linumert_plant_xyz.ini" if plant else "linumert_xyz.ini")
    text = ini.read_text().replace("DISPLAY = qtvcp linumert", "DISPLAY = retract_headless")
    text = re.sub(r"^POSTGUI_HALFILE.*$", "", text, flags=re.M)
    text = text.replace("HALFILE = ../../hal/", f"HALFILE = {ROOT / 'config/hal'}/")
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    text = text.replace("PORT = 47700", "PORT = 47823")
    text = re.sub(r"^TOOL_TABLE\s*=.*$", "TOOL_TABLE = retract.tbl", text, flags=re.M)
    text = re.sub(r"^PARAMETER_FILE\s*=.*$", "PARAMETER_FILE = retract.var", text, flags=re.M)
    ini.write_text(text)
    (work / "retract.tbl").write_text("T1 P1 Z10 D4 ; D38 test\n")
    display = work / "retract_headless"
    display.write_text("#!/bin/sh\nexec sleep 3600\n")
    display.chmod(0o755)
    env = {**os.environ, "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(work),
           "PATH": str(work) + os.pathsep + os.environ.get("PATH", "")}
    joint_count = 4 if plant else 3
    with contextlib.ExitStack() as stack:
        if plant:
            stack.enter_context(installed_modules(root, tmp_path,
                                                 ("lrt_net", "lrt_cia402", "lrt_estop2")))
            stack.enter_context(plant_server(source / "plant.yaml", 47823, "--seed", "5"))
        cnc = start_linuxcnc(root, ini, env)
        try:
            ready = False
            for _ in range(60):
                if cnc.poll() is not None:
                    break
                probe_code = "import linuxcnc; s=linuxcnc.stat(); s.poll(); "
                probe_code += f"assert s.joints == {joint_count}"
                probe = rip_run(root, "python3 -c " + shlex.quote(probe_code), work, env=env)
                if probe.returncode == 0:
                    if plant:
                        link = rip_run(root, "halcmd getp lrt-net.0.connected", work, env=env)
                        if link.stdout.strip() != "TRUE":
                            time.sleep(0.25)
                            continue
                    ready = True
                    break
                time.sleep(0.25)
            assert ready, "LinuxCNC startup failed"
            if plant:
                time.sleep(1)  # Let initial Plant feedback settle before enabling/homing drives.
            enabled = rip_run(root, "halcmd getp axis.z.eoffset-enable", work, env=env)
            assert enabled.stdout.strip() in ("FALSE", "0"), enabled.stdout
            args = [str(ROOT / "tests/pause_retract_driver.py"), str(ini),
                    str(joint_count), str(tmp_path)]
            run = rip_run(root, "python3 " + " ".join(map(shlex.quote, args)), work,
                          timeout=360, env=env)
        finally:
            stop_linuxcnc(cnc, root, work)
            (tmp_path / "linuxcnc.log").write_text(cnc.stdout.read())
    assert run.returncode == 0, run.stdout + run.stderr
    reporter = request.config.pluginmanager.get_plugin("terminalreporter")
    for line in run.stdout.splitlines():
        if line.startswith("D38_RESULT "):
            reporter.write_line(("PLANT " if plant else "SIM ") + line)
    rows = json.loads((tmp_path / "retract-results.json").read_text())
    assert [(r["correction"], r["inch"]) for r in rows] == [
        (40, False), (41, False), (42, False), (41, True), (42, True)]
    for row in rows:
        assert row["end"][:2] == pytest.approx([250, 100], abs=0.005), row
        assert abs(row["offset"]) <= RETURN_TOLERANCE_MM, row
