# SPDX-License-Identifier: GPL-2.0-or-later
"""Kreator zera detalu: wybór punktu zera na przygotówce i jej położenia na stole.

Model-Author: Claude. Nie wykonuje ruchu ani nie zapisuje układu; zwraca punkt i położenie
do formularza „Zero detalu”, gdzie osobny przycisk „Ustaw G5x” zapisuje układ.
"""

import dataclasses
import math

from PyQt5 import QtCore, QtGui, QtWidgets

from linumert.programs.workpiece import ANCHOR_TITLES, Workpiece, anchor_name

POINTS = ((-1, 1), (1, 1), (0, 0), (-1, -1), (1, -1))  # (fx, fy); fy +1 = tył (u góry rysunku)


class StockTopView(QtWidgets.QWidget):
    """Widok przygotówki z góry; klik wybiera narożnik albo środek (przód = dół rysunku)."""

    picked = QtCore.pyqtSignal(int, int)

    def __init__(self, spec):
        super().__init__()
        self.spec, self.point = spec, (-1, -1)
        self.setMinimumSize(320, 260)
        self.setAccessibleName("Widok przygotówki z góry — wybierz punkt zera")

    def set_state(self, spec, point):
        self.spec, self.point = spec, point
        self.update()

    def _rect(self):
        w, h = self.spec.x, self.spec.y
        if self.spec.shape != "box":
            w = h = self.spec.diameter
        margin = 38
        scale = min((self.width() - 2 * margin) / w, (self.height() - 2 * margin) / h)
        return QtCore.QRectF((self.width() - w * scale) / 2, (self.height() - h * scale) / 2,
                             w * scale, h * scale)

    def _pos(self, rect, fx, fy):
        return QtCore.QPointF(rect.center().x() + fx * rect.width() / 2,
                              rect.center().y() - fy * rect.height() / 2)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self._rect()
        palette = self.palette()
        painter.setBrush(palette.alternateBase())
        painter.setPen(QtGui.QPen(palette.windowText().color(), 2))
        if self.spec.shape == "box":
            painter.drawRect(rect)
        else:
            painter.drawEllipse(rect)
            painter.setPen(QtGui.QPen(palette.mid().color(), 1, QtCore.Qt.DashLine))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(rect)
        painter.setPen(palette.windowText().color())
        painter.drawText(QtCore.QRectF(0, self.height() - 26, self.width(), 22),
                         QtCore.Qt.AlignCenter, "przód (Y−)")
        painter.drawText(QtCore.QRectF(0, 4, self.width(), 22), QtCore.Qt.AlignCenter, "tył (Y+)")
        for fx, fy in POINTS:
            chosen = (fx, fy) == self.point
            center = self._pos(rect, fx, fy)
            painter.setPen(QtGui.QPen(palette.highlight().color(), 3 if chosen else 1))
            painter.setBrush(palette.highlight() if chosen else palette.base())
            painter.drawEllipse(center, 11 if chosen else 8, 11 if chosen else 8)

    def mousePressEvent(self, event):
        rect = self._rect()
        best = min(POINTS, key=lambda p: (self._pos(rect, *p) - event.pos()).manhattanLength())
        if (self._pos(rect, *best) - event.pos()).manhattanLength() <= 40:
            self.picked.emit(*best)

    def keyPressEvent(self, event):
        order = list(POINTS)
        index = order.index(self.point)
        if event.key() in (QtCore.Qt.Key_Right, QtCore.Qt.Key_Down):
            self.picked.emit(*order[(index + 1) % len(order)])
        elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Up):
            self.picked.emit(*order[(index - 1) % len(order)])
        else:
            super().keyPressEvent(event)


