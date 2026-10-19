# SPDX-License-Identifier: GPL-2.0-or-later
"""JOG/MDI, wrzeciono i wybór narzędzia. Model-Author: Codex."""
from PyQt5 import QtWidgets

import linumert_shell_model as model


class OperatorControls(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.buttons = {}
        layout = QtWidgets.QVBoxLayout(self)
        self.specialist = QtWidgets.QCheckBox("Specjalista — wycofanie JOG (maks. 100 mm/s)")
        self.specialist.toggled.connect(shell.set_specialist)
        layout.addWidget(self.specialist)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("JOG mm/s"))
        self.speed = QtWidgets.QDoubleSpinBox()
        self.speed.setRange(0.0001, 100)
        self.speed.setDecimals(4)
        self.speed.setKeyboardTracking(False)
        self.speed.setValue(10)
        row.addWidget(self.speed)
        row.addWidget(QtWidgets.QLabel("Krok mm"))
        self.increment = QtWidgets.QComboBox()
        self.increment.addItems(["ciągły", "10", "1", "0.1", "0.01", "0.001", "0.0001"])
        row.addWidget(self.increment)
        layout.addLayout(row)
        jog = QtWidgets.QHBoxLayout()
        for axis in shell.s.axes:
            for direction, sign in ((-1, "−"), (1, "+")):
                btn = QtWidgets.QPushButton(axis + sign)
                btn.pressed.connect(lambda a=axis, d=direction: self.jog(a, d))
                btn.released.connect(lambda a=axis: self.jog(a, 0))
                jog.addWidget(btn)
                self.buttons[f"jog_{axis}{direction}"] = btn
        layout.addLayout(jog)
        row = QtWidgets.QHBoxLayout()
        self.mdi = QtWidgets.QLineEdit()
        self.mdi.setPlaceholderText("MDI, np. G0 X10")
        self.mdi.returnPressed.connect(self.send_mdi)
        row.addWidget(self.mdi, 1)
        self.button(row, "mdi", "Wykonaj MDI", self.send_mdi)
        layout.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        self.rpm = QtWidgets.QSpinBox()
        self.rpm.setRange(0, int(getattr(shell.info, "MAX_SPINDLE_SPEED", 24000)))
        self.rpm.setValue(1000)
        self.rpm.setKeyboardTracking(False)
        self.rpm.setSuffix(" obr/min")
        row.addWidget(self.rpm)
        for key, text, direction in (("m3", "M3", 1), ("m4", "M4", -1), ("m5", "M5", 0)):
            self.button(row, key, text, lambda _checked=False, d=direction: self.spindle(d))
        layout.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        self.tool = QtWidgets.QSpinBox()
        self.tool.setRange(0, 99999)
        self.tool.setPrefix("T")
        self.tool.setKeyboardTracking(False)
        self.button(row, "previous", "Poprzednie", lambda: self.adjacent_tool(-1))
        row.addWidget(self.tool)
        self.button(row, "next", "Następne", lambda: self.adjacent_tool(1))
        self.button(row, "m6", "WYMIANA M6", self.change_tool)
        layout.addLayout(row)
        self.reason = QtWidgets.QLabel()
        self.reason.setWordWrap(True)
        layout.addWidget(self.reason)
        self.refresh()

    def button(self, row, key, text, slot):
        btn = QtWidgets.QPushButton(text)
        btn.clicked.connect(slot)
        row.addWidget(btn)
        self.buttons[key] = btn

    def jog(self, axis, direction):
        s = self.shell
        if direction and not s._allowed("jog"):
            return
        metric = getattr(s.info, "MACHINE_IS_METRIC", True)
        scale = 1 if metric else 25.4
        step = 0 if self.increment.currentIndex() == 0 else float(self.increment.currentText())
        s.action.JOG("XYZABCUVW".index(axis), direction,
                     min(self.speed.value(), 100) / scale, step / scale)

    def send_mdi(self):
        if self.mdi.text().strip() and self.shell._allowed("mdi"):
            self.shell.action.CALL_MDI(self.mdi.text().strip())
            self.mdi.clear()

    def spindle(self, direction):
        if direction == 0:
            self.shell.action.SET_SPINDLE_STOP()
        elif self.shell._allowed("mdi"):
            self.shell.action.SET_SPINDLE_ROTATION(direction, self.rpm.value())

    def adjacent_tool(self, direction):
        numbers = sorted(getattr(getattr(self.shell, "sim", None), "tools", {}))
        eligible = [n for n in numbers if (n - self.tool.value()) * direction > 0]
        if eligible:
            self.tool.setValue(eligible[0] if direction > 0 else eligible[-1])
        elif not numbers:
            self.tool.setValue(self.tool.value() + direction)

    def change_tool(self):
        if not self.shell._allowed("mdi"):
            return
        tool = self.tool.value()
        answer = QtWidgets.QMessageBox.question(self, "Wymiana narzędzia",
                                                f"Wykonać T{tool} M6? Wrzeciono zostanie zatrzymane.")
        if answer == QtWidgets.QMessageBox.Yes:
            self.shell.action.SET_SPINDLE_STOP()
            self.shell.action.CALL_MDI(f"T{tool} M6")

    def refresh(self):
        gates = model.gates(self.shell.s)
        self.specialist.blockSignals(True)
        self.specialist.setChecked(self.shell.s.specialist)
        self.specialist.blockSignals(False)
        for key, btn in self.buttons.items():
            gate = gates["jog" if key.startswith("jog_") else "mdi"]
            if key not in ("previous", "next", "m5"):
                btn.setEnabled(gate.enabled)
                btn.setToolTip(gate.reason)
        self.reason.setText(gates["jog"].reason or "Przytrzymaj JOG; zwolnienie zatrzymuje oś.")
