# SPDX-License-Identifier: GPL-2.0-or-later
"""Widoki nakładki linumeRT poza „Maszyna”: Diagnostyka (i kolejne strony HMI_WORKFLOW).

Model-Author: Claude · HMI etap 2 (2026-10-19).

Strona dostaje referencję powłoki (`LinumertShell`): stan z `shell.s`, kolory z `shell.c`,
akcje wyłącznie przez ACTION QtVCP. Odczyt HAL tylko do wyświetlenia (`hal.get_value`).
`refresh()` woła powłoka co 0,5 s, gdy strona jest widoczna.
"""

from __future__ import annotations

import os
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Info, Status

import linumert_shell_model as model

STATUS = Status()
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