class OriginWizard(QtWidgets.QDialog):
    """Wynik: `result_spec` (Workpiece z anchor i position) po „Użyj w formularzu”."""

    def __init__(self, spec, limits=None, read_tool=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kreator zera detalu")
        self.limits, self.read_tool = limits or {}, read_tool
        self.spec, self.result_spec = spec, None
        self.face = "top" if spec.anchor.startswith("top") else "bottom"
        self.point = self._point_of(spec.anchor)
        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "Kreator ustala, gdzie na przygotówce leży zero programu i gdzie przygotówka "
            "stoi na stole. Nie rusza osi i nie zapisuje układu — wynik trafia do formularza.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        body = QtWidgets.QHBoxLayout()
        layout.addLayout(body, 1)
        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("1. Kliknij punkt zera na przygotówce"))
        self.view = StockTopView(spec)
        self.view.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.view.picked.connect(self.pick)
        left.addWidget(self.view, 1)
        faces = QtWidgets.QHBoxLayout()
        self.top_button = QtWidgets.QRadioButton("Zero na górnej powierzchni")
        self.bottom_button = QtWidgets.QRadioButton("Zero na dolnej powierzchni")
        (self.top_button if self.face == "top" else self.bottom_button).setChecked(True)
        self.top_button.toggled.connect(self.change_face)
        faces.addWidget(self.top_button)
        faces.addWidget(self.bottom_button)
        left.addLayout(faces)
        body.addLayout(left, 3)
        right = QtWidgets.QVBoxLayout()
        right.addWidget(QtWidgets.QLabel("2. Połóż przygotówkę na stole (współrzędne G53)"))
        form = QtWidgets.QFormLayout()
        self.corner = []
        for axis, label in (("X", "Lewy przedni narożnik X"), ("Y", "Lewy przedni narożnik Y"),
                            ("Z", "Wierzch przygotówki Z")):
            spin = self._spin()
            spin.valueChanged.connect(lambda _v, a=axis: self.move_stock(a))
            self.corner.append(spin)
            form.addRow(label, spin)
        right.addLayout(form)
        self.tool_button = QtWidgets.QPushButton("Pobierz pozycję narzędzia jako punkt zera")
        self.tool_button.setToolTip("Dojedź narzędziem do wybranego punktu i kliknij; "
                                    "pozycja maszynowa (G53, z korektą długości) staje się zerem")
        self.tool_button.setEnabled(read_tool is not None)
        self.tool_button.clicked.connect(self.take_tool_position)
        right.addWidget(self.tool_button)
        right.addWidget(QtWidgets.QLabel("3. Sprawdź wynik"))
        self.result = QtWidgets.QLabel()
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        right.addWidget(self.result)
        right.addStretch(1)
        body.addLayout(right, 2)
        buttons = QtWidgets.QHBoxLayout()
        self.use_button = QtWidgets.QPushButton("Użyj w formularzu")
        self.use_button.clicked.connect(self.accept_spec)
        cancel = QtWidgets.QPushButton("Anuluj")
        cancel.clicked.connect(self.reject)
        for button in (self.use_button, cancel):
            button.setMinimumHeight(44)
            button.setAutoDefault(False)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh(sync_corner=True)

    @staticmethod
    def _spin():
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-100000, 100000)
        spin.setDecimals(3)
        spin.setSuffix(" mm")
        spin.setKeyboardTracking(False)
        return spin

    @staticmethod
    def _point_of(anchor):
        face, _, rest = anchor.partition("-")
        parts = rest.split("-")
        if len(parts) == 1:
            return (0, 0)
        return (-1 if parts[1] == "left" else 1, -1 if parts[0] == "front" else 1)

    def _anchor(self):
        return anchor_name(self.face, *self.point)

    def pick(self, fx, fy):
        old_low, _ = self.spec.bounds()
        self.point = (fx, fy)
        self.spec = dataclasses.replace(self.spec, anchor=self._anchor())
        # zero zostaje tam, gdzie jest; nowy punkt zera = ta sama przygotówka, inny punkt
        self.spec = self._with_corner(old_low, keep_top=True)
        self.refresh(sync_corner=True)

    def change_face(self, _checked):
        self.face = "top" if self.top_button.isChecked() else "bottom"
        self.pick(*self.point)

    def _with_corner(self, low, keep_top=True):
        """Przygotówka stoi tam, gdzie stała: zero liczone od jej narożnika i wierzchu."""
        probe = dataclasses.replace(self.spec, position=(0.0, 0.0, 0.0))
        p_low, p_high = probe.bounds()
        top = self._top if keep_top else p_high[2]
        position = (low[0] - p_low[0], low[1] - p_low[1], top - p_high[2])
        return dataclasses.replace(self.spec, position=position)

    @property
    def _top(self):
        return self.corner[2].value()

    def move_stock(self, _axis):
        if getattr(self, "_syncing", False):
            return
        self.spec = self._with_corner((self.corner[0].value(), self.corner[1].value(), 0.0))
        self.refresh(sync_corner=False)

    def take_tool_position(self):
        value = self.read_tool() if self.read_tool else None
        if value is None or len(value) < 3 or not all(math.isfinite(v) for v in value[:3]):
            self.result.setText("Brak odczytu pozycji maszyny — wpisz położenie przygotówki.")
            return
        self.spec = dataclasses.replace(self.spec, position=tuple(float(v) for v in value[:3]))
        self.refresh(sync_corner=True)

    def refresh(self, sync_corner):
        low, high = self.spec.bounds()
        if sync_corner:
            self._syncing = True
            for spin, number in zip(self.corner, (low[0], low[1], high[2]), strict=True):
                spin.setValue(number)
            self._syncing = False
        self.view.set_state(self.spec, self.point)
        x, y, z = self.spec.position
        lines = [f"Punkt zera: {ANCHOR_TITLES[self.spec.anchor].lower()}",
                 f"Zero w G53: X {x:.3f}  Y {y:.3f}  Z {z:.3f} mm",
                 f"Przygotówka: X {low[0]:.1f}…{high[0]:.1f}  Y {low[1]:.1f}…{high[1]:.1f}  "
                 f"Z {low[2]:.1f}…{high[2]:.1f} mm"]
        issues = self.spec.fit_issues(self.limits) if self.limits else []
        if self.limits:
            lines.append("Zakresy osi: " + ("PROBLEM" if issues else "przygotówka się mieści"))
        lines += issues
        self.result.setText("\n".join(lines))
        self.use_button.setToolTip("Przenosi punkt i położenie do formularza"
                                   + (" (uwaga na zakresy osi)" if issues else ""))

    def accept_spec(self):
        self.result_spec = self.spec
        self.accept()
