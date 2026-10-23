# SPDX-License-Identifier: GPL-2.0-or-later
"""Real Qt layout study across all selections and both sizes. Model-Author: Codex."""

import itertools
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt5")
from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screens" / "linumert"))
from linumert_skin_contract import LANGUAGE_IDS, SKIN_IDS, THEME_IDS  # noqa: E402
from linumert_skin_preview import LAYOUTS, SkinPreview  # noqa: E402
from linumert_skin_strings import text  # noqa: E402


def test_distinct_compositions_have_no_overlapping_grid_cells():
    signatures = set()
    for layout in LAYOUTS.values():
        occupied = set()
        signatures.add(tuple(layout))
        for _, row, column, height, width in layout:
            cells = {(r, c) for r in range(row, row + height)
                     for c in range(column, column + width)}
            assert not cells & occupied
            occupied |= cells
    assert len(signatures) == 4


def test_all_preview_selections_and_resolutions():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # Windows' offscreen plugin does not enumerate installed system fonts.
    # Register one for real text/layout checks; never copy it into the project.
    if not QtGui.QFontDatabase().families() and sys.platform == "win32":
        font = Path(os.environ["SystemRoot"]) / "Fonts" / "arial.ttf"
        assert QtGui.QFontDatabase.addApplicationFont(str(font)) >= 0
    assert QtGui.QFontDatabase().families(), "Layout checks require a usable font"
    window = SkinPreview()
    window.show()
    try:
        for size, family, theme, language in itertools.product(
                ((1280, 800), (1920, 1080)), SKIN_IDS, THEME_IDS, LANGUAGE_IDS):
            window.resize(*size)
            for key, value in (("skin", family), ("theme", theme), ("language", language)):
                combo = window.selectors[key]
                combo.setCurrentIndex(combo.findData(value))
            app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            app.processEvents()
            assert window.preferences.skin == family
            assert window.preferences.theme == theme
            assert window.preferences.language == language
            assert text("preview", window.preferences) in window.banner.text()
            assert window.grid.count() == 6
            assert set(window.cards) == {item[0] for item in LAYOUTS[family]}
            for card in window.cards.values():
                assert card.isVisible()
                assert card.width() > 100 and card.height() > 80
                assert window.workspace.rect().contains(card.geometry())
            for control in (*window.selectors.values(), *window.controls.values()):
                assert control.height() >= 44
            assert all(not button.isEnabled() for button in window.controls.values())
            assert window.size() == QtCore.QSize(*size)
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def test_maximize_keeps_global_controls_and_releases_previous_cards():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = SkinPreview(viewport_factory=lambda role, colors: QtWidgets.QWidget())
    window.show()
    app.processEvents()
    old_cards = list(window.cards.values())
    for role in ("machine", "toolpath", "workpiece"):
        window.expand_buttons[role].click()
        app.processEvents()
        assert window.maximized == role
        assert window.grid.count() == 1
        assert window.cards[role].width() > window.workspace.width() - 20
        assert window.status.isVisible() and window.controls["stop"].isVisible()
        window.expand_buttons[role].click()
        app.processEvents()
        assert window.grid.count() == 6
        assert all(card.isVisible() for card in window.cards.values())
    window.expand_buttons["machine"].click()
    window.selectors["skin"].setCurrentIndex(1)
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()
    from PyQt5 import sip
    assert all(sip.isdeleted(card) for card in old_cards)
    assert window.maximized is None and window.grid.count() == 6
    assert set(window.viewports) == {"machine", "toolpath", "workpiece"}
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
