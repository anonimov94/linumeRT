"""Real Qt scroll layout regression; no LinuxCNC. Model-Author: Codex."""
import os
import sys
from pathlib import Path

import pytest


def test_wide_hidden_page_does_not_clip_active_operator_page():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screens/linumert"))
    from linumert_layout import PageStack

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    stack = PageStack()
    small = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(small)
    layout.addWidget(QtWidgets.QPushButton("Operator action"))
    wide = QtWidgets.QWidget()
    wide.setMinimumWidth(1400)
    stack.addWidget(small)
    stack.addWidget(wide)
    scroll.setWidget(stack)
    scroll.resize(600, 400)
    scroll.show()
    try:
        for index in (0, 1, 0):
            stack.setCurrentIndex(index)
            for _ in range(3):
                app.processEvents()
            if index == 0:
                assert stack.width() <= scroll.viewport().width()
                assert scroll.horizontalScrollBar().maximum() == 0
            else:
                assert stack.width() >= 1400  # keep the classic page usable by scrolling
                assert scroll.horizontalScrollBar().maximum() > 0
    finally:
        scroll.close()
