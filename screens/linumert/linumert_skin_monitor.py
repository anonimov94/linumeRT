# SPDX-License-Identifier: GPL-2.0-or-later
"""Separate read-only host. No command channel or safety pins. Model-Author: Codex."""

import sys
import time
from pathlib import Path

from linumert_skin_controls import EmergencyReadout
from linumert_skin_preview import SkinPreview
from linumert_skin_readouts import AxisReadout, FeedReadout, ProgramView, ToolReadout
from linumert_skin_status import AXES, MAX_AGE, decode_sample
from PyQt5 import QtCore, QtWidgets

LOADER = Path(__file__).with_name("linumert_neon_loader.py")
MAX_SOURCE = 4 * 1024 * 1024


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
        # Completion can reach Qt before an overdue timer after a busy event loop.
        if time.monotonic() - self.started > MAX_AGE:
            self.clear("reader-timeout")
            return
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


class ProgramLoader(QtCore.QObject):
    """Ścieżka aktywnego programu z interpretera LinuxCNC w jednorazowym procesie (poza GUI).

    Model-Author: Claude. Tylko odczyt pliku; brak komend LinuxCNC. NIEZWERYFIKOWANE NA SPRZĘCIE.
    """

    loaded = QtCore.pyqtSignal(object, str)    # (Toolpath | None, opis dla operatora)

    def __init__(self, parent=None, timeout_s=None):
        super().__init__(parent)
        from linumert_neon_loader import TIMEOUT_S
        self.path = ""
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._failed)
        self.deadline = QtCore.QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self._timeout)
        self.timeout_ms = int((timeout_s or TIMEOUT_S) * 1000)

    def start(self, path):
        self.stop()
        self.path = path
        self.process.start(sys.executable, [str(LOADER), path])
        self.deadline.start(self.timeout_ms)

    def stop(self):
        self.deadline.stop()
        if self.process.state() != QtCore.QProcess.NotRunning:
            self.process.blockSignals(True)
            self.process.kill()
            self.process.waitForFinished(1000)
            self.process.blockSignals(False)

    def _timeout(self):
        self.stop()
        self.loaded.emit(None, "Przekroczono czas wczytywania ścieżki programu.")

    def _failed(self, error):
        if error == QtCore.QProcess.FailedToStart:
            self.deadline.stop()
            self.loaded.emit(None, "Nie można uruchomić wczytywania ścieżki programu.")

    def _finished(self, code, exit_status):
        from linumert_neon_loader import toolpath_from_json
        self.deadline.stop()
        payload = bytes(self.process.readAllStandardOutput())
        self.process.readAllStandardError()
        try:
            with open(self.path, encoding="utf-8", errors="replace") as fh:
                source = fh.read(MAX_SOURCE).splitlines()
        except OSError:
            source = []
        try:
            toolpath = toolpath_from_json(payload, source)
        except (ValueError, TypeError) as exc:
            self.loaded.emit(None, f"Ścieżka niewczytana: {exc}")
            return
        self.loaded.emit(toolpath, f"{Path(self.path).name} · {len(toolpath)} ruchów")


class SkinMonitor(SkinPreview):
    def __init__(self, preferences=None):
        self.sample = None
        self.reason = "waiting"
        self.program_file = None
        super().__init__(preferences, standalone=True)  # No offline scenes in a live host.
        self.shared["program_note"] = "Program niewczytany w LinuxCNC"
        self.loader = ProgramLoader(self)
        self.loader.loaded.connect(self.program_loaded)
        self.reader = StatusReader(self)
        self.reader.changed.connect(self.present)

    def program_loaded(self, toolpath, note):
        """Nowa scena Classic × Neon na żywo (albo uczciwy opis błędu) i przebudowa ekranu."""
        from linumert_neon_view import PathScene, stock_box_for
        old = self.shared.pop("path_scene", None)
        if old is not None:
            old.timer.stop()
            old.deleteLater()
        self.shared["program_note"] = note
        if toolpath is not None and len(toolpath):
            self.shared["path_scene"] = PathScene(toolpath, live=True, parent=self,
                                                  stock_box=stock_box_for(toolpath))
        elif toolpath is not None:
            self.shared["program_note"] = note + " · brak ruchów"
        self.refresh()

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
        if "alarms" in self.cards:
            labels = [label for label in self.cards["alarms"].findChildren(QtWidgets.QLabel)
                      if not label.property("heading")]
            for index, label in enumerate(labels):
                label.setText(("Alarmy niepodłączone · główne HMI" if pl else
                               "Alarms not connected · main HMI") if index == 0 else "")
        self.estop_labels = []
        # A live read-only host must not present a decorative red mushroom.
        for indicator in self.console.findChildren(EmergencyReadout):
            label = QtWidgets.QLabel("E-STOP: —")
            label.setWordWrap(True)
            label.setMinimumWidth(100)
            self.console.layout().replaceWidget(indicator, label)
            indicator.hide()
            indicator.deleteLater()
            self.estop_labels.append(label)
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
        for label in self.estop_labels:
            label.setText("E-STOP\nNML: " + (estop if sample else "—"))
        if "status" in self.cards:
            for label in self.cards["status"].findChildren(QtWidgets.QLabel):
                if not label.property("heading"):
                    label.setText(sample.task if sample else (
                        "Status niedostępny" if pl else "Status unavailable"))
        values = dict(zip(AXES, sample.positions, strict=True)) if sample else {}
        for view in self.workspace.findChildren(AxisReadout):
            view.set_positions(values)
        self.follow_program(sample)
        for view in self.workspace.findChildren(FeedReadout):
            view.set_readings(sample.feed_mm_min if sample else None,
                              sample.spindle_rpm if sample else None)
        for view in self.workspace.findChildren(ToolReadout):
            view.set_readings(sample.tool_number if sample else None,
                              sample.tool_diameter if sample else None,
                              sample.tool_length if sample else None)
        scene = self.shared.get("path_scene")
        source = scene.toolpath.source if sample and scene else None
        for view in self.workspace.findChildren(ProgramView):
            view.set_source(source, sample.file if sample else "",
                            sample.motion_line if sample else 0,
                            self.shared.get("program_note", "") if sample else (
                                "Status niedostępny" if pl else "Status unavailable"))

    def follow_program(self, sample):
        """Classic × Neon: aktywny plik → wczytanie ścieżki; linia i pozycja → następny punkt."""
        if not hasattr(self, "loader"):
            return
        if sample is None:
            self.loader.stop()
            self.program_file = None  # Recovery must reload even the same filename.
            if "path_scene" in self.shared:
                self.program_loaded(None, "Status niedostępny · ścieżka nieaktualna")
            return
        if sample.file != self.program_file:
            self.program_file = sample.file
            self.loader.stop()
            if sample.file:
                self.shared["program_note"] = "Wczytywanie ścieżki programu…"
                # Never follow program B's line/position on program A's geometry.
                if "path_scene" in self.shared:
                    self.program_loaded(None, self.shared["program_note"])
                self.loader.start(sample.file)
            else:
                self.loader.stop()
                self.program_loaded(None, "Program niewczytany w LinuxCNC")
                return
        scene = self.shared.get("path_scene")
        position = sample.work_position()
        if scene is not None and position is not None:
            scene.follow(sample.motion_line, position)
            scene.reported_dtg = sample.distance_to_go

    def closeEvent(self, event):
        self.reader.stop()
        self.loader.stop()
        super().closeEvent(event)
