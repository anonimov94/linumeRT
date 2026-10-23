# SPDX-License-Identifier: GPL-2.0-or-later
"""Deliver actual Qt keys through the QtVCP handler contract. Model-Author: Codex."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "screens/linumert"))


@pytest.fixture
def keyboard(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PyQt5.QtWidgets")
    from linumert_keyboard import NumericKeyboardMixin
    from PyQt5 import QtCore

    app = qt.QApplication.instance() or qt.QApplication([])

    class MachineShortcuts:
        def processed_key_event__(self, receiver, event, pressed, key, code, shift, ctrl):
            self.calls.append((receiver, code, pressed))
            return True  # Same swallowing behavior as the QtVCP shortcut dispatcher.

    class Handler(NumericKeyboardMixin, MachineShortcuts):
        calls = []

    handler = Handler()

    class Filter(QtCore.QObject):
        def eventFilter(self, receiver, event):
            if event.type() in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
                return handler.processed_key_event__(
                    receiver, event, event.type() == QtCore.QEvent.KeyPress,
                    event.text(), event.key(), False, False)
            return False

    event_filter = Filter()
    app.installEventFilter(event_filter)
    yield app, handler
    app.removeEventFilter(event_filter)


@pytest.mark.parametrize("kind,value", [("double", "-12.3456"), ("integer", "1234")])
def test_spinbox_accepts_typing_enter_selection_and_paste(keyboard, kind, value):
    from PyQt5 import QtCore, QtTest, QtWidgets

    app, handler = keyboard
    field = QtWidgets.QDoubleSpinBox() if kind == "double" else QtWidgets.QSpinBox()
    field.setRange(-100000, 100000)
    if kind == "double":
        field.setDecimals(4)
    field.setKeyboardTracking(False)
    field.setLocale(QtCore.QLocale.c())
    field.show()
    field.setFocus()
    field.selectAll()
    # Target the spinbox itself: plain lineEdit tests missed QtVCP interception.
    QtTest.QTest.keyClicks(field, value)
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)
    assert field.value() == float(value)
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    app.clipboard().setText("987")
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_V, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)
    assert field.value() == 987
    assert not handler.calls, "typing reached machine shortcuts"
    field.close()


@pytest.mark.parametrize("locale_name,typed", [
    ("C", "2.5"), ("pl_PL", "2,5"), ("pl_PL", "2.5"),
    ("de_DE", "2,5"), ("de_DE", "2.5"),
])
def test_custom_jog_step_is_typed_and_invalid_input_never_prevents_stop(
        keyboard, locale_name, typed):
    from types import SimpleNamespace
    from unittest.mock import Mock

    import linumert_shell_model as model
    from linumert_operator_controls import OperatorControls
    from PyQt5 import QtCore, QtTest

    _app, handler = keyboard
    shell = SimpleNamespace(s=model.ShellState(estop=False, machine_on=True),
                            action=Mock(), info=SimpleNamespace(MACHINE_IS_METRIC=True),
                            _allowed=Mock(return_value=True), set_specialist=Mock())
    panel = OperatorControls(shell)
    panel.show()
    panel.increment.setLocale(QtCore.QLocale(locale_name))
    panel.increment.lineEdit().selectAll()
    QtTest.QTest.keyClicks(panel.increment, typed)
    QtTest.QTest.keyClick(panel.increment, QtCore.Qt.Key_Return)
    assert not shell.action.mock_calls and not handler.calls
    panel.jog("X", 1)
    assert shell.action.JOG.call_args.args == (0, 1, 10, 2.5)
    shell.action.reset_mock()
    panel.increment.lineEdit().setText("-")
    panel.jog("X", 1)
    assert not shell.action.mock_calls and "Wpisz krok" in panel.reason.text()
    shell._allowed.return_value = False
    panel.jog("X", 0)
    shell.action.JOG.assert_called_once_with(0, 0, 0, 0)
    panel.close()


@pytest.mark.parametrize("invalid", ["1,234,567", "1 234", "-1", "nan", "100001"])
def test_ambiguous_grouped_or_invalid_jog_step_does_not_move(keyboard, invalid):
    from types import SimpleNamespace
    from unittest.mock import Mock

    import linumert_shell_model as model
    from linumert_operator_controls import OperatorControls
    from PyQt5 import QtCore

    shell = SimpleNamespace(s=model.ShellState(estop=False, machine_on=True),
                            action=Mock(), info=SimpleNamespace(MACHINE_IS_METRIC=True),
                            _allowed=Mock(return_value=True), set_specialist=Mock())
    panel = OperatorControls(shell)
    panel.increment.setLocale(QtCore.QLocale("en_US"))
    panel.increment.setEditText(invalid)
    panel.jog("X", 1)
    assert not shell.action.mock_calls
    panel.jog("X", 0)
    shell.action.JOG.assert_called_once_with(0, 0, 0, 0)
    panel.close()


def test_spinbox_keeps_emergency_keys_and_releases_existing_jog(keyboard):
    from PyQt5 import QtCore, QtGui, QtTest, QtWidgets

    _app, handler = keyboard
    field, outside = QtWidgets.QDoubleSpinBox(), QtWidgets.QWidget()
    field.show()
    for code in (QtCore.Qt.Key_F1, QtCore.Qt.Key_F2, QtCore.Qt.Key_Escape):
        QtTest.QTest.keyClick(field, code)
        assert handler.calls[-2:] == [(field, code, True), (field, code, False)]
    down = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Right, QtCore.Qt.NoModifier)
    up = QtGui.QKeyEvent(QtCore.QEvent.KeyRelease, QtCore.Qt.Key_Right, QtCore.Qt.NoModifier)
    handler.processed_key_event__(outside, down, True, "", down.key(), False, False)
    handler.processed_key_event__(field.lineEdit(), up, False, "", up.key(), False, False)
    assert handler.calls[-1] == (outside, QtCore.Qt.Key_Right, False)
    field.close()
