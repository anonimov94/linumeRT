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
from linumert_skin_screens import LAYOUTS as LAYOUTS
from linumert_skin_screens import SCREENS
from linumert_skin_strings import text
from PyQt5 import QtCore, QtWidgets


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
        self.console = None
        self.root = root
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
            QPushButton#start {{ border-bottom: 4px solid {c.success}; }}
            QPushButton#feed_hold {{ border-bottom: 4px solid {c.warning}; }}
            QPushButton#stop {{ border-bottom: 4px solid {c.error}; }}
        """)
        for key, label in self.selector_labels.items():
            label.setText(text(key, p))
        self.banner.setText("linumeRT  //  " + p.skin.replace("-", " ").upper()
                            + "  ·  " + text("preview", p))
        self.status.setText(text("alarms", p) + " · " + text("status_unknown", p)
                            + " · E-STOP: — · " + text("mode_manual", p) + ": —")
        old_workspace = self.workspace
        if self.console:
            self.root.removeWidget(self.console)
            self.console.hide()
            self.console.deleteLater()
        screen = SCREENS[p.skin](p, c, self.viewport_factory)
        self.root.replaceWidget(old_workspace, screen)
        old_workspace.hide()
        old_workspace.deleteLater()
        self.workspace = screen
        self.grid, self.cards = screen.grid, screen.cards
        self.expand_buttons, self.viewports = screen.expand_buttons, screen.viewports
        self.controls = screen.controls
        self.console = screen.console_widget
        self.root.addWidget(self.console)
        self.setWindowTitle("linumeRT · " + p.skin.replace("-", " ").title())

    @property
    def maximized(self):
        return getattr(self.workspace, "maximized", None)

    def toggle_panel(self, role):
        self.workspace.toggle_panel(role)


def main(viewport_factory=None):
    if QtWidgets.QApplication.instance() is None:
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = SkinPreview(viewport_factory=viewport_factory)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
