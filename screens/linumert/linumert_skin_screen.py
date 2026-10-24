# SPDX-License-Identifier: GPL-2.0-or-later
"""Common read-only view components, never the skin composition. Model-Author: Codex."""

from linumert_skin_controls import EmergencyReadout, Lever, ModeSelector, SkinButton
from linumert_skin_panel import SkinPanel, UnknownGauge
from linumert_skin_readouts import AxisReadout, FeedReadout, ProgramView, ToolReadout
from linumert_skin_strings import text
from PyQt5 import QtWidgets


class SkinScreen(QtWidgets.QWidget):
    LAYOUT = ()
    AXES = "XYZA"
    STATUS_LOCATION = "header"

    def __init__(self, preferences, palette, viewport_factory=None, shared=None):
        super().__init__()
        self.preferences, self.palette = preferences, palette
        self.viewport_factory = viewport_factory
        # Stan hosta przeżywający przebudowę ekranu przy zmianie skórki/motywu/języka
        # (np. scena ścieżki Classic × Neon). Model-Author: Claude.
        self.shared = {} if shared is None else shared
        self.cards, self.viewports, self.expand_buttons = {}, {}, {}
        self.maximized = None
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(5)
        self.build()

    def mount(self):
        p, c = self.preferences, self.palette
        titles = {"dro": "DRO / " + self.AXES, "feed": text("feed_spindle", p),
                  "overrides": text("overrides", p), "status": text("machine_status", p),
                  "manual": text("mode_manual", p)}
        for role, row, column, height, width in self.LAYOUT:
            card = SkinPanel(p.skin, c)
            card.setObjectName(role)
            layout = QtWidgets.QVBoxLayout(card)
            if p.skin == "organic-vector":
                layout.setContentsMargins(20, 10, 16, 10)
            else:
                layout.setContentsMargins(13, 8, 13, 9)
            layout.setSpacing(4)
            heading = QtWidgets.QLabel(titles.get(role) or text(role, p))
            heading.setText(heading.text().upper())
            heading.setProperty("heading", True)
            titlebar = QtWidgets.QHBoxLayout()
            titlebar.addWidget(heading, 1)
            if role in ("machine", "workpiece", "toolpath"):
                button = SkinButton("↗", p.skin, c)
                button.setFixedSize(44, 44)
                button.setToolTip(text("maximize", p))
                button.setAccessibleName(text("maximize", p))
                button.clicked.connect(lambda checked=False, key=role: self.toggle_panel(key))
                titlebar.addWidget(button)
                self.expand_buttons[role] = button
            layout.addLayout(titlebar)
            layout.addWidget(self.body(role), 1)
            self.grid.addWidget(card, row, column, height, width)
            self.cards[role] = card
        for column in range(12):
            self.grid.setColumnStretch(column, 1)
        for row in range(12):
            self.grid.setRowStretch(row, 1)

    def body(self, role):
        p, c = self.preferences, self.palette
        if role in ("machine", "toolpath", "workpiece"):
            if self.viewport_factory:
                view = self.viewport_factory(role, c)
                view.setToolTip(text("offline_scene", p))
                self.viewports[role] = view
                return view
            label = QtWidgets.QLabel(text("renderer_pending", p))
            label.setWordWrap(True)
            return label
        if role == "dro":
            return AxisReadout(p.skin, c, self.AXES)
        if role == "program":
            return ProgramView(c, text("sample_program", p))
        if role == "feed":
            return FeedReadout(p.skin, c)
        if role == "tools":
            return ToolReadout(c)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        if role == "overrides":
            row = QtWidgets.QHBoxLayout()
            for label in ("F", "S", "G0"):
                gauge = UnknownGauge(label, p.skin, c)
                gauge.setMinimumSize(40, 64)
                row.addWidget(gauge)
            layout.addLayout(row)
        elif role == "manual":
            grid = QtWidgets.QGridLayout()
            for column, axis in enumerate("XYZ"):
                for row, sign in enumerate(("+", "−")):
                    button = SkinButton(axis+sign, p.skin, c)
                    button.setEnabled(False)
                    button.setToolTip(text("demo_controls", p))
                    grid.addWidget(button, row, column)
            layout.addLayout(grid)
        elif role == "status":
            row = QtWidgets.QHBoxLayout()
            gauge = UnknownGauge("—", p.skin, c)
            gauge.setMinimumSize(88, 55)
            gauge.setFixedWidth(88)
            row.addWidget(gauge)
            label = QtWidgets.QLabel(text("status_unknown", p))
            label.setWordWrap(True)
            row.addWidget(label, 1)
            layout.addLayout(row)
        else:
            keys = ("power", "spindle", "coolant", "door") if role == "diagnostics" else (
                "status_unknown", "estop_status", "mode_auto")
            for key in keys:
                label = QtWidgets.QLabel("○  " + text(key, p) + "    —")
                label.setWordWrap(True)
                layout.addWidget(label)
        return widget

    def toggle_panel(self, role):
        self.maximized = None if self.maximized == role else role
        for card in self.cards.values():
            self.grid.removeWidget(card)
            card.hide()
        if self.maximized:
            card = self.cards[role]
            self.grid.addWidget(card, 0, 0, 12, 12)
            card.show()
        else:
            for key, row, column, height, width in self.LAYOUT:
                self.grid.addWidget(self.cards[key], row, column, height, width)
                self.cards[key].show()
        for key, button in self.expand_buttons.items():
            button.setText("↙" if key == self.maximized else "↗")

    def console(self, layout_order):
        """The individual screen specifies the order and types of its console modules."""
        p, c = self.preferences, self.palette
        panel = SkinPanel(p.skin, c)
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(9)
        self.controls = {}
        for item in layout_order:
            if item == "cycle":
                for key, signal in (("start", c.success), ("feed_hold", c.warning),
                                    ("stop", c.error)):
                    button = SkinButton(text(key, p), p.skin, c, symbol=key, signal=signal)
                    button.setObjectName(key)
                    button.setEnabled(False)
                    button.setFixedSize(92, 80)
                    button.setToolTip(text("demo_controls", p))
                    layout.addWidget(button)
                    self.controls[key] = button
            elif item == "estop":
                indicator = EmergencyReadout(c)
                indicator.setToolTip(text("status_unknown", p))
                layout.addWidget(indicator)
            elif item in ("edit", "dry_run", "block_delete"):
                button = SkinButton(text(item, p).replace(" ", "\n", 1), p.skin, c)
                button.setEnabled(False)
                button.setFixedSize(76, 70)
                button.setToolTip(text("demo_controls", p))
                layout.addWidget(button)
            elif item == "space":
                layout.addStretch()
            elif item in ("F", "S", "G0"):
                gauge = UnknownGauge(item, p.skin, c)
                gauge.setFixedSize(70, 80)
                layout.addWidget(gauge)
            elif item == "mode":
                if p.skin == "industrial-pro":
                    mode = ModeSelector(c)
                elif p.skin == "classic-digital":
                    mode = Lever("JOG / MDI / AUTO", p.skin, c)
                    mode.setFixedSize(140, 80)
                else:
                    mode = QtWidgets.QWidget()
                    modes = QtWidgets.QHBoxLayout(mode)
                    modes.setContentsMargins(0, 0, 0, 0)
                    modes.setSpacing(2)
                    for label in ("JOG", "MDI", "AUTO"):
                        button = SkinButton(label, p.skin, c)
                        button.setEnabled(False)
                        button.setFixedSize(45, 58)
                        modes.addWidget(button)
                mode.setToolTip(text("demo_controls", p))
                layout.addWidget(mode)
            else:
                label = text(item, p) if item not in ("M01", "M3", "M8") else item
                lever = Lever(label.upper(), p.skin, c)
                lever.setFixedSize(72, 80)
                layout.addWidget(lever)
        return panel
