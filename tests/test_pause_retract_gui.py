# SPDX-License-Identifier: GPL-2.0-or-later
"""Click actual D38 widgets, including Action guards. Model-Author: Codex."""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("PyQt5"), "PyQt5 unavailable")
class PauseRetractGuiTests(unittest.TestCase):
    def test_click_retract_and_return_with_both_correction_sides(self):
        root = Path(__file__).resolve().parents[1]
        script = r'''
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace as NS
from dataclasses import replace
from PyQt5 import QtCore, QtWidgets
from linumert_pause_retract import RetractControl, RetractPanel, PauseSnapshot

class Pin:
    def set(self, value): self.value = value

class Action:
    __module__ = "qtvcp.test_retract"
    calls = []
    def PAUSE(self): self.calls.append("resume")
    def RUN(self): self.calls.append("run")
    STEP = JOG = CALL_MDI = SET_MANUAL_MODE = SET_MDI_MODE = SET_AUTO_MODE = RUN

app = QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as d:
    ini = Path(d) / "test.ini"
    ini.write_text("[LINUMERT]\nVIRTUAL_MODE=1\nRESUME_RETRACT_HEIGHT=3.1234\n"
                   "RESUME_RETRACT_FEED=123\n[KINS]\nKINEMATICS=trivkins coordinates=XYZ\n")
    for side in (410, 420):
        shell = QtCore.QObject()
        shell.info = NS(INIPATH=str(ini), MACHINE_IS_METRIC=True)
        shell.s = NS(axes=("X", "Y", "Z"))
        shell.hmi_pins = {k: Pin() for k in ("retract_own", "retract_target")}
        shell.action = Action()
        alarms = []
        shell.show_alarm = lambda *a: alarms.append(a)
        c = RetractControl(shell)
        c.timer.stop()
        base = PauseSnapshot(True, True, True, True, ("part.ngc", side), -20, 0, 0, -120, 0)
        c.snapshot = lambda: replace(base, offset=c.model.target, requested=c.model.target)
        c.last = base
        panel = RetractPanel(c)
        assert panel.height.value() == 3.1234
        assert panel.feed.value() == 123
        panel.height.setValue(2)
        panel.withdraw.click()
        assert c.model.active and shell.hmi_pins["retract_own"].value
        Action().PAUSE()
        assert alarms and not Action.calls
        for _ in range(100):
            c._time = time.monotonic() - 0.05
            c.tick()
        assert c.model.phase == "retracted"
        panel.resume_button.click()
        for _ in range(100):
            c._time = time.monotonic() - 0.05
            c.tick()
        assert not c.model.active
        assert Action.calls == ["resume"]
        assert not shell.hmi_pins["retract_own"].value
        assert shell.hmi_pins["retract_target"].value == 0
        Action.calls.clear()
        panel.close()
    for key, value in (("RESUME_RETRACT_HEIGHT", "nan"),
                       ("RESUME_RETRACT_HEIGHT", "100.01"),
                       ("RESUME_RETRACT_HEIGHT", "0"),
                       ("RESUME_RETRACT_FEED", "inf"),
                       ("RESUME_RETRACT_FEED", "501"),
                       ("RESUME_RETRACT_FEED", "bad")):
        ini.write_text(f"[LINUMERT]\nVIRTUAL_MODE=1\n{key}={value}\n"
                       "[KINS]\nKINEMATICS=trivkins coordinates=XYZ\n")
        c = RetractControl(shell)
        c.timer.stop()
        c.last = base
        panel = RetractPanel(c)
        assert not c.available and not panel.withdraw.isEnabled()
        assert "błędna konfiguracja D38" in panel.message.text()
        c.withdraw(2, 60)
        assert not c.model.active and "błędna konfiguracja D38" in c.model.message
        panel.close()
    ini.write_text("[LINUMERT]\nVIRTUAL_MODE=1\n[KINS]\nKINEMATICS=trivkins coordinates=XYZ\n")
    c = RetractControl(shell)
    c.timer.stop()
    panel = RetractPanel(c)
    assert c.available and panel.height.value() == 10 and panel.feed.value() == 200
    panel.close()
'''
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
                   PYTHONPATH=str(root / "screens/linumert"))
        run = subprocess.run([sys.executable, "-c", script], env=env, cwd=root,
                             capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
