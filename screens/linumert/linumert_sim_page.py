# SPDX-License-Identifier: GPL-2.0-or-later
"""Widok „Symulacja” nakładki linumeRT: materiał przygotówki, narzędzie, kolizje, obciążenia.

Model-Author: Claude · 2026-10-19.

Obliczenia robi osobny proces `python -m linumert_sim.live` (nice 10, CLAUDE.md §5): czyta stan
LinuxCNC, usuwa materiał przejazdem narzędzia i raportuje kolizje oraz przeciążenia.
Symulacja nie wysyła komend E-STOP ani STO. Ten moduł: klient procesu (QProcess, JSON w liniach), widok 3D
(pyqtgraph.opengl, maks. 30 FPS, render tylko przy zmianie; bez pyqtgraph — widok z góry 2D)
i karty: przygotówka, model maszyny, obciążenie napędów, zdarzenia. Symulacja nie jest funkcją
bezpieczeństwa.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

import linumert_shell_pages as pages
from linumert_operator_controls import OperatorControls

try:
    import pyqtgraph.opengl as gl
except Exception:  # noqa: BLE001 - brak pyqtgraph albo OpenGL: widok 2D
    gl = None

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.environ.get("LINUMERT_ROOT") or os.path.normpath(os.path.join(HERE, "..", ".."))
MATERIALS = ("aluminium", "stal", "stal nierdzewna", "mosiądz", "miedź", "żeliwo", "tworzywo",
             "drewno", "mdf")
ORIGINS = tuple(f"{z}_{xy}" for z in ("TOP", "BOTTOM")
                for xy in ("FRONT_LEFT", "FRONT_RIGHT", "BACK_LEFT", "BACK_RIGHT", "CENTER"))
OFFSETS = ("G54", "G55", "G56", "G57", "G58", "G59")
KIND_LEVEL = {"collision": "err", "overload": "err", "warning": "warn"}


def python_for_sim() -> str:
    """Interpreter procesu symulacji: z pydantic 2 (venv startera) albo bieżący."""
    for cand in (os.environ.get("LINUMERT_PYTHON"), "/opt/linumert/bin/python",
                 os.path.expanduser("~/venv/bin/python")):
        if cand and os.access(cand, os.X_OK):
            return cand
    return sys.executable if "python" in os.path.basename(sys.executable) else "python3"


class SimClient(QtCore.QObject):
    """Proces symulacji: polecenia na stdin, zdarzenia ze stdout (po jednym JSON w linii)."""

    message = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc = QtCore.QProcess(self)
        self.proc.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.readyReadStandardError.connect(self._stderr)
        self.proc.finished.connect(self._finished)
        self._buf = b""
        self.ini = ""
        self.restarts = 0

    def start(self, ini: str) -> None:
        self.ini = ini
        env = QtCore.QProcessEnvironment.systemEnvironment()
        path = os.pathsep.join([os.path.join(ROOT, "core"), os.path.join(ROOT, "simulation")]
                               + ([env.value("PYTHONPATH")] if env.value("PYTHONPATH") else []))
        env.insert("PYTHONPATH", path)
        self.proc.setProcessEnvironment(env)
        self.proc.start(python_for_sim(), ["-m", "linumert_sim.live", "--ini", ini])

    def send(self, **cmd) -> None:
        if self.proc.state() == QtCore.QProcess.Running:
            self.proc.write((json.dumps(cmd, ensure_ascii=False) + "\n").encode("utf-8"))

    def stop(self) -> None:
        self.restarts = 99
        self.send(cmd="quit")
        if not self.proc.waitForFinished(1000):
            self.proc.kill()

    def _read(self) -> None:
        self._buf += bytes(self.proc.readAllStandardOutput())
        *lines, self._buf = self._buf.split(b"\n")
        for line in lines:
            try:
                msg = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(msg, dict):
                self.message.emit(msg)

    def _stderr(self) -> None:
        text = bytes(self.proc.readAllStandardError()).decode("utf-8", "replace").strip()
        if text:
            self.message.emit({"ev": "error", "text": text.splitlines()[-1][:300]})

    def _finished(self, code, _status) -> None:
        self.message.emit({"ev": "error", "text": f"proces symulacji zakończony (kod {code})"})
        if self.restarts < 3 and self.ini:
            self.restarts += 1
            QtCore.QTimer.singleShot(2000, lambda: self.start(self.ini))


# ---- widok 3D --------------------------------------------------------------------------------

def _revolve(profile, segments=20):
    """Bryła obrotowa z obrysu [(r, z)] → (wierzchołki, ściany) do GLMeshItem."""
    prof = [(0.0, profile[0][1])] + [tuple(p) for p in profile] + [(0.0, profile[-1][1])]
    angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
    verts = np.array([(r * math.cos(a), r * math.sin(a), z) for r, z in prof for a in angles])
    faces = []
    n = segments
    for i in range(len(prof) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c, d = a + n, b + n
            faces += [(a, b, d), (a, d, c)]
    return verts, np.array(faces)


def _box(size, center):
    sx, sy, sz = (s / 2 for s in size)
    cx, cy, cz = center
    v = np.array([(cx + x * sx, cy + y * sy, cz + z * sz) for x in (-1, 1) for y in (-1, 1)
                  for z in (-1, 1)])
    f = np.array([(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
                  (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)])
    return v, f


def _rgba(hex_color: str, alpha: float = 1.0):
    c = QtGui.QColor(hex_color)
    return (c.redF(), c.greenF(), c.blueF(), alpha)


class View3D(QtWidgets.QWidget):
    """Przygotówka (mapa wysokości), narzędzie, bryły maszyny, ślad ruchu. ≤ 30 FPS."""

    MAX_RENDER_CELLS = 160_000

    def __init__(self, colors: dict):
        super().__init__()
        self.c = colors
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor(QtGui.QColor(colors["bg"]))
        self.view.setCameraPosition(distance=600, elevation=30, azimuth=-60)
        lay.addWidget(self.view)
        self.surface = None
        self.stride = 1
        self.tool_item = None
        self.bodies: list = []
        self.path = gl.GLLinePlotItem(pos=np.zeros((1, 3)), width=1.5, antialias=True,
                                      mode="line_strip")
        self.view.addItem(self.path)
        self.points: list = []
        self.colors: list = []
        self.tip = (0.0, 0.0, 0.0)
        self._dirty = set()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._render)
        self._timer.start(33)

    def set_stock(self, meta: dict, heights: np.ndarray) -> None:
        if self.surface is not None:
            self.view.removeItem(self.surface)
        ny, nx = heights.shape
        self.stride = max(1, int(math.ceil(math.sqrt(nx * ny / self.MAX_RENDER_CELLS))))
        xs = meta["x0"] + (np.arange(nx) + 0.5) * meta["cell"]
        ys = meta["y0"] + (np.arange(ny) + 0.5) * meta["cell"]
        self.xs, self.ys = xs[::self.stride], ys[::self.stride]
        self.surface = gl.GLSurfacePlotItem(x=self.xs, y=self.ys, z=self._z(heights),
                                            shader="shaded", color=_rgba(self.c["fg2"]),
                                            smooth=False)
        self.view.addItem(self.surface)
        cx, cy = (meta["x0"] + meta["x1"]) / 2, (meta["y0"] + meta["y1"]) / 2
        self.view.opts["center"] = QtGui.QVector3D(cx, cy, meta["z1"])
        self.view.setCameraPosition(distance=max(meta["x1"] - meta["x0"],
                                                 meta["y1"] - meta["y0"]) * 2.4)

    def _z(self, heights):
        return np.ascontiguousarray(heights[::self.stride, ::self.stride].T)

    def update_map(self, heights: np.ndarray) -> None:
        self._pending_map = heights
        self._dirty.add("map")

    def set_bodies(self, bodies: list[dict]) -> None:
        for item in self.bodies:
            self.view.removeItem(item)
        self.bodies = []
        for b in bodies:
            if b["attached"] in ("head", "spindle"):
                continue
            if b["shape"] == "box":
                v, f = _box(b["size"], b["position"])
            else:
                d, h = b["size"][:2]
                x, y, z = b["position"]
                v, f = _revolve([(d / 2, -h / 2), (d / 2, h / 2)], 24)
                v = v + np.array([x, y, z])
            color = self.c["amber"] if b["attached"] in ("vise", "fixture") else self.c["line2"]
            item = gl.GLMeshItem(vertexes=v, faces=f, color=_rgba(color, 0.55), smooth=False,
                                 shader="shaded", glOptions="translucent")
            self.view.addItem(item)
            self.bodies.append(item)

    def set_tool(self, profile: list | None) -> None:
        if self.tool_item is not None:
            self.view.removeItem(self.tool_item)
            self.tool_item = None
        if profile:
            v, f = _revolve(profile)
            self.tool_item = gl.GLMeshItem(vertexes=v, faces=f, color=_rgba(self.c["teal"], 0.9),
                                           smooth=True, shader="shaded")
            self.view.addItem(self.tool_item)
            self._dirty.add("tool")

    def move_tool(self, tip, motion: str) -> None:
        if tuple(tip) == self.tip:
            return
        self.tip = tuple(tip)
        self._dirty.add("tool")
        if not self.points or math.dist(self.points[-1], tip) > 0.3:
            self.points.append(tuple(tip))
            self.colors.append(_rgba(self.c["amber"] if motion == "rapid" else self.c["teal2"]))
            if len(self.points) > 20000:
                del self.points[:5000], self.colors[:5000]
            self._dirty.add("path")

    def clear_path(self) -> None:
        self.points.clear()
        self.colors.clear()
        self._dirty.add("path")

    def _render(self) -> None:
        if not self._dirty or not self.isVisible():
            return
        if "map" in self._dirty and self.surface is not None:
            self.surface.setData(z=self._z(self._pending_map))
        if "tool" in self._dirty and self.tool_item is not None:
            self.tool_item.resetTransform()
            self.tool_item.translate(*self.tip)
        if "path" in self._dirty and len(self.points) > 1:
            self.path.setData(pos=np.array(self.points), color=np.array(self.colors))
        self._dirty.clear()


class View2D(QtWidgets.QLabel):
    """Zastępczy widok z góry (bez pyqtgraph): wysokość materiału w skali szarości."""

    def __init__(self, colors: dict):
        super().__init__("Symulacja 3D niedostępna (brak pyqtgraph) — widok z góry")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.meta = None
        self.heights = None
        self.tip = None
        self.c = colors

    def set_stock(self, meta, heights):
        self.meta, self.heights = meta, heights
        self._draw()

    def update_map(self, heights):
        self.heights = heights
        self._draw()

    def set_bodies(self, bodies):
        pass

    def set_tool(self, profile):
        pass

    def move_tool(self, tip, motion):
        self.tip = tip
        self._draw()

    def clear_path(self):
        pass

    def _draw(self):
        if self.heights is None or not self.isVisible():
            return
        h = np.asarray(self.heights)
        lo, hi = self.meta["z0"], self.meta["z1"]
        g = np.clip((h - lo) / max(hi - lo, 1e-6) * 220 + 30, 0, 255).astype(np.uint8)[::-1]
        g = np.ascontiguousarray(g)
        img = QtGui.QImage(g.data, g.shape[1], g.shape[0], g.shape[1], QtGui.QImage.Format_Grayscale8)
        pix = QtGui.QPixmap.fromImage(img).scaled(self.size(), QtCore.Qt.KeepAspectRatio)
        if self.tip is not None:
            p = QtGui.QPainter(pix)
            p.setPen(QtGui.QPen(QtGui.QColor(self.c["teal"]), 2))
            sx = pix.width() / (self.meta["x1"] - self.meta["x0"])
            sy = pix.height() / (self.meta["y1"] - self.meta["y0"])
            x = (self.tip[0] - self.meta["x0"]) * sx
            y = pix.height() - (self.tip[1] - self.meta["y0"]) * sy
            p.drawEllipse(QtCore.QPointF(x, y), 5, 5)
            p.end()
        self.setPixmap(pix)


# ---- strona ----------------------------------------------------------------------------------

class SimPage(QtWidgets.QWidget):
    """Obszar „Symulacja”: widok + przygotówka, model maszyny, obciążenie, zdarzenia."""

    def __init__(self, shell):
        super().__init__()
        self.setObjectName("lrtPage")
        self.shell = shell
        self.c = shell.c
        self.meta: dict | None = None
        self.map: np.ndarray | None = None
        self.tools: dict = {}
        self.tool = -1
        self.client = SimClient(self)
        self.client.message.connect(self.on_message)
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(16)
        frame, lay, self.lbl_view = pages.card("Symulacja obróbki", "")
        self.view = View3D(self.c) if gl is not None else View2D(self.c)
        lay.addWidget(self.view, 1)
        self.lbl_tool = pages._label("", "lrtMuted")
        lay.addWidget(self.lbl_tool)
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(frame, 1)
        panel = OperatorControls(shell)
        shell.operator_panels.append(panel)
        left_layout.addWidget(panel)
        self.reset_twin = QtWidgets.QPushButton("Uruchom / Reset symulacji → HOME")
        self.reset_twin.setEnabled(shell.s.virtual)
        self.reset_twin.setToolTip("Tylko konfiguracja VIRTUAL_MODE=1; odnawia materiał i bazuje osie")
        self.reset_twin.clicked.connect(shell.virtual_session.start)
        left_layout.addWidget(self.reset_twin)
        self.resume_preview = QtWidgets.QPushButton("Podgląd powrotu po helisie (D38)")
        self.resume_preview.setToolTip("Po zatrzymaniu: sprawdzenie geometrii na kopii materiału; "
                                       "bez ruchu maszyny i bez automatycznego wznowienia")
        self.resume_preview.clicked.connect(lambda: self.client.send(cmd="resume_preview"))
        left_layout.addWidget(self.resume_preview)
        grid.addWidget(left, 0, 0)
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        for card in (self._stock_card(), self._machine_card(), self._load_card(), self._events_card()):
            right_layout.addWidget(card)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(right)
        grid.addWidget(scroll, 0, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

    # ---- karty ---------------------------------------------------------------------------
    def _stock_card(self):
        frame, lay, self.lbl_stock_side = pages.card("Przygotówka", "brak")
        self.lbl_stock = pages._label("Program bez linii ;@STOCK — zdefiniuj przygotówkę.",
                                      "lrtMuted")
        self.lbl_stock.setWordWrap(True)
        lay.addWidget(self.lbl_stock)
        form = QtWidgets.QGridLayout()
        self.cmb_shape = QtWidgets.QComboBox()
        self.cmb_shape.addItems(["BOX", "CYL"])
        self.cmb_shape.currentTextChanged.connect(self._shape_changed)
        self.dims = {}
        for i, (key, value) in enumerate((("X", 150), ("Y", 150), ("Z", 30), ("D", 60),
                                          ("H", 40), ("TOP", 0))):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0 if key == "TOP" else 0.1, 5000)
            spin.setDecimals(4)
            spin.setKeyboardTracking(False)
            spin.setValue(value)
            spin.setSuffix(" mm")
            self.dims[key] = spin
            form.addWidget(pages._label(key, "lrtMuted"), 1 + i // 3, (i % 3) * 2)
            form.addWidget(spin, 1 + i // 3, (i % 3) * 2 + 1)
        form.addWidget(pages._label("Kształt", "lrtMuted"), 0, 0)
        form.addWidget(self.cmb_shape, 0, 1)
        self.cmb_origin = QtWidgets.QComboBox()
        self.cmb_origin.addItems(ORIGINS)
        self.cmb_offset = QtWidgets.QComboBox()
        self.cmb_offset.addItems(OFFSETS)
        self.cmb_mat = QtWidgets.QComboBox()
        self.cmb_mat.addItems(MATERIALS)
        form.addWidget(pages._label("Zero", "lrtMuted"), 3, 0)
        form.addWidget(self.cmb_origin, 3, 1, 1, 3)
        form.addWidget(self.cmb_offset, 3, 4, 1, 2)
        form.addWidget(pages._label("Materiał", "lrtMuted"), 4, 0)
        form.addWidget(self.cmb_mat, 4, 1, 1, 5)
        lay.addLayout(form)
        row = QtWidgets.QHBoxLayout()
        btn = QtWidgets.QPushButton("Ustaw przygotówkę")
        btn.setToolTip("Ustawia materiał w bieżącym układzie detalu (bez ruchu maszyny)")
        btn.clicked.connect(self.apply_stock)
        row.addWidget(btn)
        btn = QtWidgets.QPushButton("Eksport STL")
        btn.setToolTip("Zapis bieżącego materiału przygotówki do pliku STL")
        btn.clicked.connect(self.export_stl)
        row.addWidget(btn)
        btn = QtWidgets.QPushButton("Raport")
        btn.setToolTip("Raport HTML: program, czas, zdarzenia i widok materiału z góry")
        btn.clicked.connect(self.export_report)
        row.addWidget(btn)
        btn = QtWidgets.QPushButton("Odnów materiał")
        btn.setToolTip("Przywraca pełną przygotówkę i czyści ślad ruchu")
        btn.clicked.connect(self.reset_stock)
        row.addWidget(btn)
        lay.addLayout(row)
        self._shape_changed("BOX")
        return frame

    def _shape_changed(self, shape: str) -> None:
        for key in ("X", "Y", "Z"):
            self.dims[key].setEnabled(shape == "BOX")
        for key in ("D", "H"):
            self.dims[key].setEnabled(shape == "CYL")
        if shape == "CYL" and not self.cmb_origin.currentText().endswith("CENTER"):
            self.cmb_origin.setCurrentText("TOP_CENTER")

    def stock_line(self) -> str:
        shape = self.cmb_shape.currentText()
        keys = ("X", "Y", "Z") if shape == "BOX" else ("D", "H")
        words = [";@STOCK", shape] + [f"{k}{self.dims[k].value():g}" for k in keys]
        words += [f"ORIGIN={self.cmb_origin.currentText()}",
                  f"OFFSET={self.cmb_offset.currentText()}"]
        if self.dims["TOP"].value() > 0:
            words.append(f"TOP={self.dims['TOP'].value():g}")
        words.append(f'MAT="{self.cmb_mat.currentText()}"')
        return " ".join(words)

    def apply_stock(self) -> None:
        self.client.send(cmd="stock", line=self.stock_line())

    def export_stl(self) -> None:
        start = os.path.join(os.path.expanduser("~"), "material.stl")
        path, _f = QtWidgets.QFileDialog.getSaveFileName(self, "Eksport STL", start,
                                                         "STL (*.stl)")
        if path:
            self.client.send(cmd="export_stl", path=path)

    def _on_stl(self, msg) -> None:
        self._add_event("info", f"STL zapisany: {msg.get('path')} ({msg.get('triangles')} trójkątów)")

    def export_report(self) -> None:
        start = os.path.join(os.path.expanduser("~"), "raport_symulacji.html")
        path, _f = QtWidgets.QFileDialog.getSaveFileName(self, "Raport symulacji", start,
                                                         "HTML (*.html)")
        if path:
            self.client.send(cmd="export_report", path=path)

    def _on_report(self, msg) -> None:
        self._add_event("info", f"Raport zapisany: {msg.get('path')} "
                                f"({msg.get('events')} zdarzeń)")

    def _on_resume_preview(self, msg) -> None:
        if not msg.get("ok"):
            self._add_event("warn", f"Powrót D38: {msg.get('text')}")
            return
        from linumert_cycles_page import Preview2D

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Podgląd powrotu D38 — bez wykonania")
        dialog.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel(msg["text"] +
                                f" Zakładka {msg['overlap']:g} mm, posuw {msg['feed']:g} mm/min.")
        label.setWordWrap(True)
        layout.addWidget(label)
        view = Preview2D(self.c)
        view.set_lines([[(p[0], p[1]) for p in msg["points"]]])
        layout.addWidget(view, 1)
        z = [p[2] for p in msg["points"]]
        layout.addWidget(QtWidgets.QLabel(f"Z: {min(z):g}…{max(z):g} mm · "
                                         f"{len(z)} próbek geometrii. "
                                         "Styczność do zmierzonego śladu XY."))
        button = QtWidgets.QPushButton("Zamknij podgląd")
        button.clicked.connect(dialog.close)
        layout.addWidget(button)
        self._resume_dialog = dialog
        dialog.show()

    def reset_stock(self) -> None:
        self.client.send(cmd="stock_reset")
        self.view.clear_path()

    def _machine_card(self):
        frame, lay, self.lbl_machine = pages.card("Model maszyny", "")
        self.lbl_bodies = pages._label("—", "lrtMuted")
        self.lbl_bodies.setWordWrap(True)
        lay.addWidget(self.lbl_bodies)
        btn = QtWidgets.QPushButton("Wczytaj model maszyny…")
        btn.setToolTip("machine.yaml: bryły kolizyjne, zakresy osi, napędy (granice obciążenia)")
        btn.clicked.connect(self.choose_machine)
        lay.addWidget(btn, 0, QtCore.Qt.AlignLeft)
        return frame

    def choose_machine(self) -> None:
        start = os.path.join(ROOT, "config", "machines")
        path, _f = QtWidgets.QFileDialog.getOpenFileName(self, "Model maszyny", start,
                                                         "machine.yaml (*.yaml *.yml)")
        if path:
            self.client.send(cmd="machine", path=path)

    def _load_card(self):
        frame, lay, self.lbl_load = pages.card("Obciążenie napędów", "")
        self.bars = {}
        grid = QtWidgets.QGridLayout()
        for i, key in enumerate(("S", "X", "Y", "Z")):
            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 120)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            val = pages._label("—", "lrtMuted")
            grid.addWidget(pages._label("Wrzeciono" if key == "S" else f"Oś {key}", "lrtMuted"),
                           i, 0)
            grid.addWidget(bar, i, 1)
            grid.addWidget(val, i, 2)
            self.bars[key] = (bar, val)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        return frame

    def _events_card(self):
        frame, lay, self.lbl_events = pages.card("Zdarzenia symulacji", "")
        self.events = QtWidgets.QListWidget()
        self.events.setObjectName("lrtLog")
        lay.addWidget(self.events, 1)
        return frame

    # ---- proces ----------------------------------------------------------------------------
    def start(self, ini: str) -> None:
        self.client.start(ini)

    def on_message(self, msg: dict) -> None:
        ev = msg.get("ev")
        handler = getattr(self, f"_on_{ev}", None)
        if handler is not None:
            handler(msg)

    def _on_ready(self, _msg) -> None:
        self.client.restarts = 0
        self.lbl_view.setText("proces symulacji działa")

    def _on_error(self, msg) -> None:
        self._add_event("warn", f"Symulacja: {msg.get('text', '')}")

    def _on_stock(self, msg) -> None:
        if not msg.get("defined"):
            self.lbl_stock_side.setText("brak")
            return
        self.meta = msg
        try:
            self.map = np.memmap(msg["file"], dtype=np.float32, mode="r",
                                 shape=(msg["ny"], msg["nx"]))
        except (OSError, ValueError) as exc:
            self._add_event("warn", f"Mapa materiału niedostępna: {exc}")
            return
        self.view.set_stock(msg, np.array(self.map))
        self.view.clear_path()
        self.lbl_stock_side.setText(msg.get("material") or "aluminium")
        o = msg.get("origin", [0, 0, 0])
        self.lbl_stock.setText(f"{msg['line']}\nZero w układzie maszyny: X{o[0]:g} Y{o[1]:g} "
                               f"Z{o[2]:g} · siatka {msg['cell']:g} mm")

    def _on_map(self, msg) -> None:
        if self.map is not None:
            self.view.update_map(np.array(self.map))
            if self.meta:
                full = (self.meta["x1"] - self.meta["x0"]) * (self.meta["y1"] - self.meta["y0"]) \
                    * (self.meta["z1"] - self.meta["z0"])
                self.lbl_view.setText(f"materiał {msg.get('volume', 0) / 1000:.1f} cm³ "
                                      f"({100 * msg.get('volume', 0) / max(full, 1):.0f}%)")

    def _on_machine(self, msg) -> None:
        self.lbl_machine.setText(msg.get("name", ""))
        names = ", ".join(b["name"] for b in msg.get("bodies", []))
        forces = ", ".join(f"{a} {f:.0f} N" for a, f in msg.get("axis_force", {}).items())
        self.lbl_bodies.setText(f"Bryły: {names or 'brak'}\nGranice sił osi: {forces or 'domyślne'}")
        self.view.set_bodies(msg.get("bodies", []))

    def _on_tools(self, msg) -> None:
        self.tools = {int(k): v for k, v in msg.get("tools", {}).items()}
        self.tool = -1

    def _on_pos(self, msg) -> None:
        tool = int(msg.get("tool", 0))
        if tool != self.tool:
            self.tool = tool
            info = self.tools.get(tool)
            self.view.set_tool(info["profile"] if info else None)
            if info:
                hand = "prawe (M3)" if info["hand"] > 0 else "lewe (M4)"
                rpm = f" · maks. {info['max_rpm']:.0f} obr/min" if info.get("max_rpm") else ""
                self.lbl_tool.setText(f"T{tool} · {info['kind']} · D {info['d']:g} · "
                                      f"Z {info['gauge']:g} · {hand}{rpm}")
            else:
                self.lbl_tool.setText("brak narzędzia we wrzecionie" if not tool else f"T{tool}")
        self.view.move_tool(msg["tip"], msg.get("motion", "feed"))
        load = msg.get("load", {})
        lim = load.get("torque_limit") or 0
        self._bar("S", load.get("torque", 0), lim,
                  f"{load.get('power', 0)} W · {load.get('torque', 0):.2f}/{lim:.2f} N·m")
        for axis in "XYZ":
            f, flim = load.get("axis", {}).get(axis, (0, 0))
            self._bar(axis, f, flim, f"{f} / {flim} N" if flim else "—")
        self.lbl_load.setText(f"{load.get('mrr', 0) * 0.06:.1f} cm³/min")

    def _bar(self, key, value, limit, text) -> None:
        bar, label = self.bars[key]
        pct = int(min(120, 100 * value / limit)) if limit else 0
        bar.setValue(pct)
        level = "err" if pct >= 100 else "warn" if pct >= 80 else ""
        pages._restyle(bar, level=level)
        label.setText(text)

    def _on_alarms(self, msg):
        self.shell.sim_active = set(msg.get("active", []))
        if not self.shell.sim_active:
            self.shell.sim_cause = ""

    def _on_event(self, msg) -> None:
        level = KIND_LEVEL.get(msg.get("kind"), "info")
        pos = msg.get("pos", [0, 0, 0])
        text = f"{msg.get('code')} · {msg.get('text', '')}"
        if msg.get("stop"):
            text += f" (X{pos[0]:.1f} Y{pos[1]:.1f} Z{pos[2]:.1f}) · diagnostyka symulacji"
            self.shell.show_alarm("err", text, msg.get("code", ""))
        self._add_event(level, text)

    def _add_event(self, level: str, text: str) -> None:
        item = QtWidgets.QListWidgetItem(text)
        item.setForeground(QtGui.QColor(self.c.get(level, self.c["fg2"]) if level != "warn"
                                        else self.c["amber"]))
        self.events.insertItem(0, item)
        while self.events.count() > 200:
            self.events.takeItem(self.events.count() - 1)
        self.lbl_events.setText(f"{self.events.count()}")

    def refresh(self) -> None:
        pass
