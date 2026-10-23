# SPDX-License-Identifier: GPL-2.0-or-later
"""Actual NML -> process -> Qt -> skin, no CNC commands. Model-Author: Codex."""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from rip_support import stop_linuxcnc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screens/linumert"))
pytestmark = pytest.mark.linuxcnc


def test_read_only_monitor_loss_and_reconnect(tmp_path):
    from linumert_skin_monitor import SkinMonitor
    from linumert_skin_readouts import AxisReadout
    from PyQt5 import QtWidgets

    source = Path(os.environ.get("LINUXCNC_DIR", "/nonexistent")) / "configs/sim/axis"
    if not source.exists():
        source = Path("/usr/share/doc/linuxcnc/examples/sample-configs/sim/axis")
    assert source.exists(), "LinuxCNC sim configuration required"
    work = tmp_path / "axis"
    work.mkdir()
    for entry in source.iterdir():
        if entry.is_file():
            shutil.copy2(entry, work / entry.name)
    ini = work / "axis.ini"
    text = re.sub(r"(?m)^DISPLAY\s*=.*$", "DISPLAY = halui", ini.read_text())
    text = re.sub(r"(?m)^HALUI\s*=.*$", "", text)
    text = re.sub(r"(?m)^HALFILE\s*=.*axis_manualtoolchange.hal.*$", "", text)
    ini.write_text(text)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = SkinMonitor()
    window.show()
    cnc = None

    def until(predicate, timeout=15):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            app.processEvents()
            if predicate():
                return
            time.sleep(.02)
        raise AssertionError(f"Monitor timeout: {window.reason}; {window.status.text()}")

    evidence = Path("build/skin-monitor")
    evidence.mkdir(parents=True, exist_ok=True)
    def start():
        return subprocess.Popen(["linuxcnc", "-r", str(ini)], cwd=work,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
    try:
        # Start monitor FIRST: unavailable NML/tool mmap must be recoverable.
        until(lambda: window.reason != "waiting")
        assert window.sample is None
        cnc = start()
        until(lambda: window.sample is not None)
        first = window.sample
        assert first.estop and not first.enabled
        assert first.positions[:3] == pytest.approx((0, 0, 0))
        assert first.positions[3:] == (None,) * 6
        dro = window.workspace.findChild(AxisReadout)
        assert dro.display_value("X") == "0.000"
        assert dro.display_value("A") == "—.———"
        assert all(not control.isEnabled() for control in window.controls.values())
        app.processEvents()
        assert window.grab().save(str(evidence / "connected.png"))
        stop_linuxcnc(cnc, None, work)
        cnc = None
        until(lambda: window.sample is None, timeout=3)
        assert dro.display_value("X") == "—.———"
        assert "E-STOP: —" in window.status.text()
        app.processEvents()
        assert window.grab().save(str(evidence / "unavailable.png"))
        cnc = start()
        until(lambda: window.sample is not None)
        assert window.sample.estop and not window.sample.enabled
        assert window.sample.acquired_at > first.acquired_at
        app.processEvents()
        assert window.grab().save(str(evidence / "reconnected.png"))
        (evidence / "result.json").write_text(json.dumps({
            "connection": True, "loss": True, "reconnect": True,
            "commands_sent": 0, "estop_remained_active": True,
            "environment": "LinuxCNC sim, Qt/Xvfb; see test log for version",
        }, indent=2) + "\n")
    finally:
        window.close()
        if cnc:
            stop_linuxcnc(cnc, None, work)
            (evidence / "controller.log").write_text(cnc.stdout.read())
