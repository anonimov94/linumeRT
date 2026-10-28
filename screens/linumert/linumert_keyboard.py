# SPDX-License-Identifier: GPL-2.0-or-later
"""Keep text and numeric editors out of QtVCP machine shortcuts. Model-Author: Codex."""

from PyQt5 import QtCore, QtWidgets


class NumericKeyboardMixin:
    def processed_key_event__(self, receiver, event, is_pressed, key, code, shift, cntrl):
        # Stop/E-STOP/power shortcuts retain their existing handler, even in a field.
        emergency = code in (QtCore.Qt.Key_Escape, QtCore.Qt.Key_F1, QtCore.Qt.Key_F2)
        pressed = getattr(self, "_machine_key_presses", {})
        self._machine_key_presses = pressed
        target = receiver
        destination = receiver
        editor = False
        while target is not None:
            if isinstance(target, (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)):
                editor = True
                destination = target  # Key events can arrive at the text editor's viewport.
                break
            if isinstance(target, (QtWidgets.QAbstractSpinBox, QtWidgets.QLineEdit)) or (
                    isinstance(target, QtWidgets.QComboBox) and target.isEditable()):
                editor = True
                break
            target = target.parent()
        # A jog started outside an editor still receives its release after focus moves.
        if editor and not emergency and (is_pressed or code not in pressed):
            if is_pressed:
                destination.keyPressEvent(event)
            else:
                destination.keyReleaseEvent(event)
            event.accept()
            return True  # Prevent ignored edit keys bubbling into machine shortcuts.
        if not is_pressed and code in pressed:
            receiver = pressed[code]
        handled = super().processed_key_event__(
            receiver, event, is_pressed, key, code, shift, cntrl)
        if not event.isAutoRepeat():
            if is_pressed and handled:
                pressed[code] = receiver
            elif not is_pressed:
                pressed.pop(code, None)
        return handled
