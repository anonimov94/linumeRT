#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Podgląd Classic × Neon: detal + cała maszyna, następny punkt z DTG. Model-Author: Claude.

    python3 tools/dev/neon-preview.py                 # program demo, bez LinuxCNC
    python3 tools/dev/neon-preview.py --ngc plik.ngc  # ścieżka z interpretera LinuxCNC (gcode)
    python3 tools/dev/neon-preview.py --png out.png   # zrzut (np. QT_QPA_PLATFORM=offscreen)

Bez komend LinuxCNC, pinów HAL i sygnału życia. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "screens/linumert"), str(ROOT / "core"), str(ROOT / "simulation")]
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from linumert.programs.toolpath import demo_toolpath, load_ngc  # noqa: E402
from linumert_neon_render import PRESETS, MemoryStore, SettingsStore  # noqa: E402
from linumert_neon_view import NeonDetailPanel, NeonPathView, PathScene  # noqa: E402
from PyQt5 import QtCore, QtWidgets  # noqa: E402

STYLE = """
QWidget { background: #07050d; color: #f3eeff; font-family: 'IBM Plex Sans'; font-size: 13px; }
QPushButton { background: #161026; border: 1px solid #3d3060; border-radius: 12px;
              min-height: 44px; padding: 0 16px; font-weight: 600; }
QPushButton#play { background: #00f0ff; color: #07050d; border-color: #00f0ff; }
QPushButton#next { border-color: #ffe600; }
QLabel#title { color: #ab9fcc; font-weight: 600; letter-spacing: 2px; }
"""


class NeonWindow(QtWidgets.QWidget):
    def __init__(self, toolpath, store=None):
        super().__init__()
        self.setWindowTitle("linumeRT · Classic × Neon")
        self.setStyleSheet(STYLE)
        self.scene = PathScene(toolpath)
        root = QtWidgets.QVBoxLayout(self)
        views = QtWidgets.QHBoxLayout()
        store = store or SettingsStore()
        self.detail = NeonDetailPanel(self.scene, store=store)
        self.machine = NeonPathView(self.scene, "machine", store=store)
        for title, widget, stretch in (("DETAL · ZBLIŻENIE", self.detail, 13),
                                       ("MASZYNA · CAŁOŚĆ", self.machine, 10)):
            column = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(title)
            label.setObjectName("title")
            column.addWidget(label)
            column.addWidget(widget, 1)
            views.addLayout(column, stretch)
        root.addLayout(views, 1)
        bar = QtWidgets.QHBoxLayout()
        self.play = self.button(bar, "Pauza", self.scene.toggle, "play")
        self.button(bar, "◀ Punkt wstecz", lambda: self.scene.step(-1))
        self.button(bar, "Do następnego punktu ▶", lambda: self.scene.step(1), "next")
        self.speed = self.button(bar, "", self.scene.cycle_speed)
        self.button(bar, "Od początku", self.scene.restart)
        bar.addStretch(1)
        self.button(bar, "Strefy −", lambda: self.scene.set_zone_count(self.scene.zone_count - 1))
        self.zones = QtWidgets.QLabel()
        bar.addWidget(self.zones)
        self.button(bar, "Strefy +", lambda: self.scene.set_zone_count(self.scene.zone_count + 1))
        root.addLayout(bar)
        self.scene.changed.connect(self.refresh)
        self.refresh()

    def button(self, bar, text, slot, name=None):
        b = QtWidgets.QPushButton(text)
        if name:
            b.setObjectName(name)
        b.setFocusPolicy(QtCore.Qt.NoFocus)
        b.clicked.connect(slot)
        bar.addWidget(b)
        return b

    def refresh(self):
        sc = self.scene
        self.play.setText("Pauza" if sc.playing else ("Od nowa" if sc.done else "Odtwarzaj"))
        self.speed.setText(f"Tempo {sc.speed}×")
        self.zones.setText(f" {sc.zone_count} pkt ")

    def keyPressEvent(self, event):
        actions = {QtCore.Qt.Key_Space: self.scene.toggle,
                   QtCore.Qt.Key_Right: lambda: self.scene.step(1),
                   QtCore.Qt.Key_Left: lambda: self.scene.step(-1)}
        action = actions.get(event.key())
        if action:
            action()
        else:
            super().keyPressEvent(event)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ngc", help="program NGC (wymaga modułu gcode z LinuxCNC 2.9)")
    parser.add_argument("--png", help="zapisz zrzut okna i zakończ")
    parser.add_argument("--seek", type=float, default=None, help="droga [mm] dla zrzutu")
    parser.add_argument("--preset", choices=sorted(PRESETS),
                        help="jakość obu widoków dla zrzutu (bez zapisu w profilu)")
    args = parser.parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    toolpath = load_ngc(args.ngc) if args.ngc else demo_toolpath()
    window = NeonWindow(toolpath, MemoryStore() if args.png else None)
    if args.preset:
        for view in (window.detail.view, window.machine):
            view.set_settings(PRESETS[args.preset], persist=False)
    window.resize(1280, 800)
    window.show()
    if args.png:
        window.scene.playing = False
        if args.seek is not None:
            window.scene.seek(args.seek)
        if window.scene.material is not None:
            while not window.scene.update_material(budget=1.0):
                pass
        for _ in range(3):
            window.scene.tick()
            app.processEvents()
        window.grab().save(args.png)
        return 0
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
