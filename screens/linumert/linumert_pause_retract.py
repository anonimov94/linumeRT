# SPDX-License-Identifier: GPL-2.0-or-later
"""D38 pause controls: HAL offsets, commands only through QtVCP. Model-Author: Codex."""

import configparser
import math
import os
import sys
import time
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

_CORE = str(Path(__file__).resolve().parents[2] / "core")
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)
from linumert.programs.pause_retract import (  # noqa: E402
    PauseRetract,
    PauseSnapshot,
    RetractRefused,
)


class RetractControl(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell
        self.model = PauseRetract()
        self.last = None
        self.available = False
        self._time = time.monotonic()
        self._pending = None
        self.config = configparser.ConfigParser(strict=False, interpolation=None)
        ini = os.environ.get("INI_FILE_NAME") or getattr(shell.info, "INIPATH", "")
        try:
            self.config.read(ini, encoding="utf-8")
            self.available = (all(k in shell.hmi_pins for k in ("retract_own", "retract_target"))
                              and (self.config.getboolean(
                                  "LINUMERT", "VIRTUAL_MODE", fallback=False)
                                   or self.config.has_section("PLANT"))
                              and self.config.get("KINS", "KINEMATICS").split()[0] == "trivkins"
                              and set(shell.s.axes) == set("XYZ"))
        except (configparser.Error, OSError, ValueError):
            pass
        self.native = 1 if getattr(shell.info, "MACHINE_IS_METRIC", True) else 1 / 25.4
        if self.available:
            self._guard_actions()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(20)

    def _guard_actions(self):
        cls = type(self.shell.action)
        if not cls.__module__.startswith("qtvcp"):
            return
        cls._linumert_retract = self
        if getattr(cls, "_linumert_retract_wrapped", False):
            return
        for name in ("PAUSE", "RUN", "STEP", "JOG", "CALL_MDI", "SET_MANUAL_MODE",
                     "SET_MDI_MODE", "SET_AUTO_MODE"):
            original = getattr(cls, name)

            def guarded(action, *args, _original=original, **kwargs):
                control = type(action)._linumert_retract
                if control.model.active:
                    control.shell.show_alarm(
                        "warn", "Najpierw zakończ powrót D38 lub wyłącz maszynę.")
                    return None
                return _original(action, *args, **kwargs)

            setattr(cls, name, guarded)
        cls._linumert_retract_wrapped = True

    def snapshot(self):
        import hal
        import linuxcnc

        s = self.shell.status.stat
        s.poll()
        value = hal.get_value
        xyz = tuple(round(float(value(f"axis.{axis}.pos-cmd")), 6) for axis in "xyz")
        spindle = s.spindle[0]
        path = Path(s.file) if s.file else None
        stamp = path.stat() if path else None
        frame = (s.file, (stamp.st_mtime_ns, stamp.st_size) if stamp else None,
                 s.task_mode, s.tool_in_spindle, tuple(s.tool_offset), tuple(s.g5x_offset),
                 tuple(s.g92_offset), s.g5x_index, s.rotation_xy, tuple(s.gcodes[1:]),
                 tuple(s.mcodes[1:]), bool(s.feed_override_enabled), xyz,
                 tuple((key, spindle.get(key)) for key in
                     ("enabled", "direction", "speed", "override")),
                 tuple((t.id, t.diameter, t.zoffset) for t in s.tool_table if t.id > 0))
        ready = (s.task_mode == linuxcnc.MODE_AUTO and bool(s.file)
                 and all(s.homed[j] for j in self.shell.info.AVAILABLE_JOINTS)
                 and spindle.get("enabled") and spindle.get("direction")
                 and abs(spindle.get("speed", 0)) > 0
                 and bool(s.feed_override_enabled)
                 and 170 in s.gcodes and 940 in s.gcodes
                 and hal.pin_has_writer("lrt_retract_select.sel")
                 and hal.pin_has_writer("lrt_retract_select.in1")
                 and (not self.model.active or value("axis.z.eoffset-enable"))
                 and self.config.getfloat("AXIS_Z", "OFFSET_AV_RATIO") > 0
                 and not value("spindle.0.inhibit")
                 and value("linumert.eoffset-spindle-count") == 0
                 and abs(value("axis.z.eoffset-scale") - 0.001) < 1e-12
                 and not {330, 331, 730, 760, *range(810, 900, 10)}.intersection(s.gcodes))
        if hal.pin_has_writer("spindle.0.at-speed"):
            ready = ready and value("spindle.0.at-speed")
        return PauseSnapshot(s.task_state == linuxcnc.STATE_ON, bool(ready),
                             s.interp_state == linuxcnc.INTERP_PAUSED and bool(s.paused),
                             abs(s.current_vel) < 1e-7, frame, xyz[2],
                             float(value("axis.z.eoffset")), float(value("axis.z.eoffset-request")),
                             self.config.getfloat("AXIS_Z", "MIN_LIMIT"),
                             self.config.getfloat("AXIS_Z", "MAX_LIMIT"),
                             bool(value("motion.eoffset-limited")),
                             all(math.isfinite(j["ferror_current"])
                                 and abs(j["ferror_current"]) <= 0.005 * self.native
                                 for j in s.joint))

    def withdraw(self, height, feed):
        try:
            self.model.start(self.snapshot(), height * self.native, feed * self.native)
            self.write()
        except Exception as exc:  # noqa: BLE001 - show errors without escaping a Qt slot
            self.model.fail(str(exc))
        self.changed.emit()

    def return_to_path(self, resume=False):
        try:
            self.model.return_to_path(self.snapshot(), resume)
        except Exception as exc:  # noqa: BLE001 - show errors without escaping a Qt slot
            self.model.fail(str(exc))
        self.changed.emit()

    def write(self):
        self.shell.hmi_pins["retract_target"].set(self.model.target)
        self.shell.hmi_pins["retract_own"].set(self.model.active)

    def tick(self):
        if not self.available:
            return
        now, old = time.monotonic(), self._time
        self._time = now
        try:
            self.last = self.snapshot()
            if self._pending is not None:
                frame, self._pending = self._pending, None
                if (self.last.powered and self.last.ready and self.last.paused and self.last.still
                        and self.last.frame == frame and self.last.settled
                        and not self.model.active
                        and max(abs(self.last.offset), abs(self.last.requested)) < 1e-6):
                    self.shell.action.PAUSE()
                else:
                    self.model.message = "Powrót zakończony; stan zmienił się przed wznowieniem."
            if self.model.tick(self.last, now - old):
                self._pending = self.last.frame  # Release HAL inhibit before the next timer tick.
            self.write()
        except Exception as exc:  # noqa: BLE001 - loss of feedback must freeze the last offset
            self.model.fail(f"D38: brak wiarygodnego stanu: {exc}")
            # Preserve the last offset on loss of feedback; never command a blind return.
        self.changed.emit()


class RetractPanel(QtWidgets.QWidget):
    def __init__(self, control, parent=None):
        super().__init__(parent)
        self.control = control
        layout = QtWidgets.QVBoxLayout(self)
        self.message = QtWidgets.QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        row = QtWidgets.QHBoxLayout()
        self.height = QtWidgets.QDoubleSpinBox()
        self.height.setRange(0.01, 100)
        self.height.setValue(10)
        self.height.setSuffix(" mm Z")
        self.feed = QtWidgets.QDoubleSpinBox()
        self.feed.setRange(1, 500)
        self.feed.setValue(200)
        self.feed.setSuffix(" mm/min")
        self.withdraw = QtWidgets.QPushButton("Wycofaj Z w pauzie")
        self.return_button = QtWidgets.QPushButton("Powrót do ścieżki")
        self.resume_button = QtWidgets.QPushButton("Powrót i wznów")
        self.withdraw.clicked.connect(
            lambda: control.withdraw(self.height.value(), self.feed.value()))
        self.return_button.clicked.connect(lambda: control.return_to_path(False))
        self.resume_button.clicked.connect(lambda: control.return_to_path(True))
        widgets = (self.height, self.feed, self.withdraw, self.return_button, self.resume_button)
        for widget in widgets:
            widget.setMinimumHeight(44)
            row.addWidget(widget)
        layout.addLayout(row)
        control.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        c, s = self.control, self.control.last
        ready = bool(c.available and s and s.powered and s.ready
                     and s.paused and s.still and s.settled)
        self.withdraw.setEnabled(ready and not c.model.active)
        for button in (self.return_button, self.resume_button):
            button.setEnabled(ready and c.model.phase == "retracted")
        self.message.setText("D38: " + (c.model.message if c.available else
                             "brak skonfigurowanego toru external offsets.") +
                             " Wrzeciono pozostaje włączone. G41/G42 pozostają w interpreterze.")
