"""Real Qt: unchecked fields must be empty, including confirmation dialogs.

Model-Author: Codex · 028. Uses the actual legacy check image as the checked reference.
"""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'screens/linumert'))


def test_empty_checkbox_overrides_legacy_cross_and_keeps_tick(tmp_path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    QtWidgets = pytest.importorskip('PyQt5.QtWidgets')
    import linumert_shell_model as model
    from PyQt5 import QtCore, QtTest

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # Actual application rules also apply to dialogs outside the shell root.
    stylesheet = (ROOT / 'screens/linumert/linumert.qss').read_text()
    rules = '\n'.join(re.findall(r'QCheckBox[^{}]*\{[^{}]*\}', stylesheet))
    rules = rules.replace(':/buttons/images/', str(ROOT / 'screens/linumert/images') + '/')
    previous = app.styleSheet()
    app.setStyleSheet(rules)
    try:
        for shell in (False, True):
            window = QtWidgets.QWidget()
            window.setObjectName('lrtRoot' if shell else 'confirmation')
            if shell:
                window.setStyleSheet(model.shell_qss(model.load_tokens()))
            layout = QtWidgets.QVBoxLayout(window)
            box = QtWidgets.QCheckBox('Potwierdzenie')
            layout.addWidget(box)
            window.resize(250, 80)
            window.show()
            app.processEvents()
            for checked in (False, True, False):
                box.setChecked(checked)
                app.processEvents()
                option = QtWidgets.QStyleOptionButton()
                box.initStyleOption(option)
                rect = box.style().subElementRect(
                    QtWidgets.QStyle.SE_CheckBoxIndicator, option, box)
                image = box.grab(rect).toImage()
                red = green = 0
                for x in range(image.width()):
                    for y in range(image.height()):
                        pixel = image.pixelColor(x, y)
                        red += pixel.red() > 150 and pixel.green() < 100
                        green += pixel.green() > 150 and pixel.red() < 100
                assert red == 0, ('legacy cross', shell, checked)
                assert (green > 2) == checked, ('missing tick', shell, checked)
                if not checked:
                    # The empty frame must differ from its interior.
                    assert image.pixelColor(0, image.height() // 2) != image.pixelColor(
                        image.width() // 2, image.height() // 2)
            box.setFocus()
            QtTest.QTest.keyClick(box, QtCore.Qt.Key_Space)
            assert box.isChecked()
            assert window.grab().save(str(tmp_path / f'checkbox-{shell}.png'))
            window.close()
    finally:
        app.setStyleSheet(previous)
