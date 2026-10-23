# SPDX-License-Identifier: GPL-2.0-or-later
"""Standalone Qt layout study. No LinuxCNC, HAL, file edits or machine commands.

Model-Author: Codex. Optional interactive offline scenes use the SKIN-01 renderer.
"""

from dataclasses import replace

from linumert_skin_contract import (
    LANGUAGE_IDS,
    SKIN_IDS,
    THEME_IDS,
    PresentationPreferences,
    palette_for,
)
from linumert_skin_panel import SkinPanel
from linumert_skin_strings import text
from PyQt5 import QtCore, QtWidgets

# role, row, column, row span, column span. These are distinct compositions,
# not a recoloring of the existing QtDragon shell.
LAYOUTS = {
    "classic-digital": (("dro", 0, 0, 2, 1), ("program", 2, 0, 2, 1),
                        ("toolpath", 0, 1, 3, 2), ("machine", 0, 3, 3, 1),
                        ("tools", 3, 1, 1, 2), ("workpiece", 3, 3, 1, 1)),
    "industrial-pro": (("machine", 0, 0, 3, 2), ("dro", 0, 2, 2, 2),
                       ("toolpath", 0, 4, 2, 2), ("tools", 2, 2, 2, 2),
                       ("program", 2, 4, 2, 2), ("workpiece", 3, 0, 1, 2)),
    "cyberdeck": (("dro", 0, 0, 2, 1), ("program", 0, 1, 2, 1),
                  ("toolpath", 0, 2, 2, 2), ("machine", 2, 0, 2, 1),
                  ("tools", 2, 1, 2, 2), ("workpiece", 2, 3, 2, 1)),
    "organic-vector": (("dro", 0, 0, 2, 1), ("program", 2, 0, 2, 1),
                       ("machine", 0, 1, 2, 1), ("toolpath", 0, 2, 2, 2),
                       ("tools", 2, 1, 2, 2), ("workpiece", 2, 3, 2, 1)),
}


