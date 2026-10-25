# SPDX-License-Identifier: GPL-2.0-or-later
"""Opt-in presentation inside the existing QtVCP host. Model-Author: Codex.

The shell retains alarms, E-STOP, heartbeat, mode and manual controls. Cycle
buttons delegate to its existing guarded buttons. No new HAL or command owner.
"""

import json
import time

import linuxcnc
from PyQt5 import QtCore, QtWidgets

import linumert_shell_model as model
from linumert_skin_controls import SkinButton
from linumert_skin_monitor import SkinMonitor
from linumert_skin_readouts import ProgramView
from linumert_skin_status import decode_sample, read_status
from linumert_skin_strings import text


class OperatorSkin(SkinMonitor):
    """First integrated view; presentation choice is fixed at process startup."""

    def __init__(self, shell, preferences):
        self.shell = shell
        super().__init__(preferences)
        # The QtVCP process already owns STATUS; do not launch a second reader.
        self.reader.stop()
        self.setWindowFlags(QtCore.Qt.Widget)
        self.setMinimumSize(0, 0)
        shell.w.destroyed.connect(self.stop)

    def _replace_header(self, palette):
        super()._replace_header(palette)
        routes = {text(key, self.preferences): target for key, target in (
            ("machine", "machine"), ("program", "program"),
            ("tools", "tools"), ("diagnostics", "diag"), ("settings", "settings"))}
        for button in self.header.findChildren(SkinButton):
            target = routes.get(button.text())
            if target:
                button.clicked.disconnect()
                button.clicked.connect(lambda checked=False, area=target:
                                       self.shell.select_area(area))

    def refresh(self):
        super().refresh()
        pl = self.preferences.language == "pl"
        self.banner.setText(
            "Integracja HMI w toku · G53 mm/° · JOG, tryby i E-STOP na stałym pasku hosta"
            if pl else "HMI integration in progress · G53 mm/° · JOG, modes and E-STOP in host")
        for key, button in self.controls.items():
            button.clicked.connect(lambda checked=False, action=key: self.dispatch(action))
        # Until the first validated STATUS sample, every new console is disabled.
        for button in self.controls.values():
            button.setEnabled(False)

    def sync(self):
        """Use the existing STATUS object; a failed read clears the presentation."""
        try:
            payload = json.dumps(read_status(self.shell.status.stat, linuxcnc)).encode()
            sample = decode_sample(payload, time.monotonic())
        except Exception as exc:  # noqa: BLE001 - disable commands on any boundary failure
            self.present(None, f"{type(exc).__name__}: {exc}"[:300])
            for button in self.controls.values():
                button.setEnabled(False)
            return
        self.present(sample, "qtvcp-status")
        gates = model.gates(self.shell.s)
        for key, target in (("start", "start"), ("feed_hold", "pause"), ("stop", "stop")):
            button = self.controls[key]
            button.setEnabled(not sample.estop and sample.enabled and gates[target].enabled
                              and self.shell.buttons[target].isEnabled())
            button.setToolTip(gates[target].reason)
        # Show the controller's current source window, never the offline example.
        source = model.program_window(self.shell.program_lines, self.shell.s.line)
        for view in self.workspace.findChildren(ProgramView):
            editor = view.findChild(QtWidgets.QPlainTextEdit)
            content = "\n".join(f"{number:04}  {line}" for number, line, _active in source)
            if editor.toPlainText() != content:
                editor.setPlainText(content)
            caption = view.findChild(QtWidgets.QLabel)
            caption.setTextFormat(QtCore.Qt.PlainText)
            caption.setText(self.shell.s.file or ("Brak programu" if
                            self.preferences.language == "pl" else "No program"))
        if "alarms" in self.cards:
            labels = [label for label in self.cards["alarms"].findChildren(QtWidgets.QLabel)
                      if not label.property("heading")]
            for index, label in enumerate(labels):
                label.setTextFormat(QtCore.Qt.PlainText)
                label.setText(self.shell.s.alarm.text if index == 0 and self.shell.s.alarm
                              else "")

    def dispatch(self, key):
        # Re-read before every request; no command can use an old enabled state.
        self.sync()
        target = {"start": "start", "feed_hold": "pause", "stop": "stop"}.get(key)
        if (target and self.sample and self.sample.fresh(time.monotonic())
                and not self.sample.estop and self.sample.enabled
                and model.gates(self.shell.s)[target].enabled):
            self.shell.buttons[target].click()

    def stop(self, *_args):
        self.reader.stop()
        self.loader.stop()
        scene = self.shared.get("path_scene")
        if scene is not None:
            scene.timer.stop()

    def closeEvent(self, event):  # noqa: N802 - Qt virtual method
        self.stop()
        super().closeEvent(event)
