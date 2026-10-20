# SPDX-License-Identifier: GPL-2.0-or-later
"""Widok „Cykle”: generatory dialogowe (planowanie, otwory, nagłówek, narzędzie, koniec).

Model-Author: Claude · 2026-10-19 (pierwszy krok sesji 045, D36: funkcja widoczna od razu).

Formularz budowany z pól generatora (`Field`), walidacja z kodami P-xxxx, podgląd 2D i G-code
kroku. Kroki składają się w program; „Zapisz” zapisuje .ngc (koniec programu M2 dopisuje widok),
„Wczytaj” otwiera go w LinuxCNC — bez ruchu maszyny. Kroki są sprawdzane z bazą narzędzi
(typ, średnica, długość ostrza, obroty; sesja 040), „Szacuj czas” liczy czas obróbki z rs274
i limitów INI w wątku tła (sesja 053; GUI nie może stanąć — watchdog HMI, D35), „Podprogramy
NgcGui…” eksportuje `o<lrt_...>` do katalogu z SUBROUTINE_PATH (sesja 048).
Model-Author: Codex · 2026-10-21: pliki .lnx i edycja wybranego kroku (plan 23.10).
"""

from __future__ import annotations

import configparser
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import linumert_shell_pages as pages
from linumert_sim_page import ROOT
from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Action

for _p in (os.path.join(ROOT, "core"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from linumert.generators import basic, drilling, pockets, subroutines  # noqa: E402
from linumert.generators.registry import GeneratorRegistry  # noqa: E402
from linumert.generators.tooling import check_steps  # noqa: E402
from linumert.programs.compiler import CompileError, compile_program  # noqa: E402
from linumert.programs.lnx import LnxError, LnxProgram, Step, load_lnx, save_lnx  # noqa: E402

ACTION = Action()
GENERATORS = (basic.Header, basic.ToolChange, basic.FaceMill, drilling.DrillHoles,
              pockets.PocketRect, pockets.PocketCircle,
              basic.ProgramEnd)


class Preview2D(QtWidgets.QWidget):
    """Łamane XY generatora w skali okna (oś Y w górę)."""

    def __init__(self, colors):
        super().__init__()
        self.c = colors
        self.lines: list = []
        self.setMinimumHeight(180)

    def set_lines(self, lines) -> None:
        self.lines = [ln for ln in lines if len(ln) >= 2]
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - API Qt
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(self.c["bg2"]))
        pts = [pt for ln in self.lines for pt in ln]
        if not pts:
            p.setPen(QtGui.QColor(self.c["fg3"]))
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "brak podglądu 2D")
            return
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        w, h = max(max(xs) - min(xs), 1e-6), max(max(ys) - min(ys), 1e-6)
        k = min((self.width() - 20) / w, (self.height() - 20) / h)
        ox = (self.width() - w * k) / 2 - min(xs) * k
        oy = (self.height() + h * k) / 2 + min(ys) * k
        p.setPen(QtGui.QPen(QtGui.QColor(self.c["teal"]), 1.5))
        for ln in self.lines:
            poly = QtGui.QPolygonF([QtCore.QPointF(ox + x * k, oy - y * k) for x, y in ln])
            p.drawPolyline(poly)
        p.end()