class SkinPreview(QtWidgets.QMainWindow):
    def __init__(self, preferences=None, viewport_factory=None):
        super().__init__()
        self.preferences = preferences or PresentationPreferences()
        self.viewport_factory = viewport_factory
        self.viewports = {}
        self.setWindowTitle("linumeRT · GUI prototype")
        self.resize(1280, 800)
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        selectors = QtWidgets.QHBoxLayout()
        root.addLayout(selectors)
        self.selectors = {}
        self.selector_labels = {}
        for field, choices in (("skin", SKIN_IDS), ("theme", THEME_IDS),
                               ("language", LANGUAGE_IDS)):
            label = QtWidgets.QLabel()
            combo = QtWidgets.QComboBox()
            combo.setObjectName(field)
            for choice in choices:
                title = {"en": "English", "pl": "Polski"}.get(
                    choice, choice.replace("-", " ").title())
                combo.addItem(title, choice)
            combo.setCurrentIndex(combo.findData(getattr(self.preferences, field)))
            label.setBuddy(combo)
            combo.currentIndexChanged.connect(
                lambda index, key=field: self.select(
                    key, self.selectors[key].itemData(index)))
            selectors.addWidget(label)
            selectors.addWidget(combo, 1)
            self.selectors[field] = combo
            self.selector_labels[field] = label
        self.banner = QtWidgets.QLabel()
        self.banner.setObjectName("banner")
        root.addWidget(self.banner)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.workspace = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.workspace)
        self.grid.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.workspace, 1)
        footer = QtWidgets.QHBoxLayout()
        self.demo_label = QtWidgets.QLabel()
        self.demo_label.setWordWrap(True)
        footer.addWidget(self.demo_label, 1)
        self.controls = {}
        for key in ("feed_hold", "stop"):
            button = QtWidgets.QPushButton()
            button.setObjectName(key)
            button.setEnabled(False)
            footer.addWidget(button)
            self.controls[key] = button
        root.addLayout(footer)
        self.refresh()

    def select(self, field, value):
        self.preferences = replace(self.preferences, **{field: value})
        self.refresh()

    def refresh(self):
        p = self.preferences
        c = palette_for(p)
        radius = 22 if p.skin == "organic-vector" else 3
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {c.background}; color: {c.text};
                font-family: 'IBM Plex Sans', 'DejaVu Sans'; font-size: 14px; }}
            QFrame[card="true"] {{ background: transparent; border: none; }}
            QFrame[card="true"] QLabel {{ background: transparent; border: none; }}
            QLabel[heading="true"] {{ color: {c.accent}; font-size: 17px; }}
            QLabel#banner {{ color: {c.warning}; padding: 8px; }}
            QLabel#dro {{ font-family: 'JetBrains Mono', 'DejaVu Sans Mono';
                font-size: 28px; font-weight: bold; color: {c.accent}; }}
            QComboBox, QPushButton {{ min-height: 44px; padding: 0 10px;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {c.panel}, stop:1 {c.background});
                border: 1px solid {c.muted}; border-radius: {radius}px; }}
            QPushButton:disabled {{ color: {c.muted}; }}
            QComboBox:focus {{ border: 2px solid {c.accent}; }}
        """)
        for key, label in self.selector_labels.items():
            label.setText(text(key, p))
        self.banner.setText("linumeRT  //  " + p.skin.replace("-", " ").upper()
                            + "  ·  " + text("preview", p))
        self.status.setText(text("alarms", p) + " · " + text("status_unknown", p)
                            + " · E-STOP: — · " + text("mode_manual", p) + ": —")
        self.demo_label.setText(text("demo_controls", p))
        for key, button in self.controls.items():
            button.setText(text(key, p))
            button.setToolTip(text("demo_controls", p))
        while self.grid.count():
            self.grid.takeAt(0).widget().deleteLater()
        # Clear stretch from the previous composition before applying the next.
        for column in range(6):
            self.grid.setColumnStretch(column, 0)
        self.cards = {}
        self.viewports = {}
        for role, row, column, height, width in LAYOUTS[p.skin]:
            card = SkinPanel(p.skin, c)
            card.setProperty("card", True)
            card.setObjectName(role)
            layout = QtWidgets.QVBoxLayout(card)
            layout.setContentsMargins(16, 12, 16, 12)
            heading = QtWidgets.QLabel(("DRO / XYZ · mm" if role == "dro" else text(role, p)).upper())
            heading.setProperty("heading", True)
            layout.addWidget(heading)
            if role == "dro":
                content = "X  —.———\nY  —.———\nZ  —.———"
            elif role == "program":
                content = text("sample_program", p) + "\n\n001  G21 G90\n002  G54\n003  G0 X0 Y0\n004  M2"
            elif role in ("machine", "workpiece", "toolpath"):
                content = text("offline_scene", p) if self.viewport_factory else text(
                    "renderer_pending", p)
            else:
                content = "T —  ·  D —  ·  Z —"
            body = QtWidgets.QLabel(content)
            body.setWordWrap(True)
            if role == "dro":
                body.setObjectName("dro")
            if role in ("machine", "workpiece", "toolpath") and self.viewport_factory:
                viewport = self.viewport_factory(role, c)
                layout.addWidget(viewport, 1)
                self.viewports[role] = viewport
                layout.addWidget(body)
            else:
                layout.addWidget(body, 1, QtCore.Qt.AlignCenter)
            if role == "program":
                body.setStyleSheet("font-family: monospace; font-size: 13px;")
            self.grid.addWidget(card, row, column, height, width)
            self.cards[role] = card
            for index in range(column, column + width):
                self.grid.setColumnStretch(index, 1)
        for row in range(4):
            self.grid.setRowStretch(row, 1)


def main(viewport_factory=None):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = SkinPreview(viewport_factory=viewport_factory)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
