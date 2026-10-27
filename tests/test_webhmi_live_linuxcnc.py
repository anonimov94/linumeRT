# SPDX-License-Identifier: GPL-2.0-or-later
"""WebSocket commands and DRO on real LinuxCNC sim. Model-Author: Codex."""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from rip_support import start_linuxcnc, stop_linuxcnc

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.linuxcnc


def test_websocket_jog_and_disconnect_with_real_linuxcnc(tmp_path):
    """A headless fixture may reset safety; the web API itself must never do so."""
    if shutil.which("linuxcnc") is None:
        pytest.skip("LinuxCNC installed or RIP environment required")
    work = tmp_path / "cfg"
    shutil.copytree(ROOT / "config/sim/linumert_xyz", work, symlinks=True)
    ini = work / "linumert_xyz.ini"
    text = ini.read_text().replace("DISPLAY = qtvcp linumert", "DISPLAY = webhmi_headless")
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    text = text.replace("HALFILE = ../../hal/", f"HALFILE = {ROOT / 'config/hal'}/")
    text = re.sub(r"^POSTGUI_HALFILE.*$", "", text, flags=re.M)
    ini.write_text(text)
    (work / "linumert.var").unlink(missing_ok=True)
    display = work / "webhmi_headless"
    display.write_text("#!/bin/sh\nexec sleep 3600\n")
    display.chmod(0o755)
    env = {**os.environ, "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(work),
           "PATH": str(work) + os.pathsep + os.environ.get("PATH", ""),
           "PYTHONPATH": os.pathsep.join([str(ROOT / "core"), str(ROOT / "webhmi/server"),
                                          os.environ.get("PYTHONPATH", "")])}
    proc = start_linuxcnc(None, ini, env)
    try:
        deadline = time.monotonic() + 60
        while True:
            probe = subprocess.run(
                [sys.executable, "-c", "import linuxcnc; s=linuxcnc.stat(); "
                 "s.poll(); assert s.joints == 3"], env=env, cwd=work,
                capture_output=True, text=True, timeout=10)
            if probe.returncode == 0:
                break
            assert proc.poll() is None, "LinuxCNC startup failed; see linuxcnc.log"
            assert time.monotonic() < deadline, probe.stdout + probe.stderr
            time.sleep(0.25)
        run = subprocess.run([sys.executable, str(ROOT / "tests/webhmi_live_driver.py"),
                              str(tmp_path / "webhmi-result.json")],
                             env=env, cwd=work, capture_output=True, text=True, timeout=180)
        (tmp_path / "webhmi-driver.log").write_text(run.stdout + run.stderr)
        assert run.returncode == 0, run.stdout + run.stderr
        assert (tmp_path / "webhmi-result.json").exists()
    finally:
        stop_linuxcnc(proc, cwd=work)
        (tmp_path / "linuxcnc.log").write_text(proc.stdout.read())
