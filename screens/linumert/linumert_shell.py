# SPDX-License-Identifier: GPL-2.0-or-later
"""Nakładka linumeRT na QtDragon: powłoka (pasek trybu i stanu, szyna obszarów, pasek akcji)
i widok „Maszyna” według makiety docs/design/makiety/01_maszyna.png.

Model-Author: Claude · HMI-PoC (2026-10-19). Proof of concept: funkcje dochodzą etapami
(docs/design/HMI_WORKFLOW.md).

Zasady (HMI_WORKFLOW.md, CLAUDE.md §6):
- cały interfejs QtDragon zostaje nietknięty i dostępny w obszarach szyny („Program”,
  „Narzędzia”…); nakładka tylko przenosi go do stosu stron, niczego nie kopiuje;
- zmiana obszaru nie wykonuje ruchu ani zmiany trybu;
- komendy maszyny wyłącznie przez ACTION QtVCP, stan wyłącznie ze STATUS QtVCP;
- ekran nie jest funkcją bezpieczeństwa: przycisk E-STOP steruje programowym E-STOP LinuxCNC,
  obwód sprzętowy jest nadrzędny.
"""

from __future__ import annotations

import collections
import os
import time

import linuxcnc
from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Action, Info, Status

import linumert_shell_model as model
import linumert_shell_pages as pages

STATUS = Status()
ACTION = Action()
INFO = Info()

NML_KINDS = {k: getattr(linuxcnc, k) for k in
             ("NML_ERROR", "NML_TEXT", "NML_DISPLAY", "OPERATOR_ERROR", "OPERATOR_TEXT",
              "OPERATOR_DISPLAY") if hasattr(linuxcnc, k)}

# Obszary szyny: (id, etykieta, ikona, cel). Cel „page:<id>” = własna strona linumeRT,
# inaczej nazwa przycisku QtDragon, którego strona pojawia się w widoku klasycznym.
AREAS = (
    ("start", "Start", "klucz", "page:start"),
    ("machine", "Maszyna", "maszyna", "page:machine"),
    ("production", "Produkcja", "start", "page:production"),
    ("program", "Program", "program", "btn_file"),
    ("tools", "Narzędzia", "narzedzia", "btn_tool"),
    ("offsets", "Zero detalu", "zero", "btn_offsets"),
    ("probe", "Sonda", "sonda", "btn_probe"),
    ("diag", "Diagnostyka", "diagnostyka", "page:diag"),
    ("settings", "Konfiguracja", "konfiguracja", "btn_settings"),
    ("classic", "Pełny QtDragon", "wtyczka", "btn_main"),
)


def _icon(name: str, color: str) -> QtGui.QIcon:
    """Ikona SVG z docs/design/ikony (stroke=currentColor) w kolorze tokenu."""
    path = model.icon_path(name)
    try:
        with open(path, encoding="utf-8") as fh:
            svg = fh.read().replace("currentColor", color)
    except OSError:
        return QtGui.QIcon()
    pix = QtGui.QPixmap()
    pix.loadFromData(svg.encode("utf-8"), "SVG")
    return QtGui.QIcon(pix)


def _label(text: str = "", name: str = "", **props) -> QtWidgets.QLabel:
    lab = QtWidgets.QLabel(text)
    if name:
        lab.setObjectName(name)
    for key, value in props.items():
        lab.setProperty(key, value)
    return lab


def _restyle(widget: QtWidgets.QWidget, **props) -> None:
    """Zmienia właściwości stylu; przestylowanie (kosztowne) tylko przy faktycznej zmianie."""
    changed = False
    for key, value in props.items():
        if widget.property(key) != value:
            widget.setProperty(key, value)
            changed = True
    if changed:
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def _card(title: str, right: str = "") -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout,
                                                 QtWidgets.QLabel]:
    frame = QtWidgets.QFrame()
    frame.setObjectName("lrtCard")
    lay = QtWidgets.QVBoxLayout(frame)
    lay.setContentsMargins(16, 12, 16, 14)
    lay.setSpacing(8)
    head = QtWidgets.QHBoxLayout()
    head.addWidget(_label(title.upper(), "lrtCardTitle"))
    head.addStretch(1)
    side = _label(right, "lrtMuted")
    head.addWidget(side)
    lay.addLayout(head)
    return frame, lay, side


