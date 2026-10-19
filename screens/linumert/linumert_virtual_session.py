# SPDX-License-Identifier: GPL-2.0-or-later
"""Jawny tryb wirtualny i powrót do HOME przez LinuxCNC. Model-Author: Codex."""
import configparser
import time

from PyQt5 import QtCore, QtWidgets


def virtual_config(path):
    ini = configparser.ConfigParser(strict=False, interpolation=None)
    ini.read(path)
    return ini.get("LINUMERT", "VIRTUAL_MODE", fallback="0").strip() == "1"


class VirtualSession(QtCore.QObject):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.stage = ""
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)

    def start(self):
        s = self.shell
        if not s.s.virtual:
            return
        if QtWidgets.QMessageBox.question(None, "Wirtualny bliźniak",
                "Zatrzymać program, odnowić materiał i wrócić do HOME z konfiguracji maszyny?"
                ) != QtWidgets.QMessageBox.Yes:
            return
        s.action.ABORT()
        s.action.SET_SPINDLE_STOP()
        s.sim.reset_stock()
        s.s.specialist = False
        s.sim.client.send(cmd="recovery", on=True)
        s.reset_alarms(True)
        self.stage = "power"
        self.deadline = time.monotonic() + 120
        self.timer.start(250)

    def tick(self):
        s = self.shell
        if time.monotonic() > self.deadline:
            s.show_alarm("err", "Reset bliźniaka: przekroczony czas; sprawdź bazowanie i safety")
            self.finish()
            return
        if self.stage == "power" and not s.s.estop:
            s.action.SET_MACHINE_STATE(True)
            self.stage = "home"
        elif self.stage == "home" and s.s.machine_on and not s.s.running:
            s.action.SET_MANUAL_MODE()
            s.action.SET_MACHINE_HOMING(-1)
            self.homing_at = time.monotonic()
            self.stage = "wait"
        elif self.stage == "wait" and time.monotonic() - self.homing_at > 2:
            if s.s.estop or not s.s.machine_on:
                self.finish()
            elif s.s.all_homed and not s.s.running:
                s.reset_alarms(False)
                self.finish()

    def finish(self):
        self.timer.stop()
        self.stage = ""
        self.shell.sim.client.send(cmd="recovery", on=False)
