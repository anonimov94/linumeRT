#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Start a READ ONLY monitor alongside the existing HMI. Model-Author: Codex."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Classic × Neon importuje model ścieżki z rdzenia i materiał z symulacji (bez instalacji pakietu).
sys.path[:0] = [str(ROOT / "screens/linumert"), str(ROOT / "core"), str(ROOT / "simulation")]
from linumert_skin_contract import (  # noqa: E402
    LANGUAGE_IDS,
    SKIN_IDS,
    THEME_IDS,
    PresentationPreferences,
)
from linumert_skin_monitor import SkinMonitor  # noqa: E402
from PyQt5 import QtWidgets  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--skin", choices=SKIN_IDS, default=SKIN_IDS[0])
parser.add_argument("--theme", choices=THEME_IDS, default=THEME_IDS[0])
parser.add_argument("--language", choices=LANGUAGE_IDS, default="pl")
args = parser.parse_args()
app = QtWidgets.QApplication([])
window = SkinMonitor(PresentationPreferences(args.skin, args.theme, args.language))
window.show()
raise SystemExit(app.exec_())
