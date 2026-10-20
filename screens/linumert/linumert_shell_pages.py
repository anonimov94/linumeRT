# SPDX-License-Identifier: GPL-2.0-or-later
"""Widoki nakładki linumeRT poza „Maszyna”: Diagnostyka, Produkcja, Start (HMI_WORKFLOW).

Model-Author: Claude · HMI etap 2 (2026-10-19).

Strona dostaje referencję powłoki (`LinumertShell`): stan z `shell.s`, kolory z `shell.c`,
akcje wyłącznie przez ACTION QtVCP. Odczyt HAL tylko do wyświetlenia (`hal.get_value`).
`refresh()` woła powłoka co 0,5 s, gdy strona jest widoczna.
"""

from __future__ import annotations

import os
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Action, Info, Status

import linumert_shell_model as model

STATUS = Status()
ACTION = Action()
INFO = Info()


def _hal(name: str, default=None):
    try:
        import hal

        return hal.get_value(name)
    except Exception:  # noqa: BLE001 - brak pinu (konfiguracja bez Plant) albo HAL
        return default


def _label(text: str = "", name: str = "", **props) -> QtWidgets.QLabel:
    lab = QtWidgets.QLabel(text)
    if name:
        lab.setObjectName(name)
    for key, value in props.items():
        lab.setProperty(key, value)
    return lab


def _restyle(widget: QtWidgets.QWidget, **props) -> None:
    changed = False
    for key, value in props.items():
        if widget.property(key) != value:
            widget.setProperty(key, value)
            changed = True
    if changed:
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def card(title: str, right: str = "") -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout,
                                                QtWidgets.QLabel]:
    frame = QtWidgets.QFrame()
    frame.setObjectName("lrtCard")
    lay = QtWidgets.QVBoxLayout(frame)
    lay.setContentsMargins(16, 12, 16, 14)
    lay.setSpacing(8)
    head = QtWidgets.QHBoxLayout()
    head.addWidget(_label(title.upper(), "lrtCardTitle"))
    head.addStretch(1)
    side = _label(right, "lrtMuted")
    head.addWidget(side)
    lay.addLayout(head)
    return frame, lay, side


def _table(headers: list[str]) -> QtWidgets.QTableWidget:
    table = QtWidgets.QTableWidget(0, len(headers))
    table.setObjectName("lrtTable")
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
    table.setFocusPolicy(QtCore.Qt.NoFocus)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
    table.setShowGrid(False)
    return table