def _mmss(seconds: float) -> str:
    seconds = round(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


class CyclesPage(QtWidgets.QWidget):
    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.program = LnxProgram(name="Program z cykli")
        self.registry = GeneratorRegistry()
        for group in (basic, drilling, pockets):
            group.register(self.registry)
        self.lnx_path = None
        self._dirty = False
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._job = None
        self._revision = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._poll_estimate)
        self.inputs: dict[str, QtWidgets.QWidget] = {}
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        frame, lay, self.lbl_step = pages.card("Cykl", "")
        self.cmb = QtWidgets.QComboBox()
        for cls in GENERATORS:
            self.cmb.addItem(cls.title, cls)
        self.cmb.currentIndexChanged.connect(self._build_form)
        lay.addWidget(self.cmb)
        self.form_box = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.form_box)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form_box)
        lay.addWidget(scroll, 1)
        self.lbl_issue = pages._label("", "lrtMuted")
        self.lbl_issue.setWordWrap(True)
        lay.addWidget(self.lbl_issue)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Podgląd", self.preview), ("Dodaj krok", self.add_step),
                           ("Zmień wybrany", self.update_step)):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        grid.addWidget(frame, 0, 0, 2, 1)
        frame, lay, _s = pages.card("Podgląd 2D", "XY [mm]")
        self.view2d = Preview2D(shell.c)
        lay.addWidget(self.view2d)
        grid.addWidget(frame, 0, 1)
        frame, lay, self.lbl_prog = pages.card("Program z kroków", "0 kroków")
        self.step_list = QtWidgets.QListWidget()
        self.step_list.setMaximumHeight(110)
        self.step_list.currentRowChanged.connect(self.select_step)
        lay.addWidget(self.step_list)
        self.code = QtWidgets.QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        lay.addWidget(self.code, 1)
        self.lbl_tools = pages._label("", "lrtMuted")
        self.lbl_tools.setWordWrap(True)
        lay.addWidget(self.lbl_tools)
        self.lbl_time = pages._label("", "lrtMuted")
        self.lbl_time.setWordWrap(True)
        lay.addWidget(self.lbl_time)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Szacuj czas", self.estimate),
                           ("Podprogramy NgcGui…", self.export_subroutines)):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Otwórz .lnx…", self.open_lnx), ("Zapisz .lnx…", self.save_lnx)):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Usuń ostatni", self.pop_step), ("Zapisz .ngc…", self.save),
                           ("Wczytaj do LinuxCNC", self.load)):
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        lay.addLayout(row)
        grid.addWidget(frame, 1, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        self.path: str | None = None
        self._build_form()

    # ---- formularz ------------------------------------------------------------------------
    def _gen(self):
        return self.cmb.currentData()()

    def _build_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self.inputs = {}
        for f in self.cmb.currentData().fields:
            if f.kind == "choice":
                w = QtWidgets.QComboBox()
                w.addItems(list(f.choices))
                if f.default is not None:
                    w.setCurrentText(str(f.default))
                if f.name == "direction" and self._gen().name.startswith("pocket_"):
                    w.setToolTip("Kieszeń, wrzeciono M3: ccw — współbieżnie; cw — przeciwbieżnie. "
                                 "Po zmianie kierunku wrzeciona zależność jest odwrotna.")
            elif f.kind == "bool":
                w = QtWidgets.QCheckBox()
                w.setChecked(bool(f.default))
            elif f.kind == "text":
                w = QtWidgets.QLineEdit("" if f.default is None else str(f.default))
            else:
                w = QtWidgets.QLineEdit("" if f.default is None else f"{f.default:g}")
                w.setPlaceholderText("wymagane" if f.required else "")
            label = f.label + (f" [{f.unit}]" if f.unit else "") + (" *" if f.required else "")
            self.form.addRow(label, w)
            self.inputs[f.name] = w
        self.lbl_issue.setText("")
        self.view2d.set_lines([])

    def params(self) -> dict:
        out = {}
        for f in self.cmb.currentData().fields:
            w = self.inputs[f.name]
            if isinstance(w, QtWidgets.QComboBox):
                out[f.name] = w.currentText()
            elif isinstance(w, QtWidgets.QCheckBox):
                out[f.name] = w.isChecked()
            else:
                text = w.text().strip()
                if f.kind == "text":
                    out[f.name] = text
                elif text:
                    try:
                        out[f.name] = (int(text) if f.kind == "int" else
                                       float(text.replace(",", ".")))
                    except ValueError:
                        out[f.name] = text  # walidacja zgłosi P-5015
        return out

    def _values(self):
        gen = self._gen()
        values, issues = gen.normalize(self.params())
        if not issues:
            issues = gen.check(values, 0)
        if issues:
            self.lbl_issue.setText("; ".join(i.message() for i in issues))
            return gen, None
        self.lbl_issue.setText("")
        return gen, values

    def preview(self) -> list[str] | None:
        gen, values = self._values()
        if values is None:
            return None
        lines = gen.generate(values)
        self.view2d.set_lines(gen.preview_2d(values))
        self.lbl_step.setText(f"{len(lines)} linii")
        if gen.name.startswith("pocket_"):
            entry = {"plunge": "Wejście pionowe wymaga frezu skrawającego w osi.",
                     "ramp": "Rampa: sprawdź dopuszczalny kąt zagłębiania frezu.",
                     "helix": "Helisa: sprawdź dopuszczalny kąt zagłębiania frezu."}
            finish = (" Wykańczanie usuwa zadane naddatki." if values.get("finish") else
                      " Naddatki pozostają na ścianach i dnie.")
            self.lbl_issue.setText(entry[values.get("entry", "plunge")] + finish +
                                   " Sprawdź w symulacji.")
        self._last = Step(generator=gen.name, version=gen.version, params=values)
        return lines

    # ---- program --------------------------------------------------------------------------
    def add_step(self) -> None:
        lines = self.preview()
        if lines is not None:
            self.program.steps.append(self._last)
            if self._last.generator == "header":
                self.program.units = "inch" if self._last.params["units"] == "G20" else "mm"
            self._show()

    def update_step(self) -> None:
        index = self.step_list.currentRow()
        if index < 0:
            self.lbl_issue.setText("Wybierz krok z listy.")
            return
        if self.preview() is None:
            return
        original = self.program.steps[index]
        self.program.steps[index] = original.model_copy(update={
            "generator": self._last.generator, "version": self._last.version,
            "params": self._last.params})
        if self._last.generator == "header":
            self.program.units = "inch" if self._last.params["units"] == "G20" else "mm"
        self._show()

    def select_step(self, index) -> None:
        if not 0 <= index < len(self.program.steps):
            return
        step = self.program.steps[index]
        gen = self.registry.get(step.generator, step.version)
        for k in range(self.cmb.count()):
            cls = self.cmb.itemData(k)
            if (cls.name, cls.version) == (step.generator, step.version):
                break
        else:
            self.cmb.addItem(f"{gen.title} [v{gen.version}]", type(gen))
            k = self.cmb.count() - 1
        self.cmb.setCurrentIndex(k)
        self._build_form()
        for name, value in step.params.items():
            w = self.inputs.get(name)
            if isinstance(w, QtWidgets.QComboBox):
                w.setCurrentText(str(value))
            elif isinstance(w, QtWidgets.QCheckBox):
                w.setChecked(bool(value))
            elif isinstance(w, QtWidgets.QLineEdit):
                w.setText(str(value))
        self.preview()

    def pop_step(self) -> None:
        if self.program.steps:
            self.program.steps.pop()
            self._show()

    def text(self) -> str:
        return compile_program(self.program, self.registry)

    def _show(self) -> None:
        self._revision += 1
        self._dirty = True
        selected = self.step_list.currentRow()
        self.step_list.blockSignals(True)
        self.step_list.clear()
        for i, step in enumerate(self.program.steps, 1):
            gen = self.registry.get(step.generator, step.version)
            self.step_list.addItem(f"{i}. {gen.title} v{step.version}" +
                                   (" (wyłączony)" if not step.enabled else ""))
        self.step_list.setCurrentRow(min(selected, len(self.program.steps) - 1))
        self.step_list.blockSignals(False)
        self.code.setPlainText(self.text() if self.program.steps else "")
        self.lbl_prog.setText(f"{len(self.program.steps)} kroków")
        self.lbl_time.setText("")
        self.check_tools()

    # ---- baza narzędzi, czas, podprogramy -------------------------------------------------
    def _tool_lookup(self):
        tools = getattr(self.shell, "tools", None)
        if tools is None or not tools._open():
            return None
        return tools.db.get

    def check_tools(self) -> list:
        """Kroki z bazą narzędzi (P-5206…P-5211); wynik w etykiecie, zapis nie jest blokowany."""
        if not self.program.steps:
            self.lbl_tools.setText("")
            return []
        lookup = self._tool_lookup()
        if lookup is None:
            self.lbl_tools.setText("Baza narzędzi niedostępna: kroki niesprawdzone z narzędziami.")
            return []
        steps = [(i, step.generator, self.registry.get(step.generator, step.version).normalize(
            step.params, i)[0]) for i, step in enumerate(self.program.steps, 1) if step.enabled]
        issues = check_steps(steps, lookup, self.program.units)
        if issues:
            self.lbl_tools.setText("Narzędzia — sprawdź przed obróbką: "
                                   + "; ".join(i.message() for i in issues))
        else:
            self.lbl_tools.setText("Narzędzia: kroki zgodne z bazą narzędzi.")
        return issues

    @staticmethod
    def _ini() -> str:
        try:
            from qtvcp.core import Info

            inipath = getattr(Info(), "INIPATH", "")
        except Exception:  # noqa: BLE001 - poza QtVCP (testy)
            inipath = ""
        return os.environ.get("INI_FILE_NAME") or inipath or ""

    def estimate(self) -> None:
        if not self.program.steps:
            self.lbl_time.setText("Brak kroków programu.")
            return
        if self._job is not None:
            return
        ini = self._ini()
        if not ini:
            self.lbl_time.setText("Brak pliku INI maszyny: nie można policzyć czasu.")
            return
        from linumert.programs.estimate import estimate_ngc

        fd, path = tempfile.mkstemp(prefix="linumert-czas-", suffix=".ngc")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(self.text())
        self._job = (self._pool.submit(estimate_ngc, path, ini), path, self._revision)
        self.lbl_time.setText("Liczenie czasu obróbki…")
        self._timer.start()

    def _poll_estimate(self) -> None:
        if self._job is None:
            return
        future, path, revision = self._job
        if not future.done():
            return
        self._timer.stop()
        self._job = None
        try:
            os.unlink(path)
        except OSError:
            pass
        if revision != self._revision:
            self.lbl_time.setText("Program zmieniony: oszacuj czas ponownie.")
            return
        try:
            est = future.result()
        except Exception as exc:  # noqa: BLE001 - brak rs274 albo błąd programu: komunikat
            self.lbl_time.setText(f"Czas obróbki niedostępny: {exc}")
            return
        self.lbl_time.setText(
            f"Szacowany czas: {_mmss(est.total)} (G0 {_mmss(est.rapid)}, obróbka "
            f"{_mmss(est.feed)}, postoje {_mmss(est.dwell)}, wymiany {_mmss(est.tool_change)}) "
            "— górne oszacowanie z zatrzymaniem w narożach.")

    def subroutine_dir(self) -> str:
        """Domyślny katalog: wpis SUBROUTINE_PATH z „user_macros”, inaczej pierwszy wpis."""
        ini = self._ini()
        cfg = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            cfg.read(ini, encoding="utf-8")
            entries = cfg.get("RS274NGC", "SUBROUTINE_PATH", fallback="").split(":")
        except (configparser.Error, OSError):
            entries = []
        base = os.path.dirname(os.path.abspath(ini)) if ini else os.path.expanduser("~")
        entries = [os.path.normpath(os.path.join(base, os.path.expanduser(e.strip())))
                   for e in entries if e.strip()]
        return next((e for e in entries if "user_macros" in e), entries[0] if entries else base)

    def export_subroutines(self) -> list[str]:
        target = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Katalog podprogramów (SUBROUTINE_PATH)", self.subroutine_dir())
        if not target:
            return []
        try:
            paths = [str(p) for p in subroutines.export(target)]
        except OSError as exc:
            self.lbl_issue.setText(f"Nie zapisano podprogramów: {exc}")
            return []
        self.lbl_issue.setText(f"Zapisano {len(paths)} podprogramy w {target} "
                               "(lrt_face_mill, lrt_drill_grid, lrt_drill_circle).")
        return paths

    def open_lnx(self) -> bool:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self, "Otwórz program dialogowy", self.lnx_path or os.path.expanduser("~"),
            "Program dialogowy (*.lnx)")
        if not path:
            return False
        try:
            program = load_lnx(path)
            # Najpierw walidacja całego pliku. Przy błędzie obecny program pozostaje.
            compile_program(program, self.registry)
        except (LnxError, CompileError) as exc:
            self.lbl_issue.setText(f"Nie otwarto: {exc}")
            return False
        if self._dirty and QtWidgets.QMessageBox.question(
                self, "Niezapisany program", "Odrzucić niezapisane zmiany w krokach?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return False
        self.program = program
        self.lnx_path = path
        self.path = None
        self._show()
        self._dirty = False
        if self.program.steps:
            self.step_list.setCurrentRow(0)
        self.lbl_issue.setText(f"Otwarto {path}")
        return True

    def save_lnx(self) -> str | None:
        start = self.lnx_path or os.path.join(os.path.expanduser("~"), "linumert_cykle.lnx")
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Zapisz program dialogowy", start, "Program dialogowy (*.lnx)")
        if not path:
            return None
        if not path.endswith(".lnx"):
            path += ".lnx"
        try:
            save_lnx(self.program, path)
        except OSError as exc:
            self.lbl_issue.setText(f"Nie zapisano: {exc}")
            return None
        self.lnx_path = path
        self._dirty = False
        self.lbl_issue.setText(f"Zapisano {path}")
        return path

    def save(self) -> str | None:
        if not self.program.steps:
            self.lbl_issue.setText("Brak kroków programu.")
            return None
        start = self.path or os.path.join(os.path.expanduser("~"), "linumert_cykle.ngc")
        path, _f = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz program", start,
                                                         "G-code (*.ngc)")
        if not path:
            return None
        if not path.endswith(".ngc"):
            path += ".ngc"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.text())
        except OSError as exc:
            self.lbl_issue.setText(f"Nie zapisano: {exc}")
            return None
        self.path = path
        self.lbl_issue.setText(f"Zapisano {path}")
        return path

    def load(self) -> None:
        if not self.program.steps:
            self.lbl_issue.setText("Brak kroków programu.")
            return
        if self.shell.s.running:
            self.lbl_issue.setText("Najpierw zatrzymaj program.")
            return
        path = self.path
        if path:  # zapis bieżących kroków pod tą samą nazwą
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(self.text())
            except OSError as exc:
                self.lbl_issue.setText(f"Nie zapisano: {exc}")
                return
        else:
            path = self.save()
        if path:
            ACTION.OPEN_PROGRAM(path)

    def refresh(self) -> None:
        pass

    def closeEvent(self, event) -> None:  # noqa: N802 - API Qt
        self._timer.stop()
        if self._job is not None:
            future, path, _revision = self._job
            # Plik musi przetrwać, dopóki interpreter go odczytuje.
            def cleanup(_future):
                try:
                    os.unlink(path)
                except OSError:
                    pass
            future.add_done_callback(cleanup)
            self._job = None
        self._pool.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)
