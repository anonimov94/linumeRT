# SPDX-License-Identifier: GPL-2.0-or-later
"""Pomocnicze widgety bez połączenia z LinuxCNC. Model-Author: Codex."""

from PyQt5 import QtWidgets


def label(text="", name=""):
    widget = QtWidgets.QLabel(text)
    widget.setObjectName(name)
    return widget


def card(title, right=""):
    frame = QtWidgets.QFrame()
    frame.setObjectName("lrtCard")
    body = QtWidgets.QVBoxLayout(frame)
    body.setContentsMargins(16, 12, 16, 14)
    head = QtWidgets.QHBoxLayout()
    head.addWidget(label(title.upper(), "lrtCardTitle"))
    head.addStretch(1)
    side = label(right, "lrtMuted")
    head.addWidget(side)
    body.addLayout(head)
    return frame, body, side