def _set_row(table: QtWidgets.QTableWidget, row: int, values: list[str],
             colors: dict[int, str] | None = None) -> None:
    if table.rowCount() <= row:
        table.setRowCount(row + 1)
    for col, value in enumerate(values):
        item = table.item(row, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            table.setItem(row, col, item)
        if item.text() != value:
            item.setText(value)
        color = (colors or {}).get(col)
        if color:
            item.setForeground(QtGui.QColor(color))


class DiagPage(QtWidgets.QWidget):
    """Diagnostyka: łącze LRT-NET, napędy CiA 402 (Plant), osie LinuxCNC, wejścia, komunikaty."""

    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.c = shell.c
        root = model.repo_root()
        try:
            with open(os.path.join(root, "plant", "core", "drive.h"), encoding="utf-8") as fh:
                self.faults = model.drive_fault_codes(fh.read())
        except OSError:
            self.faults = {}
        try:
            import yaml

            with open(os.path.join(root, "core", "linumert", "alarms", "catalog.yaml"),
                      encoding="utf-8") as fh:
                self.texts = model.catalog_texts(yaml.safe_load(fh))
        except (OSError, ImportError, ValueError):
            self.texts = {}
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        grid.addWidget(self._link_card(), 0, 0)
        grid.addWidget(self._inputs_card(), 1, 0)
        grid.addWidget(self._drives_card(), 0, 1)
        grid.addWidget(self._joints_card(), 1, 1)
        grid.addWidget(self._log_card(), 2, 0, 1, 2)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        grid.setRowStretch(2, 1)
        self.doctor_button = QtWidgets.QPushButton("Raport środowiska…")
        self.doctor_button.setMinimumHeight(44)
        self.doctor_button.clicked.connect(self.show_environment)
        grid.addWidget(self.doctor_button, 3, 0, 1, 2)

    def show_environment(self):
        from linumert_doctor_dialog import DoctorDialog

        DoctorDialog(self).exec_()

    # ---- karty ----------------------------------------------------------------------------
    def _link_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_link = card("Łącze LRT-NET (Plant)", "")
        self.link_values: dict[str, QtWidgets.QLabel] = {}
        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(16)
        for i, (pin, label) in enumerate(model.LINK_COUNTERS):
            form.addWidget(_label(label, "lrtMuted"), i, 0)
            value = _label("—", "lrtValue")
            value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            form.addWidget(value, i, 1)
            self.link_values[pin] = value
        lay.addLayout(form)
        lay.addStretch(1)
        return frame

    def _drives_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_drives = card("Napędy CiA 402", "")
        self.drives = _table(["Staw", "Stan", "6041h", "Błąd nadążania", "Moment ‰", "Awaria"])
        lay.addWidget(self.drives)
        return frame

    def _joints_card(self) -> QtWidgets.QWidget:
        frame, lay, _side = card("Osie LinuxCNC", "")
        self.joints = _table(["Staw", "Bazowany", "Błąd nadążania", "Krańcówki", "Napęd"])
        lay.addWidget(self.joints)
        return frame

    def _inputs_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_inputs = card("Wejścia z Plant (din)", "")
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(4)
        self.inputs = []
        for bit in range(32):
            cell = _label(f"{bit:02d}", "lrtBit", on="false")
            cell.setAlignment(QtCore.Qt.AlignCenter)
            cell.setToolTip(f"lrt-net.0.din-{bit:02d} (1 = obwód zamknięty)")
            grid.addWidget(cell, bit // 8, bit % 8)
            self.inputs.append(cell)
        lay.addLayout(grid)
        lay.addStretch(1)
        return frame

    def _log_card(self) -> QtWidgets.QWidget:
        frame, lay, _side = card("Historia komunikatów", "ostatnie 200")
        self.log = QtWidgets.QListWidget()
        self.log.setObjectName("lrtLog")
        lay.addWidget(self.log)
        return frame

    # ---- dane -----------------------------------------------------------------------------
    def add_log(self, level: str, text: str) -> None:
        item = QtWidgets.QListWidgetItem(f"{time.strftime('%H:%M:%S')}  {text}")
        item.setForeground(QtGui.QColor(
            {"err": self.c["err"], "warn": self.c["amber"]}.get(level, self.c["fg2"])))
        self.log.insertItem(0, item)
        while self.log.count() > 200:
            self.log.takeItem(self.log.count() - 1)

    def refresh(self) -> None:
        plant = _hal("lrt-net.0.connected")
        if plant is None:
            self.lbl_link.setText("brak komponentu lrt_net: symulator LinuxCNC")
            for value in self.link_values.values():
                value.setText("—")
        else:
            self.lbl_link.setText("połączony" if plant else "BRAK ŁĄCZA")
            for pin, value in self.link_values.items():
                value.setText(str(_hal(f"lrt-net.0.{pin}", "—")))
        self._refresh_drives(plant is not None)
        self._refresh_joints()
        self._refresh_inputs(plant is not None)

    def _axis_of(self, joint: int) -> str:
        try:
            return INFO.GET_NAME_FROM_JOINT.get(joint, "?").upper()[:1]
        except AttributeError:
            return "?"

    def _refresh_drives(self, plant: bool) -> None:
        if not plant:
            self.lbl_drives.setText("napędy z Plant niedostępne (symulator)")
            self.drives.setRowCount(0)
            return
        rows = 0
        for n in range(8):
            sw = _hal(f"lrt-net.0.axis.{n}.statusword")
            if sw is None:
                break
            axis = self._axis_of(n)
            name, level = model.cia402_state(int(sw))
            code = int(_hal(f"lrt-net.0.axis.{n}.error-code", 0) or 0)
            ferror = float(_hal(f"lrt-net.0.axis.{n}.ferror", 0.0) or 0.0)
            torque = float(_hal(f"lrt-net.0.axis.{n}.torque", 0.0) or 0.0)
            color = {"ok": self.c["ok"], "warn": self.c["amber"], "err": self.c["err"]}.get(
                level, self.c["info"])
            _set_row(self.drives, n, [f"{n} ({axis})", name, f"0x{int(sw):04X}",
                                      f"{ferror:+.4f}", f"{torque:.0f}",
                                      model.drive_error_text(code, self.faults, self.texts, axis)],
                     {1: color, 5: self.c["err"] if code else self.c["fg3"]})
            rows += 1
        self.drives.setRowCount(rows)
        faults = _hal("lrt-net.0.drive-fault")
        self.lbl_drives.setText(f"{rows} napędów" + (" · FAULT" if faults else ""))

    def _refresh_joints(self) -> None:
        stat = STATUS.stat
        try:
            joints = stat.joints
        except AttributeError:
            return
        for j in range(joints):
            data = stat.joint[j]
            limits = ("MIN " if data["min_hard_limit"] else "") + \
                     ("MAX" if data["max_hard_limit"] else "")
            ok = self.c["ok"]
            _set_row(self.joints, j, [
                f"{j} ({self._axis_of(j)})", "tak" if data["homed"] else "nie",
                f"{data['ferror_current']:+.4f}", limits.strip() or "—",
                "błąd" if data["fault"] else ("włączony" if data["enabled"] else "wyłączony")],
                {1: ok if data["homed"] else self.c["amber"],
                 3: self.c["err"] if limits.strip() else self.c["fg3"],
                 4: self.c["err"] if data["fault"] else ok if data["enabled"] else self.c["fg2"]})
        self.joints.setRowCount(joints)

    def _refresh_inputs(self, plant: bool) -> None:
        if not plant:
            self.lbl_inputs.setText("symulator: brak wejść Plant")
        else:
            estop = _hal("lrt-net.0.estop-open")
            self.lbl_inputs.setText("pętla E-STOP otwarta" if estop else "pętla E-STOP zamknięta")
        for bit, cell in enumerate(self.inputs):
            on = bool(_hal(f"lrt-net.0.din-{bit:02d}", False)) if plant else False
            _restyle(cell, on="true" if on else "false")


class ProductionPage(QtWidgets.QWidget):
    """Produkcja: program i postęp, czas pracy, korekcje F/G0/S, opcje, start od linii."""

    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.clock = model.RunClock()
        self._last_interp = "idle"
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        grid.addWidget(self._program_card(), 0, 0, 2, 1)
        grid.addWidget(self._override_card(), 0, 1)
        grid.addWidget(self._options_card(), 1, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setRowStretch(1, 1)

    # ---- karty ----------------------------------------------------------------------------
    def _program_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_file = card("Program", "brak programu")
        stats = QtWidgets.QHBoxLayout()
        self.lbl_line = _label("—", "lrtTitle")
        self.lbl_time = _label("00:00", "lrtTitle")
        self.lbl_pct = _label("0 %", "lrtTitle")
        for title, value in (("Linia", self.lbl_line), ("Czas pracy", self.lbl_time),
                             ("Postęp", self.lbl_pct)):
            box = QtWidgets.QVBoxLayout()
            box.addWidget(_label(title, "lrtMuted"))
            box.addWidget(value)
            stats.addLayout(box)
            stats.addStretch(1)
        lay.addLayout(stats)
        self.bar = QtWidgets.QProgressBar()
        self.bar.setTextVisible(False)
        lay.addWidget(self.bar)
        self.code = []
        for _ in range(12):
            row = _label("", "lrtCode", current="false")
            row.setTextFormat(QtCore.Qt.PlainText)
            lay.addWidget(row)
            self.code.append(row)
        lay.addStretch(1)
        return frame

    def _override_card(self) -> QtWidgets.QWidget:
        frame, lay, _side = card("Korekcje", "")
        self.sliders: dict[str, tuple[QtWidgets.QSlider, QtWidgets.QLabel]] = {}
        self.reset_buttons: dict[str, QtWidgets.QPushButton] = {}
        spec = (
            ("feed", "Posuw F", 0, max(round(INFO.MAX_FEED_OVERRIDE), 100)),
            ("rapid", "Przejazdy G0", 0, 100),
            ("spindle", "Wrzeciono S", max(round(INFO.MIN_SPINDLE_OVERRIDE), 0),
             max(round(INFO.MAX_SPINDLE_OVERRIDE), 100)),
        )
        for key, title, lo, hi in spec:
            head = QtWidgets.QHBoxLayout()
            head.addWidget(_label(title, "lrtMuted"))
            head.addStretch(1)
            value = _label("100 %", "lrtValue")
            head.addWidget(value)
            lay.addLayout(head)
            row = QtWidgets.QHBoxLayout()
            minus = QtWidgets.QPushButton("−10")
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setObjectName("lrtSlider")
            slider.setRange(lo, hi)
            slider.setValue(100)
            slider.setPageStep(10)
            plus = QtWidgets.QPushButton("+10")
            reset = QtWidgets.QPushButton("100 %")
            slider.valueChanged.connect(lambda v, k=key: self.set_override(k, v))
            minus.clicked.connect(lambda _c=False, s=slider: s.setValue(s.value() - 10))
            plus.clicked.connect(lambda _c=False, s=slider: s.setValue(s.value() + 10))
            reset.clicked.connect(lambda _c=False, s=slider: s.setValue(100))
            for wdg in (minus, slider, plus, reset):
                row.addWidget(wdg, 1 if wdg is slider else 0)
            lay.addLayout(row)
            self.sliders[key] = (slider, value)
            self.reset_buttons[key] = reset
        lay.addStretch(1)
        return frame

    def _options_card(self) -> QtWidgets.QWidget:
        frame, lay, _side = card("Opcje programu", "")
        row = QtWidgets.QHBoxLayout()
        self.chk_block = QtWidgets.QPushButton("Pomijaj bloki „/”")
        self.chk_block.setCheckable(True)
        self.chk_block.setToolTip("Block delete: linie zaczynające się od „/” są pomijane")
        self.chk_block.clicked.connect(lambda on: (ACTION.SET_BLOCK_DELETE_ON if on
                                                   else ACTION.SET_BLOCK_DELETE_OFF)())
        self.chk_m1 = QtWidgets.QPushButton("Stop opcjonalny M1")
        self.chk_m1.setCheckable(True)
        self.chk_m1.setToolTip("Optional stop: M1 zatrzymuje program")
        self.chk_m1.clicked.connect(lambda on: (ACTION.SET_OPTIONAL_STOP_ON if on
                                                else ACTION.SET_OPTIONAL_STOP_OFF)())
        row.addWidget(self.chk_block)
        row.addWidget(self.chk_m1)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addSpacing(8)
        lay.addWidget(_label("START OD LINII", "lrtCardTitle"))
        line = QtWidgets.QHBoxLayout()
        self.spin_line = QtWidgets.QSpinBox()
        self.spin_line.setObjectName("lrtSpin")
        self.spin_line.setRange(1, 1)
        self.btn_from_line = QtWidgets.QPushButton("Start od linii")
        self.btn_from_line.setProperty("role", "start")
        self.btn_from_line.clicked.connect(self.run_from_line)
        line.addWidget(self.spin_line, 1)
        line.addWidget(self.btn_from_line)
        lay.addLayout(line)
        self.lbl_from_line = _label("", "lrtMuted")
        self.lbl_from_line.setWordWrap(True)
        lay.addWidget(self.lbl_from_line)
        lay.addStretch(1)
        STATUS.connect("block-delete-changed", lambda _w, on: self.chk_block.setChecked(on))
        STATUS.connect("optional-stop-changed", lambda _w, on: self.chk_m1.setChecked(on))
        return frame

    # ---- akcje ----------------------------------------------------------------------------
    def set_override(self, key: str, value: int) -> None:
        {"feed": ACTION.SET_FEED_RATE, "rapid": ACTION.SET_RAPID_RATE,
         "spindle": ACTION.SET_SPINDLE_RATE}[key](value)

    def run_from_line(self, confirm: bool = True) -> None:
        line = self.spin_line.value()
        gate = model.run_from_line_gate(self.shell.s, line)
        if not gate.enabled:
            self.shell.show_alarm("warn", f"Niedostępne: {gate.reason}")
            return
        if confirm:
            box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Start od linii",
                                        model.RUN_FROM_LINE_WARNING.format(line=line),
                                        QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                        self)
            if box.exec_() != QtWidgets.QMessageBox.Ok:
                return
        ACTION.RUN(line)
        self.shell.h.add_status(f"Start programu od linii {line}")

    # ---- dane -----------------------------------------------------------------------------
    def on_state(self) -> None:
        """Woła powłoka przy każdej zmianie stanu (także gdy strona niewidoczna)."""
        s, now = self.shell.s, time.monotonic()
        if s.interp == "run" and self._last_interp == "idle":
            self.clock.reset()
        self.clock.update(s.interp, now)
        self._last_interp = s.interp
        for key, attr in (("feed", "feed_override"), ("rapid", "rapid_override"),
                          ("spindle", "spindle_override")):
            slider, value = self.sliders[key]
            pct = round(getattr(s, attr) * 100)
            if slider.value() != pct and not slider.isSliderDown():
                slider.blockSignals(True)
                slider.setValue(pct)
                slider.blockSignals(False)
            value.setText(f"{pct} %")

    def refresh(self) -> None:
        s, now = self.shell.s, time.monotonic()
        self.lbl_file.setText(os.path.basename(s.file) or "brak programu")
        total = max(s.total_lines, 1)
        self.lbl_line.setText(f"{s.line} / {s.total_lines}" if s.file else "—")
        self.lbl_time.setText(model.fmt_duration(self.clock.value(now)))
        pct = round(100 * min(s.line, total) / total) if s.file else 0
        self.lbl_pct.setText(f"{pct} %")
        self.bar.setRange(0, total)
        self.bar.setValue(min(s.line, total))
        rows = model.program_window(self.shell.program_lines, s.line, before=3, after=8)
        for label, row in zip(self.code, rows + [None] * len(self.code), strict=False):
            if row is None:
                label.setText("")
                continue
            n, code, current = row
            label.setText(f"N{n:<5} {code}")
            _restyle(label, current="true" if current else "false")
        self.spin_line.setRange(1, max(s.total_lines, 1))
        gate = model.run_from_line_gate(s, self.spin_line.value())
        self.btn_from_line.setEnabled(gate.enabled)
        self.lbl_from_line.setText(gate.reason if not gate.enabled else
                                   "Uruchomienie wymaga potwierdzenia (pomija wcześniejsze bloki).")


class StartPage(QtWidgets.QWidget):
    """Start: lista gotowości maszyny z akcjami i ostatnie komunikaty."""

    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.items: list[model.CheckItem] = []
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        frame, lay, self.lbl_ready = card("Gotowość maszyny", "")
        self.rows = QtWidgets.QGridLayout()
        self.rows.setHorizontalSpacing(16)
        self.rows.setVerticalSpacing(10)
        lay.addLayout(self.rows)
        self.row_widgets: dict[str, tuple] = {}
        lay.addStretch(1)
        self.btn_next = QtWidgets.QPushButton("Dalej: Produkcja")
        self.btn_next.setProperty("role", "start")
        self.btn_next.clicked.connect(lambda: self.shell.select_area("production"))
        lay.addWidget(self.btn_next, 0, QtCore.Qt.AlignRight)
        grid.addWidget(frame, 0, 0)
        frame, lay, _side = card("Ostatnie komunikaty", "pełna historia: Diagnostyka")
        self.recent = []
        for _ in range(8):
            row = _label("", "lrtMuted")
            row.setWordWrap(True)
            lay.addWidget(row)
            self.recent.append(row)
        lay.addStretch(1)
        grid.addWidget(frame, 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

    def _row(self, key: str, index: int) -> tuple:
        if key not in self.row_widgets:
            dot = _label("●", "lrtDot", level="info")
            title = _label("", "lrtTitleSmall")
            detail = _label("", "lrtMuted")
            btn = QtWidgets.QPushButton("")
            btn.clicked.connect(lambda _c=False, k=key: self._act(k))
            self.rows.addWidget(dot, index, 0)
            self.rows.addWidget(title, index, 1)
            self.rows.addWidget(detail, index, 2)
            self.rows.addWidget(btn, index, 3)
            self.rows.setColumnStretch(2, 1)
            self.row_widgets[key] = (dot, title, detail, btn)
        return self.row_widgets[key]

    def _act(self, key: str) -> None:
        item = next((i for i in self.items if i.key == key), None)
        if item is None or not item.action:
            return
        shell = self.shell
        {"estop": shell.toggle_estop, "power": shell.toggle_power, "home": shell.home_all,
         "program": lambda: shell.select_area("program"),
         "production": lambda: shell.select_area("production"),
         "diag": lambda: shell.select_area("diag")}[item.action]()

    def refresh(self) -> None:
        fault = _hal("lrt-net.0.drive-fault")
        self.items = model.checklist(self.shell.s, None if fault is None else bool(fault))
        for index, item in enumerate(self.items):
            dot, title, detail, btn = self._row(item.key, index)
            _restyle(dot, level=item.level)
            title.setText(item.label)
            detail.setText(item.detail)
            btn.setVisible(bool(item.action))
            btn.setText(model.ACTION_LABEL.get(item.action, ""))
        ready = model.ready_to_run(self.items)
        self.lbl_ready.setText("gotowa do pracy" if ready else "wymaga działań")
        self.btn_next.setEnabled(ready)
        log = self.shell.diag.log
        for i, row in enumerate(self.recent):
            row.setText(log.item(i).text() if i < log.count() else ("brak komunikatów" if i == 0
                                                                     else ""))
