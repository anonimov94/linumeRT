# SPDX-License-Identifier: GPL-2.0-or-later
"""Separate read-only host. No command channel or safety pins. Model-Author: Codex."""

import sys
import time
from pathlib import Path

from linumert_skin_preview import SkinPreview
from linumert_skin_readouts import AxisReadout, ProgramView
from linumert_skin_status import AXES, MAX_AGE, decode_sample
from PyQt5 import QtCore, QtWidgets


class StatusReader(QtCore.QObject):
    changed = QtCore.pyqtSignal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample = None
        self.started = 0.0
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(100)

    def clear(self, reason):
        self.sample = None
        self.changed.emit(None, reason)

    def failed(self, error):
        self.clear("reader-error")

    def finished(self, code, exit_status):
        payload = bytes(self.process.readAllStandardOutput())
        self.process.readAllStandardError()  # Drain diagnostics, never show untrusted rich text.
        if code or exit_status != QtCore.QProcess.NormalExit:
            self.clear("read-failed")
            return
        try:
            self.sample = decode_sample(payload, time.monotonic())
        except (ValueError, TypeError, KeyError):
            self.clear("invalid-status")
            return
        self.changed.emit(self.sample, "sampled")

    def tick(self):
        now = time.monotonic()
        if self.sample and not self.sample.fresh(now):
            self.clear("expired")
        if self.process.state() != QtCore.QProcess.NotRunning:
            if now - self.started > MAX_AGE:
                self.clear("reader-timeout")
                self.process.kill()
            return
        if now - self.started < 0.2:
            return
        self.started = now
        self.process.start(sys.executable, [str(Path(__file__).with_name("linumert_skin_status.py"))])

    def stop(self):
        self.timer.stop()
        self.process.kill()
        self.process.waitForFinished(1000)


class SkinMonitor(SkinPreview):
    def __init__(self, preferences=None):
        self.sample = None
        self.reason = "waiting"
        super().__init__(preferences, standalone=True)  # No offline scenes in a live host.
        self.reader = StatusReader(self)
        self.reader.changed.connect(self.present)

    def refresh(self):
        super().refresh()
        self.banner.setWordWrap(True)
        pl = self.preferences.language == "pl"
        self.banner.setText(
            "Monitor LinuxCNC · TYLKO ODCZYT · G53 mm/° · alarmy i sterowanie w głównym HMI"
            if pl else "LinuxCNC monitor · READ ONLY · G53 mm/° · alarms and control in main HMI")
        # Remove the sample G-code entirely; do not imply it is the controller's program.
        for view in self.workspace.findChildren(ProgramView):
            view.findChild(QtWidgets.QPlainTextEdit).clear()
            view.findChild(QtWidgets.QLabel).setText(
                "Program niepodłączony" if pl else "Program not connected")
        for label in self.workspace.findChildren(QtWidgets.QLabel):
            if label.property("heading") and label.text().startswith("DRO"):
                label.setText("G53 / " + self.workspace.AXES + " · mm/°")
        self.present(self.sample, self.reason)

    def present(self, sample, reason):
        if sample and not sample.fresh(time.monotonic()):
            sample, reason = None, "expired"
        self.sample, self.reason = sample, reason
        pl = self.preferences.language == "pl"
        self.status.setTextFormat(QtCore.Qt.PlainText)
        if sample:
            estop = ("AKTYWNY" if pl else "ACTIVE") if sample.estop else (
                "nieaktywny (NML)" if pl else "inactive (NML)")
            self.status.setText(
                f"{sample.mode} · {sample.task} · {sample.interpreter} · E-STOP: {estop}\n"
                + ("Odczyt NML; świeżość producenta niepotwierdzona" if pl else
                   "NML sampled; producer freshness unverified"))
        else:
            self.status.setText(("Status niedostępny" if pl else "Status unavailable")
                                + f" · {reason} · E-STOP: — · G53: —")
        values = dict(zip(AXES, sample.positions, strict=True)) if sample else {}
        for view in self.workspace.findChildren(AxisReadout):
            view.set_positions(values)

    def closeEvent(self, event):
        self.reader.stop()
        super().closeEvent(event)
