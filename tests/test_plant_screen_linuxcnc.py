# SPDX-License-Identifier: GPL-2.0-or-later
"""Start the actual Plant display with its complete postgui HAL. Model-Author: Codex."""

import contextlib
import os
import shlex
import shutil
import time
from pathlib import Path

import pytest
from rip_support import (
    installed_modules,
    plant_server,
    rip_root,
    rip_run,
    start_linuxcnc,
    stop_linuxcnc,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config/plant/linumert_plant_xyz"
pytestmark = pytest.mark.linuxcnc


@pytest.mark.parametrize("shell", ["1", "0"], ids=["hmi", "classic"])
def test_plant_opens_actual_screen_with_postgui(tmp_path, shell):
    root = rip_root()
    work = tmp_path / "cfg"
    shutil.copytree(CFG, work, symlinks=True)
    screen = work / "qtvcp/screens/linumert"
    screen.unlink()
    screen.symlink_to(ROOT / "screens/linumert")
    ini = work / "linumert_plant_xyz.ini"
    text = ini.read_text().replace("PORT = 47700", "PORT = 47825")
    text = text.replace("../../hal/", str(ROOT / "config/hal") + "/")
    text = text.replace("../../sim/", str(ROOT / "config/sim") + "/")
    # Keep DISPLAY, POSTGUI_HALFILE and HMI_ESTOP_BYPASS exactly as used by the launcher.
    ini.write_text(text)
    env = {**os.environ, "LINUMERT_SHELL": shell, "INI_FILE_NAME": str(ini)}
    probe_code = """
import time, hal
component = hal.component('linumert_screen_probe')
component.ready()
assert hal.get_value('lrt-net.0.connected')
for pin in ('sim_toolchange.in', 'iocontrol.0.tool-changed', 'lrt_ack_edge.in'):
    assert hal.pin_has_writer(pin), pin
hal.get_value('hal_manualtoolchange.number')
seen = set()
end = time.monotonic() + 2
while time.monotonic() < end and len(seen) < 2:
    seen.add(bool(hal.get_value('linumert.hmi-heartbeat')))
    time.sleep(0.025)
assert len(seen) == 2, 'GUI heartbeat is not running'
component.exit()
"""
    with contextlib.ExitStack() as stack:
        stack.enter_context(installed_modules(root, tmp_path,
                                             ("lrt_net", "lrt_cia402", "lrt_estop2")))
        stack.enter_context(plant_server(CFG / "plant.yaml", 47825, "--seed", "5"))
        cnc = start_linuxcnc(root, ini, env)
        ready, diagnostic = False, ""
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and cnc.poll() is None:
                probe = rip_run(root, "python3 -c " + shlex.quote(probe_code), work,
                                timeout=10, env=env)
                if probe.returncode == 0:
                    ready = True
                    break
                diagnostic = probe.stdout + probe.stderr
                time.sleep(0.25)
            if ready:
                # Exercise offline analysis while the actual QtVCP/tool mmap is live.
                # Recheck heartbeat and toolchange pins after both bounded failures.
                loop = work / "infinite.ngc"
                loop.write_text("o100 while [1]\nG4 P0.1\no100 endwhile\nM2\n")
                analysis = f"""
from linumert.programs.estimate import estimate_ngc
from linumert.programs.linuxcnc_check import check_with_linuxcnc
result = check_with_linuxcnc({str(loop)!r}, {str(root)!r}, timeout=0.2)
assert not result.ok and not result.completed, result
try:
    estimate_ngc({str(loop)!r}, {str(ini)!r}, {str(root)!r}, timeout=0.2)
except ValueError as exc:
    assert 'limit' in str(exc), str(exc)
else:
    raise AssertionError('infinite program received a runtime estimate')
"""
                checked = rip_run(root, "python3 -c " + shlex.quote(analysis), work, env=env)
                assert checked.returncode == 0, checked.stdout + checked.stderr
                alive = rip_run(root, "python3 -c " + shlex.quote(probe_code), work, env=env)
                assert alive.returncode == 0, alive.stdout + alive.stderr
                shot_path = str(tmp_path / "screen.png")
                capture = ("from PyQt5.QtWidgets import QApplication; a=QApplication([]); "
                           f"assert a.primaryScreen().grabWindow(0).save({shot_path!r})")
                shot = rip_run(root, "python3 -c " + shlex.quote(capture), work, env=env)
                assert shot.returncode == 0, shot.stdout + shot.stderr
                assert cnc.poll() is None
        finally:
            stop_linuxcnc(cnc, root, work)
            log = cnc.stdout.read()
            (tmp_path / "linuxcnc.log").write_text(log)
    assert ready, "Plant display/postgui did not become ready:\n" + diagnostic + log[-12000:]
    assert "Pin 'sim_toolchange.in' does not exist" not in log, log
