# SPDX-License-Identifier: GPL-2.0-or-later
"""Size the active operator page, preserving scroll access to wider pages.

Model-Author: Codex. Presentation only; no CNC actions or state changes.
"""
from PyQt5 import QtCore, QtWidgets


class CardColumns(QtWidgets.QGridLayout):
    """Keep two cards side by side only when both fit comfortably."""

    def __init__(self, parent, cards, breakpoint=1100):
        super().__init__(parent)
        self.cards = tuple(cards)
        self.breakpoint = breakpoint
        self._stacked = None
        self.setContentsMargins(16, 16, 16, 16)
        self.setSpacing(16)
        self._arrange(True)

    def _arrange(self, stacked):
        if stacked == self._stacked:
            return
        self._stacked = stacked
        for card in self.cards:
            self.removeWidget(card)
        for index, card in enumerate(self.cards):
            self.addWidget(card, index if stacked else 0, 0 if stacked else index)
        self.setColumnStretch(0, 1 if stacked else 3)
        self.setColumnStretch(1, 0 if stacked else 2)

    def minimumSize(self):  # noqa: N802 - Qt virtual method
        size = super().minimumSize()
        margins = self.contentsMargins()
        width = max(max(card.minimumWidth(), card.minimumSizeHint().width())
                    for card in self.cards)
        size.setWidth(width + margins.left() + margins.right())
        return size

    def setGeometry(self, rect):  # noqa: N802 - Qt virtual method
        margins = self.contentsMargins()
        width = sum(max(card.minimumWidth(), card.minimumSizeHint().width())
                    for card in self.cards) + self.spacing() + margins.left() + margins.right()
        self._arrange(rect.width() < max(self.breakpoint, width))
        super().setGeometry(rect)


class PageStack(QtWidgets.QStackedWidget):
    """Hidden classic widgets must not impose their minimum on every HMI page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentChanged.connect(self._page_changed)

    def minimumSizeHint(self):  # noqa: N802 - Qt virtual method
        page = self.currentWidget()
        return page.minimumSizeHint().expandedTo(page.minimumSize()) if page else QtCore.QSize(0, 0)

    def sizeHint(self):  # noqa: N802 - Qt virtual method
        page = self.currentWidget()
        return page.sizeHint().expandedTo(self.minimumSizeHint()) if page else QtCore.QSize(0, 0)

    def _page_changed(self, _index):
        self.updateGeometry()
        self.adjustSize()
