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
        size.setHeight(max(max(card.minimumHeight(), card.minimumSizeHint().height())
                           for card in self.cards) + margins.top() + margins.bottom())
        return size

    def hasHeightForWidth(self):  # noqa: N802 - Qt virtual method
        return True

    def heightForWidth(self, width):  # noqa: N802 - Qt virtual method
        margins = self.contentsMargins()
        if not self._needs_stack(width):
            return super().heightForWidth(width)
        heights = [max(card.minimumHeight(), card.minimumSizeHint().height(),
                       card.heightForWidth(width - margins.left() - margins.right()))
                   for card in self.cards]
        return sum(heights) + self.spacing() + margins.top() + margins.bottom()

    def _needs_stack(self, available):
        margins = self.contentsMargins()
        width = sum(max(card.minimumWidth(), card.minimumSizeHint().width())
                    for card in self.cards) + self.spacing() + margins.left() + margins.right()
        return available < max(self.breakpoint, width)

    def setGeometry(self, rect):  # noqa: N802 - Qt virtual method
        self._arrange(self._needs_stack(rect.width()))
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


class NavigationRail(QtWidgets.QScrollArea):
    """Two columns on short displays; preserve buttons, focus and connections."""

    def __init__(self):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.panel = QtWidgets.QFrame()
        self.panel.setObjectName("lrtRail")
        self.grid = QtWidgets.QGridLayout(self.panel)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(4)
        self.buttons = []
        self.columns = 0
        self.setWidget(self.panel)
        self.arrange(2)

    def add_button(self, button):
        self.buttons.append(button)
        self.columns = 0
        self.arrange(2 if self.height() < 1000 else 1)

    def arrange(self, columns):
        if self.columns == columns:
            return
        self.columns = columns
        self.setFixedWidth(204 if columns == 2 else 116)
        self.panel.setStyleSheet("QToolButton#lrtRailBtn { min-height: 48px; font-size: 11px; }"
                                if columns == 2 else "")
        for row in range(self.grid.rowCount()):
            self.grid.setRowStretch(row, 0)
        for button in self.buttons:
            self.grid.removeWidget(button)
        for index, button in enumerate(self.buttons):
            button.setMinimumHeight(48 if columns == 2 else 72)
            button.setIconSize(QtCore.QSize(18, 18) if columns == 2 else QtCore.QSize(24, 24))
            self.grid.addWidget(button, index // columns, index % columns)
        self.grid.setRowStretch((len(self.buttons) + columns - 1) // columns, 1)

    def resizeEvent(self, event):  # noqa: N802 - Qt virtual method
        self.arrange(2 if event.size().height() < 1000 else 1)
        super().resizeEvent(event)
