# SPDX-License-Identifier: GPL-2.0-or-later
"""Strona „Wygląd” HMI: wybór palety, edytor kolorów, podgląd na żywo, zapis. Model-Author: Claude.

M2 (028): operator zmienia kolorystykę działającego ekranu bez edycji plików. Zmiana wyglądu nie
wysyła żadnego polecenia do CNC. Kolory są sprawdzane (`linumert_appearance.check`): kontrast tekstu
i znaczników oraz znaczenie czerwonego/zielonego/bursztynowego muszą zostać zachowane, inaczej
„Zastosuj” i „Zapisz” są zablokowane z podaniem przyczyny. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

import linumert_appearance as ap
from linumert_view_helpers import card
from linumert_view_helpers import label as _label
from PyQt5 import QtGui, QtWidgets


class AppearancePage(QtWidgets.QWidget):
    def __init__(self, shell, path=None):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell, self.path = shell, path
        saved = ap.load(path)
        self.preset, self.colors = saved["preset"], dict(saved["colors"])
        self.edits, self.swatches = {}, {}
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        frame, body, _ = card("Paleta")
        row = QtWidgets.QHBoxLayout()
        self.preset_buttons = {}
        for pid, (title, _colors) in ap.PRESETS.items():
            btn = QtWidgets.QPushButton(title)
            btn.setObjectName("lrtAction")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, p=pid: self.choose_preset(p))
            row.addWidget(btn)
            self.preset_buttons[pid] = btn
        row.addStretch(1)
        body.addLayout(row)
        body.addWidget(_label("Własne kolory poniżej tworzą paletę „Własna”.", "lrtMuted"))
        root.addWidget(frame)

        frame, body, _ = card("Kolory")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        for i, (role, _token, title) in enumerate(ap.ROLES):
            r, c = divmod(i, 2)
            grid.addWidget(_label(title), r, c * 3)
            swatch = QtWidgets.QPushButton()
            swatch.setFixedSize(44, 32)
            swatch.setObjectName("lrtSwatch")
            swatch.clicked.connect(lambda _=False, k=role: self.pick(k))
            edit = QtWidgets.QLineEdit()
            edit.setMaxLength(7)
            edit.setFixedWidth(100)
            edit.editingFinished.connect(lambda k=role: self.typed(k))
            grid.addWidget(swatch, r, c * 3 + 1)
            grid.addWidget(edit, r, c * 3 + 2)
            self.swatches[role], self.edits[role] = swatch, edit
        body.addLayout(grid)
        self.status = _label("", "lrtMuted")
        self.status.setWordWrap(True)
        body.addWidget(self.status)
        root.addWidget(frame)

        actions = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Zastosuj (podgląd)")
        self.btn_save = QtWidgets.QPushButton("Zapisz")
        self.btn_reset = QtWidgets.QPushButton("Przywróć domyślne")
        for btn, slot in ((self.btn_apply, self.apply), (self.btn_save, self.save),
                          (self.btn_reset, self.reset)):
            btn.setObjectName("lrtAction")
            btn.clicked.connect(slot)
            actions.addWidget(btn)
        actions.addStretch(1)
        root.addLayout(actions)
        root.addWidget(_label(
            "Podgląd odświeża większość elementów od razu; widoki rysowane własnym kodem (np. "
            "symulacja, ścieżka) przejmują kolory po ponownym uruchomieniu ekranu. Zmiana wyglądu "
            "nie wysyła poleceń do maszyny.", "lrtMuted"))
        root.addStretch(1)
        if saved.get("note"):
            self.status.setText(saved["note"])
        self.refresh()

    # ---- stan -------------------------------------------------------------------------------
    def refresh(self) -> None:
        for role, edit in self.edits.items():
            color = self.colors[role]
            if edit.text() != color:
                edit.setText(color)
            self.swatches[role].setStyleSheet(
                f"background: {color}; border: 1px solid #888; border-radius: 6px;")
        for pid, btn in self.preset_buttons.items():
            btn.setChecked(pid == self.preset)
        problems = ap.check(self.colors)
        self.btn_apply.setEnabled(not problems)
        self.btn_save.setEnabled(not problems)
        if problems:
            self.status.setText("Nie można zastosować: " + " · ".join(problems))
        elif not self.status.text().startswith(("Zapisano", "Zastosowano", "Przywrócono",
                                                "Ustawienia")):
            self.status.setText("Kolory poprawne: kontrast i znaczenie stanów zachowane.")

    def choose_preset(self, pid: str) -> None:
        self.preset, self.colors = pid, dict(ap.PRESETS[pid][1])
        self.status.setText("")
        self.refresh()
        self.apply()

    def custom(self, role: str, value: str) -> None:
        self.colors[role] = value
        self.preset = "custom"
        self.status.setText("")
        self.refresh()

    def typed(self, role: str) -> None:
        text = self.edits[role].text().strip()
        if not text.startswith("#"):
            text = "#" + text
        try:
            ap.rgb(text)
        except ap.AppearanceError:
            self.status.setText(f"{text!r}: oczekiwano koloru #rrggbb")
            self.edits[role].setText(self.colors[role])
            return
        self.custom(role, text.lower())

    def pick(self, role: str) -> None:
        chosen = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.colors[role]), self,
                                                 "Wybierz kolor")
        if chosen.isValid():
            self.custom(role, chosen.name())

    # ---- akcje ------------------------------------------------------------------------------
    def apply(self) -> None:
        try:
            tokens = ap.apply_to_tokens(self.shell.tokens, self.colors)
        except ap.AppearanceError as exc:
            self.status.setText(f"Nie zastosowano: {exc}")
            return
        self.shell.apply_tokens(tokens)
        self.status.setText("Zastosowano (podgląd). „Zapisz”, aby zachować po restarcie.")

    def save(self) -> None:
        try:
            path = ap.save(self.preset, self.colors, self.path)
        except (ap.AppearanceError, OSError) as exc:
            self.status.setText(f"Nie zapisano: {exc}")
            return
        self.apply()
        self.status.setText(f"Zapisano w {path}")

    def reset(self) -> None:
        ap.reset(self.path)
        self.preset, self.colors = ap.DEFAULT_PRESET, ap.default_colors()
        self.refresh()
        self.apply()
        self.status.setText("Przywrócono domyślny wygląd (Classic Turquoise).")