class LinumertShell(QtCore.QObject):
    """Powłoka linumeRT owinięta wokół centralnego widgetu QtDragon."""

    def __init__(self, handler):
        super().__init__(handler.w)
        self.h = handler
        self.w = handler.w
        self.tokens = model.load_tokens()
        self.c = self.tokens["kolory"]
        self.s = model.ShellState(axes=tuple(a.upper() for a in INFO.AVAILABLE_AXES))
        self.dro_view = "work"
        self.program_lines: list[str] = []
        self.positions = ([0.0] * 9, [0.0] * 9, [0.0] * 9)
        self.areas: dict[str, QtWidgets.QToolButton] = {}
        self._missed: collections.deque[int] = collections.deque(maxlen=5)  # ok. 2 s historii
        self._estop_requested = False
        self.buttons: dict[str, QtWidgets.QPushButton] = {}

    # ---- budowa ---------------------------------------------------------------------------
    def install(self) -> LinumertShell:
        classic = self.w.takeCentralWidget()
        root = QtWidgets.QWidget()
        root.setObjectName("lrtRoot")
        root.setStyleSheet(model.shell_qss(self.tokens))
        grid = QtWidgets.QVBoxLayout(root)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(self._top_bar())
        grid.addWidget(self._alarm_bar())
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._rail())
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self._machine_page())
        classic_page = QtWidgets.QWidget()
        classic_page.setObjectName("lrtClassic")
        lay = QtWidgets.QVBoxLayout(classic_page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(classic)
        self.stack.addWidget(classic_page)
        self.diag = pages.DiagPage(self)
        self.production = pages.ProductionPage(self)
        self.start = pages.StartPage(self)
        self.pages = {"machine": 0, "classic": 1, "diag": self.stack.addWidget(self.diag),
                      "production": self.stack.addWidget(self.production),
                      "start": self.stack.addWidget(self.start)}
        self.page_widgets = {"diag": self.diag, "production": self.production,
                             "start": self.start}
        body.addWidget(self.stack, 1)
        grid.addLayout(body, 1)
        grid.addWidget(self._bottom_bar())
        self.w.setCentralWidget(root)
        self.w.setWindowTitle("linumeRT")
        # Widok klasyczny potrzebuje ok. 1280 px samego QtDragon + szyna: startowo 1440 × 960,
        # jeśli ekran pozwala (mniejszy ekran: QtDragon ściśnięty, widok „Maszyna” bez zmian).
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None and not self.w.isFullScreen():
            area = screen.availableGeometry()
            self.w.resize(min(max(self.w.width(), 1440), area.width()),
                          min(max(self.w.height(), 960), area.height()))
        self._connect_status()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)
        self.select_area("start")  # po uruchomieniu zawsze Start (HMI_WORKFLOW)
        self.refresh()
        return self

    def _top_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QFrame()
        bar.setObjectName("lrtTopBar")
        lay = QtWidgets.QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(12)
        logo = QtWidgets.QLabel()
        logo.setObjectName("lrtLogo")
        logo.setTextFormat(QtCore.Qt.RichText)
        logo.setText(f"linume<span style='color:{self.c['teal']}'>RT</span>")
        lay.addWidget(logo)
        modes = QtWidgets.QButtonGroup(bar)
        for mode in model.MODES:
            btn = QtWidgets.QPushButton(model.MODE_LABEL[mode])
            btn.setCheckable(True)
            btn.setToolTip({"manual": "Tryb ręczny (JOG)", "mdi": "Tryb MDI",
                            "auto": "Tryb automatyczny"}[mode])
            btn.clicked.connect(lambda _c=False, m=mode: self.set_mode(m))
            modes.addButton(btn)
            lay.addWidget(btn)
            self.buttons[f"mode_{mode}"] = btn
        prog = QtWidgets.QVBoxLayout()
        prog.setSpacing(0)
        prog.addWidget(_label("PROGRAM", "lrtMuted"))
        self.lbl_program = _label("—", "lrtProgram")
        prog.addWidget(self.lbl_program)
        lay.addSpacing(12)
        lay.addLayout(prog)
        lay.addStretch(1)
        self.lbl_plant = _label("", "", pill="info")
        self.lbl_machine = _label("", "", pill="err")
        self.lbl_clock = _label("", "lrtClock")
        for wdg in (self.lbl_plant, self.lbl_machine, self.lbl_clock):
            lay.addWidget(wdg)
        return bar

    def _alarm_bar(self) -> QtWidgets.QWidget:
        self.alarm = QtWidgets.QFrame()
        self.alarm.setObjectName("lrtAlarm")
        self.alarm.setProperty("level", "info")
        lay = QtWidgets.QHBoxLayout(self.alarm)
        lay.setContentsMargins(16, 6, 8, 6)
        self.lbl_alarm = QtWidgets.QLabel()
        self.lbl_alarm.setWordWrap(True)
        lay.addWidget(self.lbl_alarm, 1)
        close = QtWidgets.QPushButton("Potwierdź")
        close.setToolTip("Ukryj komunikat (historia: Diagnostyka)")
        close.clicked.connect(self.clear_alarm)
        lay.addWidget(close)
        self.alarm.hide()
        return self.alarm

    def _rail(self) -> QtWidgets.QWidget:
        rail = QtWidgets.QFrame()
        rail.setObjectName("lrtRail")
        rail.setFixedWidth(96)
        lay = QtWidgets.QVBoxLayout(rail)
        lay.setContentsMargins(8, 12, 8, 12)
        lay.setSpacing(6)
        group = QtWidgets.QButtonGroup(rail)
        for area, text, icon, _btn in AREAS:
            btn = QtWidgets.QToolButton()
            btn.setText(text.replace(" ", "\n", 1) if len(text) > 11 else text)
            btn.setObjectName("lrtRailBtn")
            btn.setCheckable(True)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            btn.setIcon(_icon(icon, self.c["fg2"]))
            btn.setIconSize(QtCore.QSize(24, 24))
            btn.setToolTip(f"Obszar: {text} (bez ruchu i bez zmiany trybu)")
            btn.clicked.connect(lambda _c=False, a=area: self.select_area(a))
            group.addButton(btn)
            lay.addWidget(btn)
            self.areas[area] = btn
        lay.addStretch(1)
        return rail

    def _machine_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setObjectName("lrtPage")
        grid = QtWidgets.QGridLayout(page)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.addWidget(self._dro_card(), 0, 0)
        grid.addWidget(self._program_card(), 1, 0)
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(16)
        right.addWidget(self._tool_card())
        right.addWidget(self._feed_card())
        right.addWidget(self._manual_card(), 1)
        grid.addLayout(right, 0, 1, 2, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        grid.setRowStretch(1, 1)
        return page

    def _dro_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_dro_head = _card("Pozycja · układ detalu G54", "mm · do przejechania")
        self.dro: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QLabel, QtWidgets.QLabel]] = {}
        rows = QtWidgets.QGridLayout()
        rows.setHorizontalSpacing(16)
        for i, axis in enumerate(self.s.axes):
            main = _label(model.fmt_pos(0.0), "lrtDro")
            main.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            small = _label(model.fmt_pos(0.0), "lrtDroSmall")
            small.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            homed = _label("◎", "lrtHomed", homed="false")
            homed.setToolTip("Oś bazowana")
            rows.addWidget(_label(axis, "lrtAxis"), i, 0)
            rows.addWidget(main, i, 1)
            rows.addWidget(small, i, 2)
            rows.addWidget(homed, i, 3)
            self.dro[axis] = (main, small, homed)
        rows.setColumnStretch(1, 1)
        lay.addLayout(rows)
        views = QtWidgets.QHBoxLayout()
        group = QtWidgets.QButtonGroup(frame)
        for view in model.DRO_VIEWS:
            btn = QtWidgets.QPushButton(model.DRO_VIEW_LABEL[view])
            btn.setCheckable(True)
            btn.setChecked(view == self.dro_view)
            btn.clicked.connect(lambda _c=False, v=view: self.set_dro_view(v))
            group.addButton(btn)
            views.addWidget(btn)
        views.addStretch(1)
        lay.addLayout(views)
        return frame

    def _program_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_line = _card("Bieżący blok", "brak programu")
        self.code_rows = []
        for _ in range(5):
            row = _label("", "lrtCode", current="false")
            row.setTextFormat(QtCore.Qt.PlainText)
            lay.addWidget(row)
            self.code_rows.append(row)
        self.bar_program = QtWidgets.QProgressBar()
        self.bar_program.setTextVisible(False)
        lay.addWidget(self.bar_program)
        lay.addStretch(1)
        return frame

    def _tool_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_tool_side = _card("Narzędzie", "")
        self.lbl_tool = _label("T0 · brak narzędzia", "lrtTitle")
        self.lbl_tool_info = _label("", "lrtMuted")
        lay.addWidget(self.lbl_tool)
        lay.addWidget(self.lbl_tool_info)
        return frame

    def _feed_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_feed_ovr = _card("Posuw", "korekcja 100 %")
        self.lbl_feed = _label("0", "lrtBig")
        lay.addWidget(self.lbl_feed)
        self.bar_feed = QtWidgets.QProgressBar()
        self.bar_feed.setRange(0, max(round(INFO.MAX_FEED_OVERRIDE), 100))
        self.bar_feed.setTextVisible(False)
        lay.addWidget(self.bar_feed)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(_label("WRZECIONO S1", "lrtCardTitle"))
        head.addStretch(1)
        self.lbl_spindle_ovr = _label("korekcja 100 %", "lrtMuted")
        head.addWidget(self.lbl_spindle_ovr)
        lay.addSpacing(6)
        lay.addLayout(head)
        self.lbl_spindle = _label("0 obr/min", "lrtBig")
        lay.addWidget(self.lbl_spindle)
        self.bar_spindle = QtWidgets.QProgressBar()
        self.bar_spindle.setRange(0, max(round(INFO.MAX_SPINDLE_OVERRIDE), 100))
        self.bar_spindle.setTextVisible(False)
        lay.addWidget(self.bar_spindle)
        return frame

    def _manual_card(self) -> QtWidgets.QWidget:
        frame, lay, self.lbl_jog_side = _card("Ruch ręczny i MDI", "")
        jog = QtWidgets.QGridLayout()
        jog.setSpacing(8)
        for i, axis in enumerate(self.s.axes[:4]):
            for j, (sign, direction) in enumerate((("−", -1), ("+", 1))):
                btn = QtWidgets.QPushButton(f"{axis}{sign}")
                btn.setProperty("role", "jog")
                btn.setToolTip(f"JOG {axis}{sign}: przytrzymaj (prędkość i krok jak w QtDragon)")
                btn.setAutoRepeat(False)
                btn.pressed.connect(lambda a=axis, d=direction: self.jog(a, d))
                btn.released.connect(lambda a=axis: self.jog(a, 0))
                jog.addWidget(btn, i // 2, (i % 2) * 2 + j)
                self.buttons[f"jog_{axis}{direction}"] = btn
        lay.addLayout(jog)
        mdi = QtWidgets.QHBoxLayout()
        self.mdi = QtWidgets.QLineEdit()
        self.mdi.setObjectName("lrtMdi")
        self.mdi.setPlaceholderText("MDI, np. G0 X10 Y10")
        self.mdi.returnPressed.connect(self.send_mdi)
        send = QtWidgets.QPushButton("Wyślij")
        send.clicked.connect(self.send_mdi)
        self.buttons["mdi"] = send
        mdi.addWidget(self.mdi, 1)
        mdi.addWidget(send)
        lay.addLayout(mdi)
        lay.addStretch(1)
        return frame

    def _bottom_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QFrame()
        bar.setObjectName("lrtBottomBar")
        lay = QtWidgets.QHBoxLayout(bar)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(10)
        spec = (
            ("start", "Cykl start", "start", "start", self.cycle_start),
            ("pause", "Wstrzymaj", "pauza", "pause", ACTION.PAUSE),
            ("stop", "Stop", "stop", "stop", ACTION.ABORT),
            ("step", "Pojedynczy blok", "blok", "", ACTION.STEP),
            ("home", "Bazuj wszystkie", "bazuj", "", self.home_all),
            ("power", "Maszyna", "maszyna", "power", self.toggle_power),
        )
        for key, text, icon, role, slot in spec:
            btn = QtWidgets.QPushButton(text)
            btn.setIcon(_icon(icon, self.c["fg"]))
            btn.setIconSize(QtCore.QSize(20, 20))
            btn.setMinimumHeight(56)
            if role:
                btn.setProperty("role", role)
            btn.clicked.connect(lambda _c=False, f=slot: f())
            lay.addWidget(btn)
            self.buttons[key] = btn
        lay.addStretch(1)
        estop = QtWidgets.QVBoxLayout()
        estop.setSpacing(2)
        estop.addWidget(_label("Obwód E-STOP", "lrtMuted"), 0, QtCore.Qt.AlignRight)
        self.lbl_estop = _label("", "")
        estop.addWidget(self.lbl_estop, 0, QtCore.Qt.AlignRight)
        lay.addLayout(estop)
        btn = QtWidgets.QPushButton("E-STOP")
        btn.setProperty("role", "estop")
        btn.setMinimumHeight(56)
        btn.setToolTip("Programowy E-STOP LinuxCNC. Obwód sprzętowy E-STOP jest nadrzędny.")
        btn.clicked.connect(self.toggle_estop)
        lay.addWidget(btn)
        self.buttons["estop"] = btn
        return bar

    # ---- STATUS → stan ------------------------------------------------------------------
    def _connect_status(self) -> None:
        s = self.s

        def setter(attr, value_fn=lambda *a: a[-1]):
            def cb(_w, *args):
                setattr(s, attr, value_fn(*args))
                self.refresh()
            return cb

        STATUS.connect("state-estop", lambda _w: self._estop())
        STATUS.connect("state-estop-reset", lambda _w: self._event(estop=False))
        STATUS.connect("state-on", lambda _w: self._event(machine_on=True))
        STATUS.connect("state-off", lambda _w: self._event(machine_on=False))
        STATUS.connect("mode-manual", lambda _w: self._set(mode="manual"))
        STATUS.connect("mode-mdi", lambda _w: self._set(mode="mdi"))
        STATUS.connect("mode-auto", lambda _w: self._set(mode="auto"))
        STATUS.connect("interp-idle", lambda _w: self._set(interp="idle"))
        STATUS.connect("interp-run", lambda _w: self._set(interp="run"))
        STATUS.connect("interp-paused", lambda _w: self._set(interp="paused"))
        STATUS.connect("program-pause-changed",
                       lambda _w, p: self._set(interp="paused" if p else
                                               ("run" if s.interp == "paused" else s.interp)))
        STATUS.connect("homed", lambda _w, j: self._homed(j, True))
        STATUS.connect("unhomed", lambda _w, j: self._homed(j, False))
        STATUS.connect("all-homed", lambda _w: self._set(homed=set(s.axes)))
        STATUS.connect("file-loaded", lambda _w, f: self._file(f))
        STATUS.connect("line-changed", setter("line"))
        STATUS.connect("tool-in-spindle-changed", setter("tool", int))
        # Posuw przychodzi przy każdym odpytaniu stanu (co CYCLE_TIME): tylko etykieta, bez
        # pełnego odświeżenia ekranu.
        STATUS.connect("current-feed-rate", lambda _w, v: self._feed(v))
        STATUS.connect("feed-override-changed", setter("feed_override", lambda v: v / 100.0))
        STATUS.connect("rapid-override-changed", setter("rapid_override", lambda v: v / 100.0))
        STATUS.connect("spindle-override-changed",
                       setter("spindle_override", lambda v: v / 100.0))
        STATUS.connect("requested-spindle-speed-changed", setter("spindle_requested"))
        STATUS.connect("actual-spindle-speed-changed", setter("spindle_actual"))
        STATUS.connect("spindle-control-changed",
                       lambda _w, _n, on, direction, *_r: self._set(
                           spindle_dir=direction if on else 0))
        STATUS.connect("metric-mode-changed", setter("metric", bool))
        STATUS.connect("user-system-changed",
                       lambda _w, d: self._set(user_system=f"G{53 + int(float(d))}"
                                               if str(d).replace('.', '', 1).isdigit() else str(d)))
        STATUS.connect("error", lambda _w, kind, text: self.show_alarm(
            model.error_level(kind, NML_KINDS), text))
        STATUS.connect("current-position", self._positions)

    def _event(self, **values) -> None:
        """Zmiana stanu maszyny z wpisem do historii (Diagnostyka)."""
        texts = {("estop", False): "E-STOP zwolniony", ("machine_on", True): "Maszyna włączona",
                 ("machine_on", False): "Maszyna wyłączona"}
        for key, value in values.items():
            if getattr(self.s, key) != value and (key, value) in texts and hasattr(self, "diag"):
                self.diag.add_log("info", texts[(key, value)])
        self._set(**values)

    def _estop(self) -> None:
        if self.s.estop:  # stan początkowy albo powtórzony sygnał: bez alarmu
            self._estop_requested = False
            return
        loop = pages._hal("lrt-net.0.din-00")
        connected = pages._hal("lrt-net.0.connected")
        missed = pages._hal("lrt-net.0.missed")
        delta = None if missed is None or not self._missed else int(missed) - self._missed[0]
        reason = model.estop_reason(None if loop is None else bool(loop),
                                    None if connected is None else bool(connected), delta,
                                    requested=self._estop_requested)
        self._estop_requested = False
        self._set(estop=True, machine_on=False)
        self.show_alarm("err", reason)

    def _feed(self, value: float) -> None:
        if abs(value - self.s.feed) < 0.5:
            return
        self.s.feed = value
        units = "mm" if self.s.metric else "in"
        self.lbl_feed.setText(f"{model.fmt_int(value)} {units}/min")

    def _set(self, **values) -> None:
        for key, value in values.items():
            setattr(self.s, key, value)
        self.refresh()

    def _homed(self, joint, state: bool) -> None:
        # Sygnał podaje numer stawu; osie z INFO (gantry XYYZ: stawy 1 i 2 = oś Y).
        try:
            axis = INFO.GET_NAME_FROM_JOINT.get(int(joint), "").upper()[:1]
        except (AttributeError, ValueError):
            axis = ""
        if axis:
            (self.s.homed.add if state else self.s.homed.discard)(axis)
        self.refresh()

    def _file(self, path: str) -> None:
        self.s.file = path or ""
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                self.program_lines = fh.read().splitlines()
        except OSError:
            self.program_lines = []
        self.s.total_lines = len(self.program_lines)
        self.refresh()

    def _positions(self, _w, absolute, relative, dtg, _joints) -> None:
        self.positions = (relative, absolute, dtg)
        self._refresh_dro()

    # ---- akcje (wyłącznie ACTION QtVCP) -----------------------------------------------------
    def set_mode(self, mode: str) -> None:
        if not self._allowed("mode"):
            return
        {"manual": ACTION.SET_MANUAL_MODE, "mdi": ACTION.SET_MDI_MODE,
         "auto": ACTION.SET_AUTO_MODE}[mode]()

    def cycle_start(self) -> None:
        if not self._allowed("start"):
            return
        ACTION.RUN(0)
        if hasattr(self.h, "start_timer"):
            self.h.start_timer()
        self.h.add_status(f"Start programu {os.path.basename(self.s.file)}")

    def home_all(self) -> None:
        if self._allowed("home"):
            ACTION.SET_MACHINE_HOMING(-1)

    def toggle_power(self) -> None:
        if self._allowed("power"):
            ACTION.SET_MACHINE_STATE(not self.s.machine_on)

    def toggle_estop(self) -> None:
        self._estop_requested = not self.s.estop
        ACTION.SET_ESTOP_STATE(not self.s.estop)

    def jog(self, axis: str, direction: int) -> None:
        if direction and not self._allowed("jog"):
            return
        ACTION.DO_JOG(axis, direction)

    def send_mdi(self) -> None:
        text = self.mdi.text().strip()
        if not text or not self._allowed("mdi"):
            return
        ACTION.CALL_MDI(text)
        self.mdi.clear()

    def _allowed(self, key: str) -> bool:
        gate = model.gates(self.s)[key]
        if not gate.enabled:
            self.show_alarm("warn", f"Niedostępne: {gate.reason}")
        return gate.enabled

    # ---- nawigacja (tylko prezentacja) ---------------------------------------------------
    def select_area(self, area: str) -> None:
        self.areas[area].setChecked(True)
        target = dict((a, b) for a, _t, _i, b in AREAS)[area]
        if target.startswith("page:"):
            page = target[5:]
            self.stack.setCurrentIndex(self.pages[page])
            if page in self.page_widgets:
                self.page_widgets[page].refresh()
            return
        self.stack.setCurrentIndex(self.pages["classic"])
        btn = getattr(self.w, target, None)
        if btn is not None and btn.isEnabled():
            btn.click()  # przełącza tylko stronę QtDragon (main_tab_changed), bez ruchu

    def set_dro_view(self, view: str) -> None:
        self.dro_view = view
        self._refresh_dro()

    # ---- alarmy -------------------------------------------------------------------------
    def show_alarm(self, level: str, text: str) -> None:
        text = " ".join(str(text).split())
        if not text:
            return
        self.s.alarm = model.Alarm(level, text)
        if getattr(self, "diag", None) is not None:
            self.diag.add_log(level, text)
        self.lbl_alarm.setText(text)
        _restyle(self.alarm, level=level)
        self.alarm.show()

    def clear_alarm(self) -> None:
        self.s.alarm = None
        self.alarm.hide()

    # ---- odświeżanie ----------------------------------------------------------------------
    def _tick(self) -> None:
        self.lbl_clock.setText(time.strftime("%H:%M"))
        current = self.stack.currentWidget()
        if current in self.page_widgets.values():
            current.refresh()
        missed = pages._hal("lrt-net.0.missed")
        if missed is not None and not self.s.estop:
            self._missed.append(int(missed))  # odniesienie przyczyny E-STOP: najstarsza próbka
        plant = self._plant_link()
        if plant != self.s.plant:
            if self.s.plant is not None or plant == "lost":
                self.show_alarm("err" if plant == "lost" else "info",
                                "Łącze LRT-NET z Plant utracone" if plant == "lost"
                                else "Łącze LRT-NET z Plant odzyskane")
            self.s.plant = plant
            self.refresh()

    def _plant_link(self) -> str | None:
        """Stan łącza LRT-NET z pinu lrt-net.0.connected (brak komponentu = symulator)."""
        try:
            import hal

            return "ok" if hal.get_value("lrt-net.0.connected") else "lost"
        except Exception:  # noqa: BLE001 - brak pinu albo HAL: konfiguracja bez Plant
            return None

    def _refresh_dro(self) -> None:
        source = {"work": 0, "machine": 1, "dtg": 2}[self.dro_view]
        main, dtg = self.positions[source], self.positions[2]
        for axis, (big, small, homed) in self.dro.items():
            index = "XYZABCUVW".find(axis)
            big.setText(model.fmt_pos(main[index], self.s.metric))
            small.setText(model.fmt_pos(dtg[index], self.s.metric))
            want = "true" if axis in self.s.homed else "false"
            if homed.property("homed") != want:
                _restyle(homed, homed=want)

    def refresh(self) -> None:
        s, g = self.s, model.gates(self.s)
        production = getattr(self, "production", None)
        if production is not None:
            production.on_state()
            current = self.stack.currentWidget()
            if current is production:
                current.refresh()  # bieżąca linia i postęp; Start odświeża _tick (0,5 s)
        for mode in model.MODES:
            btn = self.buttons[f"mode_{mode}"]
            btn.setChecked(s.mode == mode)
            btn.setEnabled(g["mode"].enabled)
        self.lbl_program.setText(os.path.basename(s.file) or "—")
        text, level = model.machine_pill(s)
        self.lbl_machine.setText(text)
        _restyle(self.lbl_machine, pill=level)
        text, level = model.plant_pill(s)
        self.lbl_plant.setText(text)
        _restyle(self.lbl_plant, pill=level)
        units = "mm" if s.metric else "in"
        view = {"work": f"układ detalu {s.user_system}", "machine": "układ maszyny G53",
                "dtg": "do przejechania"}[self.dro_view]
        self.lbl_dro_head.setText(f"{units} · {view} │ małe: do przejechania")
        self._refresh_dro()
        rows = model.program_window(self.program_lines, s.line)
        for label, row in zip(self.code_rows, rows + [None] * len(self.code_rows), strict=False):
            if row is None:
                label.setText("")
                continue
            n, code, current = row
            label.setText(f"N{n:<5} {code}")
            want = "true" if current else "false"
            if label.property("current") != want:
                _restyle(label, current=want)
        self.lbl_line.setText(f"linia {s.line} z {s.total_lines}" if s.file else "brak programu")
        self.bar_program.setRange(0, max(s.total_lines, 1))
        self.bar_program.setValue(min(s.line, max(s.total_lines, 1)))
        self.lbl_tool.setText(f"T{s.tool}" + ("" if s.tool else " · brak narzędzia"))
        self.lbl_tool_info.setText(self._tool_info(s.tool))
        self.lbl_feed.setText(f"{model.fmt_int(s.feed)} {units}/min")
        self.lbl_feed_ovr.setText(f"korekcja {model.fmt_pct(s.feed_override)}")
        self.bar_feed.setValue(round(s.feed_override * 100))
        _restyle(self.bar_feed, level="warn" if abs(s.feed_override - 1) > 0.01 else "")
        rpm = s.spindle_actual or s.spindle_requested
        turn = {1: " · M3", -1: " · M4"}.get(s.spindle_dir, " · stop")
        self.lbl_spindle.setText(f"{model.fmt_int(abs(rpm))} obr/min{turn}")
        self.lbl_spindle_ovr.setText(f"korekcja {model.fmt_pct(s.spindle_override)}")
        self.bar_spindle.setValue(round(s.spindle_override * 100))
        for key in ("start", "pause", "stop", "step", "home", "power", "mdi"):
            gate = g[key]
            self.buttons[key].setEnabled(gate.enabled)
            self.buttons[key].setToolTip(gate.reason)
        self.buttons["pause"].setText("Wznów" if s.interp == "paused" else "Wstrzymaj")
        self.buttons["power"].setText("Maszyna WŁ." if s.machine_on else "Maszyna WYŁ.")
        _restyle(self.buttons["power"], active="true" if s.machine_on else "false")
        self.buttons["estop"].setText("E-STOP" if not s.estop else "Zwolnij E-STOP")
        _restyle(self.buttons["estop"], active="true" if s.estop else "false")
        self.lbl_estop.setText("otwarty" if s.estop else "zamknięty")
        self.lbl_estop.setStyleSheet(f"color: {self.c['err'] if s.estop else self.c['ok']};"
                                     "font-weight: 600;")
        jog_ok = g["jog"]
        for key, btn in self.buttons.items():
            if key.startswith("jog_"):
                btn.setEnabled(jog_ok.enabled)
                btn.setToolTip(jog_ok.reason or btn.toolTip())
        self.lbl_jog_side.setText("" if jog_ok.enabled else jog_ok.reason)

    def _tool_info(self, tool: int) -> str:
        if not tool:
            return "wymiana ręczna: M6 T… w MDI"
        try:
            info = STATUS.get_toolinfo(tool)
        except Exception:  # noqa: BLE001 - narzędzie spoza tabeli
            return ""
        if not info:
            return ""
        return (f"D {info[11]:.3f} · Z {info[3]:.3f} · kieszeń P{info[1]}"
                if len(info) > 11 else "")


def install(handler) -> LinumertShell:
    return LinumertShell(handler).install()
