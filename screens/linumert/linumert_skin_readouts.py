# SPDX-License-Identifier: GPL-2.0-or-later
"""Original read-only instruments for the four screens. Model-Author: Codex."""

from linumert_skin_controls import housing
from PyQt5 import QtCore, QtGui, QtWidgets


class AxisReadout(QtWidgets.QWidget):
    def __init__(self, family, palette, axes="XYZA"):
        super().__init__()
        self.family, self.palette, self.axes = family, palette, axes
        self.values = {}
        self.setMinimumSize(110, 120)
        self.setAccessibleName("DRO —")

    def set_positions(self, values):
        self.values = dict(values)
        self.setAccessibleName("G53 " + " / ".join(
            axis + " " + self.display_value(axis) for axis in self.axes))
        self.update()

    def display_value(self, axis):
        value = self.values.get(axis)
        return "—.———" if value is None else f"{value:.3f}"

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        height = self.height()/len(self.axes)
        for index, axis in enumerate(self.axes):
            row = QtCore.QRectF(1, index*height+2, self.width()-2, height-5)
            p.fillPath(housing(row, self.family), QtGui.QColor(c.background))
            badge = QtCore.QRectF(row.x()+3, row.y()+3, min(52, row.width()*.18), row.height()-6)
            p.fillPath(housing(badge, self.family), QtGui.QColor(c.raised))
            p.setPen(QtGui.QPen(QtGui.QColor(c.accent), 1))
            p.drawPath(housing(badge, self.family))
            font = QtGui.QFont("DejaVu Sans Mono")
            font.setPixelSize(max(18, min(36, int(height*.52))))
            font.setBold(True)
            p.setFont(font)
            p.drawText(badge, QtCore.Qt.AlignCenter, axis)
            p.setPen(QtGui.QColor(c.accent if self.family != "industrial-pro" else c.text))
            digits = row.adjusted(badge.width()+12, 0, -28, 0)
            # Resize the font to keep the unknown value inside narrow panels.
            value = self.display_value(axis)
            while (QtGui.QFontMetricsF(font).horizontalAdvance(value) > digits.width()
                   and font.pixelSize() > 12):
                font.setPixelSize(font.pixelSize()-1)
            p.setFont(font)
            p.drawText(digits, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, value)
            p.setFont(QtGui.QFont("DejaVu Sans", 7))
            p.setPen(QtGui.QColor(c.muted))
            p.drawText(row.adjusted(row.width()-24, 0, 0, 0), QtCore.Qt.AlignCenter,
                       "°" if axis in "ABC" else "mm")


class FeedReadout(QtWidgets.QWidget):
    def __init__(self, family, palette):
        super().__init__()
        self.family, self.palette = family, palette
        self.setMinimumSize(90, 64)
        self.feed = self.spindle = None
        self.setToolTip("F: rzeczywista prędkość toru · S: zadane obroty z LinuxCNC")

    def set_readings(self, feed=None, spindle=None):
        self.feed, self.spindle = feed, spindle
        self.setAccessibleName(f"F {self.format_value(feed)} mm/min; "
                               f"S zadane {self.format_value(spindle)} rpm")
        self.update()

    @staticmethod
    def format_value(value):
        return "—" if value is None else f"{value:.1f}"

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        for index, (label, unit) in enumerate((("F", "mm/min"), ("S", "rpm zad."))):
            rect = QtCore.QRectF(2, index*self.height()/2+2, self.width()-4, self.height()/2-4)
            p.fillPath(housing(rect, self.family), QtGui.QColor(c.background))
            p.setPen(QtGui.QColor(c.accent))
            font = QtGui.QFont("DejaVu Sans Mono")
            font.setPixelSize(max(16, min(26, int(rect.height()*.45))))
            font.setBold(True)
            p.setFont(font)
            p.drawText(rect.adjusted(9, 0, 0, 0),
                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, label)
            p.drawText(rect.adjusted(28, 0, -55, 0),
                       QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                       self.format_value(self.feed if index == 0 else self.spindle))
            p.setPen(QtGui.QColor(c.muted))
            p.setFont(QtGui.QFont("DejaVu Sans", 7))
            p.drawText(rect.adjusted(rect.width()-50, 0, -4, 0), QtCore.Qt.AlignCenter, unit)


