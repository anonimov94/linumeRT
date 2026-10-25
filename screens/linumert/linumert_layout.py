# SPDX-License-Identifier: GPL-2.0-or-later
"""Size the active operator page, preserving scroll access to wider pages.

Model-Author: Codex. Presentation only; no CNC actions or state changes.
"""
from PyQt5 import QtCore, QtWidgets


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
