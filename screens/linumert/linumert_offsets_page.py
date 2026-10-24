# SPDX-License-Identifier: GPL-2.0-or-later
"""Zero detalu: maszyna, przygotówka i profil odlewu. Model-Author: Codex."""

import json
import os
import sys
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

import linumert_shell_model as model
from linumert_profile_editor import ProfileEditor
from linumert_view_helpers import card, label as _label

ROOT = os.environ.get("LINUMERT_ROOT", str(Path(__file__).resolve().parents[2]))

if os.path.join(ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "core"))

from linumert.programs.workpiece import ANCHOR_TITLES, Workpiece, offset_command
from linumert_workpiece_view import WorkpieceView

import linumert_access_ui as access_ui

SHAPES = (("Prostopadłościan", "box"), ("Walec", "cylinder"),
          ("Rura", "tube"), ("Odlew", "casting"))
ANCHORS = tuple((title, name) for name, title in ANCHOR_TITLES.items())


class OffsetsPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell, self.spec, self.loading, self.valid = shell, Workpiece(), True, True
        ini = getattr(getattr(shell, "info", None), "INIPATH", "") or os.environ.get("INI_FILE_NAME")
        self.ini_path = ini
        self.state_path = (Path(ini).resolve().parent / "linumert_workpiece.json" if ini else
                           Path.home() / ".config/linumert/workpiece.json")
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        frame, left, self.machine_name = card("Maszyna i detal", "model poglądowy")
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
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(scroll, 1)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(350)
        panel, form_body, _side = card("Zero detalu i przygotówka", "mm")
        form = QtWidgets.QFormLayout()
        self.shape = QtWidgets.QComboBox()
        for title, value in SHAPES:
            self.shape.addItem(title, value)
        form.addRow("Kształt", self.shape)
        self.fields = {}
        self.field_labels = {}
        for name, label in (("x", "Długość X"), ("y", "Szerokość Y"),
                            ("height", "Wysokość Z"), ("diameter", "Średnica D"),
                            ("bore", "Otwór rury d")):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0.0001, 100000)
            spin.setDecimals(4)
            spin.setKeyboardTracking(False)
            spin.setValue(getattr(self.spec, name))
            spin.setSuffix(" mm")
            spin.valueChanged.connect(self.preview)
            self.fields[name] = spin
            self.field_labels[name] = _label(label)
            form.addRow(self.field_labels[name], spin)
        self.anchor = QtWidgets.QComboBox()
        for title, value in ANCHORS:
            self.anchor.addItem(title, value)
        form.addRow("Punkt zerowy", self.anchor)
        self.wizard_button = QtWidgets.QPushButton("Kreator zera detalu…")
        self.wizard_button.setToolTip("Wybierz punkt zera na przygotówce i ułóż ją na stole")
        self.wizard_button.clicked.connect(self.open_wizard)
        form.addRow("", self.wizard_button)
        self.offset = QtWidgets.QComboBox()
        self.offset.addItems([f"G{n}" for n in range(54, 60)])
        form.addRow("Układ detalu", self.offset)
        self.position = []
        for axis, value in zip("XYZ", self.spec.position, strict=True):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(-100000, 100000)
            spin.setDecimals(4)
            spin.setKeyboardTracking(False)
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
        self.message = _label("", "lrtMuted")
        self.message.setWordWrap(True)
        right_layout.addWidget(self.message)
        actions = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Zapisz przygotówkę")
        self.save_button.clicked.connect(self.save)
        load_button = QtWidgets.QPushButton("Wczytaj…")
        load_button.clicked.connect(self.choose_definition)
        actions.addWidget(self.save_button)
        actions.addWidget(load_button)
        right_layout.addLayout(actions)
        self.machine_zero = QtWidgets.QPushButton("Wczytaj bazę z maszyny")
        self.machine_zero.setEnabled(not getattr(shell, "preview", False))
        self.machine_zero.clicked.connect(self.read_machine_zero)
        right_layout.addWidget(self.machine_zero)
        self.zero_button = QtWidgets.QPushButton("Ustaw G54")
        self.zero_button.clicked.connect(lambda: self.apply_zero())
        right_layout.addWidget(self.zero_button)
        scroll.setWidget(panel)
        root.addWidget(right, 2)
        self.form_body = form_body
        for combo in (self.shape, self.anchor, self.offset):
            combo.currentIndexChanged.connect(self.preview)
        self.material.textChanged.connect(self.preview)
        self.loading = False
        self.preview()
        client = getattr(getattr(shell, "sim", None), "client", None)
        if client is not None:
            client.message.connect(self.scene_event)
        if self.state_path.exists():
            self.load(self.state_path)

    def tool_position(self):
        """Pozycja czubka narzędzia w G53 (actual_position bez korekty długości) albo None."""
        stat = getattr(getattr(self.shell, "status", None), "stat", None)
        if stat is None or getattr(self.shell, "preview", False):
            return None
        try:
            scale = 1 if getattr(self.shell.info, "MACHINE_IS_METRIC", True) else 25.4
            return tuple((stat.actual_position[i] - stat.tool_offset[i]) * scale for i in range(3))
        except (AttributeError, IndexError, TypeError):
            return None

    def axis_limits(self):
        if not self.ini_path:
            return {}
        try:
            from linumert.programs.limits import limits_from_ini
            return limits_from_ini(self.ini_path)
        except (ImportError, OSError, ValueError):
            return {}

    def open_wizard(self):
        if not self.valid:
            return None
        from linumert_origin_wizard import OriginWizard

        wizard = OriginWizard(self.build_spec(), self.axis_limits(), self.tool_position, self)
        self.wizard = wizard
        if wizard.exec_() != QtWidgets.QDialog.Accepted or wizard.result_spec is None:
            return None
        result = wizard.result_spec
        self.loading = True
        self.anchor.setCurrentIndex(self.anchor.findData(result.anchor))
        for spin, number in zip(self.position, result.position, strict=True):
            spin.setValue(number)
        self.loading = False
        self.preview()
        self.message.setText("Kreator ustawił punkt zera w formularzu. Układ w maszynie "
                             f"zapisze dopiero „Ustaw {result.offset}”.")
        return result

    def read_machine_zero(self):
        """Aktywny układ ze STATUS; pozostałe zapisane układy z PARAMETER_FILE."""
        if getattr(self.shell, "preview", False):
            return
        import configparser
        import math
        from linumert_sim.placement import OFFSET_INDEX, read_var_offsets

        name = self.offset.currentText()
        stat = getattr(getattr(self.shell, "status", None), "stat", None)
        value = None
        if stat is not None and getattr(stat, "g5x_index", None) == OFFSET_INDEX[name]:
            value = tuple(stat.g5x_offset[:3])
        else:
            path = getattr(self.shell.info, "INIPATH", "") or os.environ.get("INI_FILE_NAME", "")
            ini = configparser.ConfigParser(strict=False, interpolation=None)
            ini.read(path)
            filename = ini.get("RS274NGC", "PARAMETER_FILE", fallback="linuxcnc.var")
            source = Path(filename).expanduser()
            if not source.is_absolute():
                source = Path(path).resolve().parent / source
            value = read_var_offsets(source).get(name)
        if value is None or len(value) != 3 or not all(math.isfinite(v) for v in value):
            self.message.setText(f"Brak zapisanej bazy {name}; wpisz pozycję ręcznie.")
            return
        scale = 1 if getattr(self.shell.info, "MACHINE_IS_METRIC", True) else 25.4
        self.loading = True
        for spin, number in zip(self.position, value, strict=True):
            spin.setValue(number * scale)
        self.loading = False
        self.preview()
        self.message.setText(f"Wczytano {name} z konfiguracji maszyny — bez zmiany zer i bez ruchu.")

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
            field.setVisible(key in enabled)
            self.field_labels[key].setVisible(key in enabled)
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
        if hasattr(self, "zero_button"):
            gate = model.gates(self.shell.s)["mdi"]
            self.zero_button.setText(f"Ustaw {self.offset.currentText()}")
            self.zero_button.setEnabled(self.valid and gate.enabled and
                                        not getattr(self.shell, "preview", False))
            self.zero_button.setToolTip(gate.reason or "Zapis położenia układu, bez ruchu osi")
            self.save_button.setEnabled(self.valid)

    def apply_zero(self, confirm=True):
        if not access_ui.require(self.shell, "offsets.edit", "zero detalu"):
            return False
        if (getattr(self.shell, "preview", False) or not self.valid or
                not model.gates(self.shell.s)["mdi"].enabled):
            return False
        spec = self.build_spec()
        if confirm and QtWidgets.QMessageBox.question(
                self, "Ustaw zero detalu", f"Zapisać {spec.offset} w położeniu G53 "
                f"{spec.position} mm? Osie pozostaną w miejscu.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return False
        self.shell.action.CALL_MDI(offset_command(spec, self.shell.s.metric))
        access_ui.audit(self.shell, "offsets.edit", f"{spec.offset} w G53 {spec.position}")
        self.message.setText(f"Zlecono ustawienie {spec.offset}. Sprawdź wskazanie DRO.")
        return True

    def save(self):
        if not self.valid or not access_ui.require(self.shell, "offsets.edit", "przygotówka"):
            return False
        try:
            data = json.dumps(self.build_spec().to_dict(), ensure_ascii=False, indent=2).encode()
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            target = QtCore.QSaveFile(str(self.state_path))
            if not target.open(QtCore.QIODevice.WriteOnly):
                raise OSError(target.errorString())
            if target.write(data) != len(data):
                target.cancelWriting()
                raise OSError(target.errorString())
            if not target.commit():
                raise OSError(target.errorString())
            self.message.setText(f"Zapisano przygotówkę: {self.state_path}")
            return True
        except (OSError, ValueError, TypeError) as exc:
            self.message.setText(f"Błąd zapisu: {exc}")
            return False

    def choose_definition(self):
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Przygotówka", str(self.state_path.parent), "Przygotówka (*.json)",
            options=QtWidgets.QFileDialog.ReadOnly | QtWidgets.QFileDialog.DontUseNativeDialog)
        if path:
            self.load(path)

    def load(self, path):
        try:
            with Path(path).open("rb") as source:
                raw = source.read(65537)
            if len(raw) > 65536:
                raise ValueError("Definicja przygotówki jest za duża")
            spec = Workpiece(**json.loads(raw))
        except (OSError, ValueError, TypeError) as exc:
            self.message.setText(f"Błąd odczytu przygotówki: {exc}")
            return False
        self.loading, self.spec = True, spec
        self.shape.setCurrentIndex(self.shape.findData(spec.shape))
        self.anchor.setCurrentIndex(self.anchor.findData(spec.anchor))
        self.offset.setCurrentText(spec.offset)
        for name, field in self.fields.items():
            field.setValue(getattr(spec, name))
        for field, value in zip(self.position, spec.position, strict=True):
            field.setValue(value)
        self.material.setText(spec.material)
        self.profile.set_points(spec.profile)
        self.loading = False
        self.preview()
        return True
