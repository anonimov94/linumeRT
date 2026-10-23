# SPDX-License-Identifier: GPL-2.0-or-later
"""Standalone Qt layout study. No LinuxCNC, HAL, file edits or machine commands.

Model-Author: Codex. Viewports reserve space for the separately validated renderer.
"""

from dataclasses import replace

from linumert_skin_contract import (
    LANGUAGE_IDS,
    SKIN_IDS,
    THEME_IDS,
    PresentationPreferences,
    palette_for,
)
from linumert_skin_strings import text
from PyQt5 import QtCore, QtWidgets

# role, row, column, row span, column span. These are distinct compositions,
# not a recoloring of the existing QtDragon shell.
LAYOUTS = {
    "classic-digital": (("dro", 0, 0, 2, 1), ("toolpath", 0, 1, 2, 3),
                        ("machine", 0, 4, 1, 1), ("workpiece", 1, 4, 1, 1),
                        ("program", 2, 0, 1, 4), ("tools", 2, 4, 1, 1)),
    "industrial-pro": (("dro", 0, 0, 1, 2), ("tools", 0, 2, 1, 1),
                       ("machine", 1, 0, 2, 1), ("toolpath", 1, 1, 2, 1),
                       ("workpiece", 1, 2, 1, 1), ("program", 2, 2, 1, 1)),
    "cyberdeck": (("program", 0, 0, 1, 1), ("dro", 0, 1, 1, 1),
                  ("toolpath", 0, 2, 2, 2), ("machine", 1, 0, 2, 2),
                  ("workpiece", 2, 2, 1, 1), ("tools", 2, 3, 1, 1)),
    "organic-vector": (("machine", 0, 0, 2, 2), ("dro", 0, 2, 1, 1),
                       ("toolpath", 0, 3, 2, 2), ("tools", 1, 2, 1, 1),
                       ("workpiece", 2, 0, 1, 2), ("program", 2, 2, 1, 3)),
}


class SkinPreview(QtWidgets.QMainWindow):
    def __init__(self, preferences=None):
        super().__init__()
        self.preferences = preferences or PresentationPreferences()
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
        radius = {"classic-digital": 0, "industrial-pro": 4,
                  "cyberdeck": 1, "organic-vector": 24}[p.skin]
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {c.background}; color: {c.text};
                font-family: 'IBM Plex Sans', 'DejaVu Sans'; font-size: 14px; }}
            QFrame[card="true"] {{ background: {c.panel}; border: 1px solid {c.muted};
                border-radius: {radius}px; }}
            QFrame[card="true"] QLabel {{ background: transparent; border: none; }}
            QLabel[heading="true"] {{ color: {c.accent}; font-size: 17px; }}
            QLabel#banner {{ color: {c.warning}; padding: 8px; }}
            QLabel#dro {{ font-family: 'JetBrains Mono', 'DejaVu Sans Mono';
                font-size: 32px; color: {c.accent}; }}
            QComboBox, QPushButton {{ min-height: 44px; padding: 0 10px;
                background: {c.panel}; border: 1px solid {c.muted}; }}
            QPushButton:disabled {{ color: {c.muted}; }}
            QComboBox:focus {{ border: 2px solid {c.accent}; }}
        """)
        for key, label in self.selector_labels.items():
            label.setText(text(key, p))
        self.banner.setText(text("preview", p))
        self.status.setText(text("alarms", p) + " · " + text("status_unknown", p)
                            + " · E-STOP: — · " + text("mode_manual", p) + ": —")
        self.demo_label.setText(text("demo_controls", p))
        for key, button in self.controls.items():
            button.setText(text(key, p))
            button.setToolTip(text("demo_controls", p))
        while self.grid.count():
            self.grid.takeAt(0).widget().deleteLater()
        # Clear stretch from the previous composition before applying the next.
        for column in range(5):
            self.grid.setColumnStretch(column, 0)
        self.cards = {}
        for role, row, column, height, width in LAYOUTS[p.skin]:
            card = QtWidgets.QFrame()
            card.setProperty("card", True)
            card.setObjectName(role)
            layout = QtWidgets.QVBoxLayout(card)
            heading = QtWidgets.QLabel("DRO" if role == "dro" else text(role, p))
            heading.setProperty("heading", True)
            layout.addWidget(heading)
            if role == "dro":
                content = "X  —\nY  —\nZ  —"
            elif role == "program":
                content = text("sample_program", p) + "\n\nG21 G90\nG0 X0 Y0\nM2"
            elif role in ("machine", "workpiece", "toolpath"):
                content = text("renderer_pending", p)
            else:
                content = "T —  ·  D —  ·  Z —"
            body = QtWidgets.QLabel(content)
            body.setWordWrap(True)
            if role == "dro":
                body.setObjectName("dro")
            layout.addWidget(body, 1, QtCore.Qt.AlignCenter)
            self.grid.addWidget(card, row, column, height, width)
            self.cards[role] = card
            for index in range(column, column + width):
                self.grid.setColumnStretch(index, 1)
        for row in range(3):
            self.grid.setRowStretch(row, 1)


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = SkinPreview()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