class ToolReadout(QtWidgets.QWidget):
    def __init__(self, palette):
        super().__init__()
        self.palette = palette
        self.setMinimumSize(80, 65)
        self.number = self.diameter = self.length = None
        self.setToolTip("Narzędzie we wrzecionie · D: średnica · L: offset Z z tabeli narzędzi")

    def set_readings(self, number=None, diameter=None, length=None):
        self.number, self.diameter, self.length = number, diameter, length
        self.setAccessibleName(f"T {number if number is not None else '—'}; "
                               f"D {self.dimension_value(diameter)} mm; "
                               f"L {self.dimension_value(length)} mm")
        self.update()

    @staticmethod
    def dimension_value(value):
        return "—" if value is None else f"{value:.3f}".rstrip("0").rstrip(".")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = self.palette
        x, top = max(12, self.width()*.17), 8
        height = min(self.height()-16, 140)
        metal = QtGui.QLinearGradient(x-9, 0, x+9, 0)
        for stop, value in ((0, c.panel), (.35, c.text), (.55, c.muted), (1, c.background)):
            metal.setColorAt(stop, QtGui.QColor(value))
        p.setBrush(metal)
        p.setPen(QtGui.QPen(QtGui.QColor(c.muted), 1))
        p.drawRoundedRect(QtCore.QRectF(x-10, top, 20, height*.45), 2, 2)
        p.drawRoundedRect(QtCore.QRectF(x-6, top+height*.45, 12, height*.5), 2, 2)
        for y in range(int(top+height*.5), int(top+height*.9), 8):
            p.drawLine(int(x-5), y+5, int(x+5), y)
        p.setPen(QtGui.QColor(c.accent))
        font = QtGui.QFont("DejaVu Sans Mono", 15)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QtCore.QRectF(x+20, top, self.width()-x-20, 30), QtCore.Qt.AlignLeft,
                   f"T {self.number if self.number is not None else '—'}")
        p.setPen(QtGui.QColor(c.muted))
        p.setFont(QtGui.QFont("DejaVu Sans Mono", 9))
        p.drawText(QtCore.QRectF(x+20, top+32, self.width()-x-20, height), f"D {self.dimension_value(self.diameter)} mm\n"
                   f"L {self.dimension_value(self.length)} mm")


class ProgramView(QtWidgets.QWidget):
    def __init__(self, palette, caption):
        super().__init__()
        self.palette = palette
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(caption)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {palette.muted}; font-size: 10px;")
        layout.addWidget(label)
        editor = QtWidgets.QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        editor.setMinimumSize(70, 60)
        editor.setStyleSheet(f"background:{palette.background}; color:{palette.text};"
                            "border:none; font:12px 'DejaVu Sans Mono';")
        editor.setPlainText("\n".join(f"{i:04}  {line}" for i, line in enumerate((
            "; linumeRT / example", "G21 G90 G17", "G54", "T1 M6", "S8000 M3",
            "G0 X0 Y0 Z10", "G1 Z-2 F200", "G1 X60 F900", "G1 Y40", "G1 X0",
            "G1 Y0", "G0 Z10", "M5", "M2"), 1)))
        cursor = editor.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.MoveAnchor, 6)
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format.setBackground(QtGui.QColor(palette.raised))
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        editor.setExtraSelections([selection])
        layout.addWidget(editor, 1)

    def set_source(self, source, filename, line, note=""):
        editor = self.findChild(QtWidgets.QPlainTextEdit)
        caption = self.findChild(QtWidgets.QLabel)
        caption.setTextFormat(QtCore.Qt.PlainText)
        caption.setText(filename.rsplit("/", 1)[-1] if source is not None else note)
        caption.setToolTip(filename)
        content = "\n".join(f"{i:04}  {text}" for i, text in enumerate(source or (), 1))
        if editor.toPlainText() != content:
            editor.setPlainText(content)
        selection = QtWidgets.QTextEdit.ExtraSelection()
        cursor = editor.textCursor()
        block = editor.document().findBlockByNumber(line - 1)
        if source and block.isValid():
            cursor.setPosition(block.position())
            selection.cursor = cursor
            selection.format.setBackground(QtGui.QColor(self.palette.raised))
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            editor.setExtraSelections([selection])
            editor.setTextCursor(cursor)
            editor.ensureCursorVisible()
        else:
            editor.setExtraSelections([])
