#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Real GL acceptance of embedded skin panels, not CNC. Model-Author: Codex."""

import argparse
import itertools
import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
os.environ.setdefault("PYOPENGL_PLATFORM", "glx")
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "screens/linumert"), str(ROOT / "core"), str(ROOT / "simulation")]

import numpy as np  # noqa: E402
from linumert_skin_contract import (  # noqa: E402
    LANGUAGE_IDS,
    SKIN_IDS,
    THEME_IDS,
    PresentationPreferences,
)
from linumert_skin_preview import SkinPreview  # noqa: E402
from linumert_skin_viewports import create_viewport  # noqa: E402
from PyQt5 import QtCore, QtGui, QtTest, QtWidgets  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/skin-preview")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication([])
    window = SkinPreview(viewport_factory=create_viewport)
    window.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint
                          | QtCore.Qt.X11BypassWindowManagerHint)
    window.show()
    results = []
    try:
        for size, skin, theme, language in itertools.product(
                ((1280, 800), (1920, 1080)), SKIN_IDS, THEME_IDS, LANGUAGE_IDS):
            window.resize(*size)
            window.preferences = PresentationPreferences(skin=skin, theme=theme, language=language)
            for key, combo in window.selectors.items():
                combo.blockSignals(True)
                combo.setCurrentIndex(combo.findData(getattr(window.preferences, key)))
                combo.blockSignals(False)
            window.refresh()
            app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            QtTest.QTest.qWait(100)
            assert window.size() == QtCore.QSize(*size), (skin, theme, language, window.size())
            reports = {}
            for role, view in window.viewports.items():
                reports[role] = view.context_report()
                assert reports[role]["depth_bits"] >= 24
                frame = view.grabFramebuffer().convertToFormat(QtGui.QImage.Format_RGBA8888)
                assert not frame.isNull(), (skin, role)
                data = frame.bits()
                data.setsize(frame.byteCount())
                pixels = np.frombuffer(data, np.uint8).reshape(frame.height(), -1, 4)
                # A clear colour alone must never pass for a rendered model.
                sample = pixels[::4, :frame.width():4, :3].reshape(-1, 3)
                colors, counts = np.unique(sample, axis=0, return_counts=True)
                assert len(colors) >= 3 and counts.max() < len(sample)*0.999, (
                    skin, theme, language, role, len(colors), counts.max(), len(sample))
                assert window.workspace.rect().contains(window.cards[role].geometry())
            assert window.status.isVisible()
            assert all(b.isVisible() and not b.isEnabled() for b in window.controls.values())
            if theme == THEME_IDS[0] and language == "en":
                for view in window.viewports.values():
                    view.update()
                QtTest.QTest.qWait(100)
                shot = window.grab()
                for role, view in window.viewports.items():
                    origin = view.mapTo(window, QtCore.QPoint(0, 0))
                    crop = shot.copy(QtCore.QRect(origin, view.size())).toImage()
                    crop = crop.convertToFormat(QtGui.QImage.Format_RGBA8888)
                    data = crop.bits()
                    data.setsize(crop.byteCount())
                    rgb = np.frombuffer(data, np.uint8).reshape(crop.height(), -1, 4)
                    assert np.unique(rgb[::4, ::4, :3].reshape(-1, 3), axis=0).shape[0] >= 3, (
                        "empty composed viewport", skin, role)
                assert shot.save(str(args.output / f"{skin}-{size[0]}.png"))
                window.expand_buttons["machine"].click()
                QtTest.QTest.qWait(50)
                assert window.viewports["machine"].width() > window.workspace.width()-40
                assert window.status.isVisible() and window.controls["stop"].isVisible()
                window.expand_buttons["machine"].click()
                QtTest.QTest.qWait(50)
                assert all(card.isVisible() for card in window.cards.values())
            results.append({"size": size, "skin": skin, "theme": theme,
                            "language": language, "contexts": reports})
        report = {"passed": True, "combinations": len(results), "results": results}
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"passed": True, "combinations": len(results)}))
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


if __name__ == "__main__":
    main()
