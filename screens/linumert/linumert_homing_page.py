# SPDX-License-Identifier: GPL-2.0-or-later
"""Bazowanie: stan każdego stawu i jawne akcje operatora. Model-Author: Codex."""

from collections import Counter

from PyQt5 import QtWidgets
from qtvcp.core import Action, Info, Status

import linumert_shell_model as model
from linumert_shell_pages import _hal, _label, _set_row, _table, card

ACTION, INFO, STATUS = Action(), Info(), Status()


def _sequence(joint) -> int:
    """HOME_SEQUENCE stawu; w LinuxCNC 2.9 INFO.JOINT_SEQUENCE to lista, nie słownik."""
    seq = getattr(INFO, "JOINT_SEQUENCE", None) or []
    try:
        return int(seq[joint] if not hasattr(seq, "get") else seq.get(joint, 0))
    except (IndexError, TypeError, ValueError):
        return 0


class HomingPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        frame, body, self.summary = card("Bazowanie", "")
        self.table = _table(["Staw", "Oś", "Stan", "Czujnik bazowania", "Krańcówki"])
        body.addWidget(self.table)
        self.reason = _label("", "lrtMuted")
        self.reason.setWordWrap(True)
        body.addWidget(self.reason)
        buttons = QtWidgets.QHBoxLayout()
        self.home = QtWidgets.QPushButton("Bazuj wszystkie")
        self.home.setMinimumHeight(44)
        self.home.clicked.connect(shell.home_all)
        buttons.addWidget(self.home)
        self.joint_buttons = {}
        names = INFO.GET_NAME_FROM_JOINT
        counts = Counter(name.upper()[:1] for name in names.values())
        for joint in INFO.AVAILABLE_JOINTS:
            name = names[joint].upper()
            # Portal pozostaje w sekwencji Home All; nie rozdzielamy jego napędów.
            if counts[name[:1]] != 1 or _sequence(joint) < 0:
                continue
            button = QtWidgets.QPushButton(f"Bazuj {name}")
            button.setMinimumHeight(44)
            button.clicked.connect(lambda _checked=False, j=joint: self.home_joint(j))
            buttons.addWidget(button)
            self.joint_buttons[joint] = button
        body.addLayout(buttons)
        layout.addWidget(frame, 1)
        self.refresh()

    def home_joint(self, joint):
        if self.shell._allowed("home") and self.joint_buttons[joint].isEnabled():
            ACTION.SET_MACHINE_HOMING(joint)

    def refresh(self):
        gate = model.gates(self.shell.s)["home"]
        joints = getattr(STATUS.stat, "joint", ())
        active = any(j.get("homing", False) for j in joints)
        self.home.setEnabled(gate.enabled and not active)
        for button in self.joint_buttons.values():
            button.setEnabled(gate.enabled and not active)
        self.reason.setText("Trwa bazowanie — Stop przerywa ruch." if active else gate.reason or
                            "Portal bazuj przez „Bazuj wszystkie”, zgodnie z sekwencją maszyny.")
        done = 0
        for row, joint in enumerate(INFO.AVAILABLE_JOINTS):
            state = joints[joint] if joint < len(joints) else {}
            homed = bool(state.get("homed", False))
            done += homed
            text = "bazowanie" if state.get("homing") else "zbazowany" if homed else "niebazowany"
            switch = _hal(f"joint.{joint}.home-sw-in")
            limits = [label for pin, label in (("min_hard_limit", "MIN"),
                                               ("max_hard_limit", "MAX")) if state.get(pin)]
            _set_row(self.table, row, [str(joint), INFO.GET_NAME_FROM_JOINT[joint].upper(), text,
                                      "—" if switch is None else "aktywny" if switch else "wolny",
                                      ", ".join(limits) or "wolne"])
        self.summary.setText(f"zbazowane stawy: {done} / {len(INFO.AVAILABLE_JOINTS)}")
