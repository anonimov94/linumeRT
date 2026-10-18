"""Real RIP/uspace smoke tests; no physical machine. Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.linuxcnc


def wait_for(predicate, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        assert process.poll() is None, "LinuxCNC exited prematurely; inspect linuxcnc.log"
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError("LinuxCNC did not reach the expected state before timeout")


@pytest.fixture
def simulation(tmp_path):
    import linuxcnc

    source = Path(os.environ["LINUXCNC_DIR"])
    assert not Path("/tmp/linuxcnc.lock").exists(), "Another LinuxCNC instance is running"
    configs = tmp_path / "configs"
    shutil.copytree(source / "configs", configs, symlinks=True)
    shutil.copytree(source / "nc_files", tmp_path / "nc_files", symlinks=True)
    processes = []

    def start(relative, headless=False):
        ini = configs / relative
        text = ini.read_text()
        if headless:
            text = re.sub(r"(?m)^DISPLAY\s*=.*$", "DISPLAY = halui", text)
            text = re.sub(r"(?m)^HALUI\s*=.*$", "", text)
            text = re.sub(r"(?m)^HALFILE\s*= axis_manualtoolchange.hal.*$", "", text)
        ini.write_text(text)
        log = (tmp_path / "linuxcnc.log").open("w")
        process = subprocess.Popen(
            ["linuxcnc", "-r", str(ini)], cwd=ini.parent,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        processes.append((process, log))
        def ready():
            # Upstream caches a failed first tool mmap for the process lifetime.
            # Probe in a separate process until both NML and tool data are ready.
            probe = subprocess.run(
                [sys.executable, "-c", "import linuxcnc; s=linuxcnc.stat(); "
                 "s.poll(); assert s.joints == 3"],
                capture_output=True, timeout=5,
            )
            return probe.returncode == 0

        wait_for(ready, process)
        status = linuxcnc.stat()
        status.poll()
        return process, status

    yield start
    for process, log in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        log.close()
        print((tmp_path / "linuxcnc.log").read_text())


def test_sim_import_home_and_mdi(simulation):
    import linuxcnc

    process, status = simulation("sim/axis/axis.ini", headless=True)
    command = linuxcnc.command()

    def state_is(expected):
        status.poll()
        return status.task_state == expected

    command.state(linuxcnc.STATE_ESTOP_RESET)
    wait_for(lambda: state_is(linuxcnc.STATE_ESTOP_RESET), process)
    command.state(linuxcnc.STATE_ON)
    wait_for(lambda: state_is(linuxcnc.STATE_ON), process)
    command.mode(linuxcnc.MODE_MANUAL)
    assert command.wait_complete(10) == linuxcnc.RCS_DONE
    command.home(-1)

    def homed():
        status.poll()
        return all(status.homed[:3])

    wait_for(homed, process)
    command.mode(linuxcnc.MODE_MDI)
    assert command.wait_complete(10) == linuxcnc.RCS_DONE
    command.mdi("G20 G90 G53 G0 X1 Y1 Z-1")
    assert command.wait_complete(15) == linuxcnc.RCS_DONE
    status.poll()
    assert status.actual_position[:3] == pytest.approx((1, 1, -1), abs=0.001)
    command.state(linuxcnc.STATE_OFF)
    wait_for(lambda: state_is(linuxcnc.STATE_ESTOP_RESET), process)


def test_qtdragon_screen(simulation, tmp_path):
    process, _ = simulation("sim/qtdragon/qtdragon_xyz/qtdragon_metric.ini")

    def screen_ready():
        result = subprocess.run(
            ["halcmd", "show", "pin", "qtdragon.*"], capture_output=True, text=True,
            check=True, timeout=5,
        )
        return "qtdragon" in result.stdout

    wait_for(screen_ready, process, timeout=60)
    time.sleep(8)
    assert process.poll() is None
    screenshot = Path(os.environ.get("LINUXCNC_SCREENSHOT", tmp_path / "spike_qtdragon.png"))
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["import", "-window", "root", str(screenshot)], check=True, timeout=15)
    assert screenshot.stat().st_size > 10000
