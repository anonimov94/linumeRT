# SPDX-License-Identifier: GPL-2.0-or-later
"""Zero detalu: maszyna, przygotówka i profil odlewu. Model-Author: Codex."""

import os
import sys

from PyQt5 import QtWidgets

import linumert_shell_pages as pages
from linumert_profile_editor import ProfileEditor
from linumert_sim_page import ROOT

if os.path.join(ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "core"))

from linumert.programs.workpiece import Workpiece
from linumert_workpiece_view import WorkpieceView

SHAPES = (("Prostopadłościan", "box"), ("Walec", "cylinder"),
          ("Rura", "tube"), ("Odlew", "casting"))
ANCHORS = (("Środek górnej powierzchni", "top-center"),
           ("Środek dolnej powierzchni", "bottom-center"),
           ("Lewy przedni narożnik na górze", "top-front-left"))


class OffsetsPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell, self.spec, self.loading, self.valid = shell, Workpiece(), True, True
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        frame, left, self.machine_name = pages.card("Maszyna i detal", "model poglądowy")
        self.view = WorkpieceView(shell.c)
        left.addWidget(self.view, 1)
        camera = QtWidgets.QHBoxLayout()
        for title, part in (("Cała maszyna", False), ("Powiększ detal", True)):
            button = QtWidgets.QPushButton(title)
            button.clicked.connect(lambda _checked=False, p=part: self.view.fit(p))
            camera.addWidget(button)
        left.addLayout(camera)
        root.addWidget(frame, 3)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(350)
        panel, form_body, _side = pages.card("Zero detalu i przygotówka", "mm")
        form = QtWidgets.QFormLayout()
        self.shape = QtWidgets.QComboBox()
        for title, value in SHAPES:
            self.shape.addItem(title, value)
        form.addRow("Kształt", self.shape)
        self.fields = {}
        for name, label in (("x", "Długość X"), ("y", "Szerokość Y"),
                            ("height", "Wysokość Z"), ("diameter", "Średnica D"),
                            ("bore", "Otwór rury d")):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0.01, 100000)
            spin.setDecimals(3)
            spin.setValue(getattr(self.spec, name))
            spin.setSuffix(" mm")
            spin.valueChanged.connect(self.preview)
            self.fields[name] = spin
            form.addRow(label, spin)
        self.anchor = QtWidgets.QComboBox()
        for title, value in ANCHORS:
            self.anchor.addItem(title, value)
        form.addRow("Punkt zerowy", self.anchor)
        self.offset = QtWidgets.QComboBox()
        self.offset.addItems([f"G{n}" for n in range(54, 60)])
        form.addRow("Układ detalu", self.offset)
        self.position = []
        for axis, value in zip("XYZ", self.spec.position, strict=True):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(-100000, 100000)
            spin.setDecimals(3)
            spin.setValue(value)
            spin.setSuffix(" mm")
            spin.valueChanged.connect(self.preview)
            self.position.append(spin)
            form.addRow(f"Zero {axis} w G53", spin)
        self.material = QtWidgets.QLineEdit(self.spec.material)
        self.material.setMaxLength(60)
        form.addRow("Materiał", self.material)
        form_body.addLayout(form)
        self.profile = ProfileEditor(shell.c)
        self.profile.set_points(self.spec.profile)
        self.profile.changed.connect(self.preview)
        form_body.addWidget(self.profile)
        self.message = pages._label("", "lrtMuted")
        self.message.setWordWrap(True)
        form_body.addWidget(self.message)
        scroll.setWidget(panel)
        root.addWidget(scroll, 2)
        self.form_body = form_body
        for combo in (self.shape, self.anchor, self.offset):
            combo.currentIndexChanged.connect(self.preview)
        self.material.textChanged.connect(self.preview)
        self.loading = False
        self.preview()
        client = getattr(getattr(shell, "sim", None), "client", None)
        if client is not None:
            client.message.connect(self.scene_event)

    def build_spec(self):
        kind = self.shape.currentData()
        return Workpiece(shape=kind, **{k: s.value() for k, s in self.fields.items()},
                         position=tuple(s.value() for s in self.position),
                         profile=self.profile.points() if kind == "casting" else self.spec.profile,
                         anchor=self.anchor.currentData(), offset=self.offset.currentText(),
                         material=self.material.text().strip())

    def preview(self, *_args):
        if self.loading:
            return
        kind = self.shape.currentData()
        enabled = {"box": {"x", "y", "height"}, "cylinder": {"height", "diameter"},
                   "tube": {"height", "diameter", "bore"}, "casting": set()}[kind]
        for key, field in self.fields.items():
            field.setEnabled(key in enabled)
        self.profile.setVisible(kind == "casting")
        try:
            self.spec = self.build_spec()
            self.view.set_workpiece(self.spec)
            self.valid = True
            self.message.setText("Podgląd nominalnej przygotówki. Edycja nie wykonuje ruchu.")
        except (ValueError, TypeError) as exc:
            self.valid = False
            self.message.setText(str(exc))
        self.refresh()

    def scene_event(self, message):
        if message.get("ev") == "machine":
            self.machine_name.setText(message.get("name", "maszyna"))
            self.view.set_machine(message.get("bodies", []))
        elif message.get("ev") == "pos":
            self.view.nose = tuple(message.get("nose", (0, 0, 0)))
            if self.isVisible():
                self.view.update()

    def refresh(self):
        pass  # edycja geometrii nie zmienia stanu LinuxCNC
