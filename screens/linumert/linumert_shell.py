# SPDX-License-Identifier: GPL-2.0-or-later
"""Nakładka linumeRT na QtDragon: powłoka (pasek trybu i stanu, szyna obszarów, pasek akcji)
i widok „Maszyna” według makiety docs/design/makiety/01_maszyna.png.

Model-Author: Claude · HMI-PoC (2026-10-19). Proof of concept: funkcje dochodzą etapami
(docs/design/HMI_WORKFLOW.md).

Zasady (HMI_WORKFLOW.md, CLAUDE.md §6):
- własne strony operatora współdzielą stan LinuxCNC; bazowy QtDragon pozostaje w stosie stron;
- zmiana obszaru nie wykonuje ruchu ani zmiany trybu;
- komendy maszyny wyłącznie przez ACTION QtVCP, stan wyłącznie ze STATUS QtVCP;
- ekran nie jest funkcją bezpieczeństwa; grzyb E-STOP w HMI to DODATKOWY, szeregowy element
  łańcucha E-STOP w HAL (D35, config/hal/linumert_hmi_estop.hal): wciśnięcie odbiera zezwolenie,
  zwolnienie albo podwójny Reset potwierdza zatrzask E-STOP, ekran wysyła sygnał życia
  (watchdog HAL). Obwód sprzętowy maszyny jest nadrzędny i podłączony do HAL fizycznie.
"""

from __future__ import annotations

import collections
import os
import time

import linuxcnc
from PyQt5 import QtCore, QtGui, QtWidgets
from qtvcp.core import Action, Info, Status

from linumert_alarm_panel import AlarmPanel
from linumert_layout import PageStack
from linumert_operator_controls import OperatorControls
from linumert_virtual_session import VirtualSession, virtual_config
import linumert_shell_model as model
import linumert_shell_pages as pages
from linumert_homing_page import HomingPage
from linumert_program_page import ProgramPage
from linumert_offsets_page import OffsetsPage
from linumert_preflight import Preflight
import linumert_sim_page as sim_page

try:  # baza narzędzi wymaga rdzenia linumert (pyyaml); bez niego obszar = tabela QtDragon
    import linumert_tools_page as tools_page
    TOOLS_ERROR = ""
except Exception as exc:  # noqa: BLE001 - nakładka musi wstać także bez tej strony
    tools_page = None
    TOOLS_ERROR = f"{type(exc).__name__}: {exc}"
try:  # generatory cykli: rdzeń linumert (pyyaml); bez niego obszar Cykle = widok Program
    import linumert_cycles_page as cycles_page
except Exception:  # noqa: BLE001 - nakładka musi wstać także bez tej strony
    cycles_page = None

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
    ("homing", "Bazowanie", "bazuj", "page:homing"),
    ("production", "Produkcja", "start", "page:production"),
    ("sim", "Symulacja", "symulacja", "page:sim"),
    ("program", "Program", "program", "page:program"),
    ("cycles", "Cykle", "dialog", "page:cycles"),
    ("tools", "Narzędzia", "narzedzia", "page:tools"),
    ("offsets", "Zero detalu", "zero", "page:offsets"),
    ("probe", "Sonda", "sonda", "btn_probe"),
    ("diag", "Diagnostyka", "diagnostyka", "page:diag"),
    ("settings", "Konfiguracja", "konfiguracja", "btn_settings"),
    ("classic", "Pełny QtDragon", "wtyczka", "btn_main"),
)
if os.environ.get("LINUMERT_OPERATOR_SKIN"):
    AREAS = (("skin", "HMI", "maszyna", "page:skin"), *AREAS)


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

    def __init__(self, handler, hmi_pins: dict | None = None):
        super().__init__(handler.w)
        self.h = handler
        self.w = handler.w
        self.action, self.info, self.status = ACTION, INFO, STATUS
        # Piny grzyba HMI (D35): ok = 1 grzyb zwolniony, hb = sygnał życia, wd = uzbrojenie watchdoga
        self.hmi_pins = hmi_pins or {}
        self.tokens = model.load_tokens()
        self.c = self.tokens["kolory"]
        self.s = model.ShellState(axes=tuple(a.upper() for a in INFO.AVAILABLE_AXES))
        ini = os.environ.get("INI_FILE_NAME") or getattr(INFO, "INIPATH", "")
        self.s.virtual = bool(ini and virtual_config(ini))
        # Sesja 007: język ekranu przed budową widoków (teksty przez translate(), źródło EN).
        from linumert_i18n import install as install_language
        from linumert_i18n import language_from_ini

        self.language = language_from_ini(ini)
        install_language(self.language)

        # Sesja 036: role operator/technolog/serwis (PIN w SQLite obok INI); bez PIN-ów wyłączone.
        import linumert_access_ui as access_ui

        self.access, self.access_reason = access_ui.open_session(ini)
        self.current_area: str | None = None
        self.virtual_session = VirtualSession(self)
        self.dro_view = "work"
        self.program_lines: list[str] = []
        self.positions = ([0.0] * 9, [0.0] * 9, [0.0] * 9)
        self.areas: dict[str, QtWidgets.QToolButton] = {}
        self._missed: collections.deque[int] = collections.deque(maxlen=5)  # ok. 2 s historii
        self._estop_requested = False
        self.sim_cause = ""  # ostatnia kolizja/przeciążenie z symulacji (przyczyna E-STOP)
        self.buttons: dict[str, QtWidgets.QPushButton] = {}
        self.operator_panels = []
        from linumert_pause_retract import RetractControl

        self.retract = RetractControl(self)

    # ---- budowa ---------------------------------------------------------------------------
    def install(self) -> LinumertShell:
        # Sesja 027: fonty z tokens.yaml dołączone do ekranu (OFL), przed zastosowaniem QSS.
        from linumert_fonts import register as register_fonts

        self.fonts = register_fonts()
        classic = self.w.takeCentralWidget()
        root = QtWidgets.QWidget()
        root.setObjectName("lrtRoot")
        root.setStyleSheet(model.shell_qss(self.tokens))
        grid = QtWidgets.QVBoxLayout(root)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(self._alarm_bar())
        grid.addWidget(self._top_bar())
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._rail())
        self.stack = PageStack()
        self.stack.addWidget(self._machine_page())
        classic_page = QtWidgets.QWidget()
        classic_page.setObjectName("lrtClassic")
        lay = QtWidgets.QVBoxLayout(classic_page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(classic)
        self.stack.addWidget(classic_page)
        self.preflight = Preflight(parent=self)
        self.diag = pages.DiagPage(self)
        self.production = pages.ProductionPage(self)
        self.start = pages.StartPage(self)
        self.homing = HomingPage(self)
        self.program = ProgramPage(self)
        self.sim = sim_page.SimPage(self)
        ini = os.environ.get("INI_FILE_NAME") or getattr(INFO, "INIPATH", "")
        self.tools = tools_page.ToolsPage(self, ini) if tools_page is not None else None
        self.offsets = OffsetsPage(self)
        self.pages = {"machine": 0, "classic": 1, "diag": self.stack.addWidget(self.diag),
                      "production": self.stack.addWidget(self.production),
                      "start": self.stack.addWidget(self.start),
                      "sim": self.stack.addWidget(self.sim),
                      "homing": self.stack.addWidget(self.homing),
                      "program": self.stack.addWidget(self.program),
                      "offsets": self.stack.addWidget(self.offsets)}
        self.page_widgets = {"diag": self.diag, "production": self.production,
                             "start": self.start, "sim": self.sim,
                             "homing": self.homing, "program": self.program, "offsets": self.offsets}
        self.cycles = cycles_page.CyclesPage(self) if cycles_page is not None else None
        if self.cycles is not None:
            self.pages["cycles"] = self.stack.addWidget(self.cycles)
            self.page_widgets["cycles"] = self.cycles
        if self.tools is not None:
            self.pages["tools"] = self.stack.addWidget(self.tools)
            self.page_widgets["tools"] = self.tools
        content = QtWidgets.QScrollArea()
        content.setWidgetResizable(True)
        content.setFrameShape(QtWidgets.QFrame.NoFrame)
        content.setWidget(self.stack)
        body.addWidget(content, 1)
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
        loaded = getattr(getattr(STATUS, "stat", None), "file", "")
        if isinstance(loaded, str) and loaded and not self.s.file:
            self._file(loaded)  # program wczytany przy starcie, zanim ekran podłączył status
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)
        self._start_mushroom()
        if os.environ.get("LINUMERT_OPERATOR_SKIN"):
            from linumert_skin_contract import PresentationPreferences
            from linumert_skin_qtvcp import OperatorSkin

            preferences = PresentationPreferences(
                skin=os.environ["LINUMERT_OPERATOR_SKIN"],
                theme=os.environ.get("LINUMERT_OPERATOR_THEME", "classic-turquoise"),
                language=self.language)
            self.skin_host = OperatorSkin(self, preferences)
            self.pages["skin"] = self.stack.addWidget(self.skin_host)
        if TOOLS_ERROR:
            self.diag.add_log("warn", f"Strona Narzędzia linumeRT niedostępna ({TOOLS_ERROR}); "
                                      "obszar Narzędzia = tabela QtDragon")
        ini = os.environ.get("INI_FILE_NAME") or getattr(INFO, "INIPATH", "")
        if ini:
            self.sim.start(ini)  # proces symulacji materiału i kolizji (nice 10)
        # po uruchomieniu Start (HMI_WORKFLOW); LINUMERT_START_AREA tylko do testów i pokazów
        area = os.environ.get("LINUMERT_START_AREA", "skin" if hasattr(self, "skin_host")
                              else "start")
        self.select_area(area if area in self.areas else "start")
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
        import linumert_access_ui as access_ui

        self.role_button = access_ui.RoleButton(self.access, self.access_reason)
        self.role_button.changed.connect(lambda role: self.show_alarm(
            "info", f"Rola: {access_ui.ROLE_LABEL[role]}"))
        for wdg in (self.lbl_plant, self.lbl_machine, self.role_button, self.lbl_clock):
            lay.addWidget(wdg)
        return bar

    def _alarm_bar(self) -> QtWidgets.QWidget:
        self.alarm = AlarmPanel(self)
        self.lbl_alarm = self.alarm.rows[0]
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
        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(116)
        scroll.setWidget(rail)
        return scroll

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
        panel = OperatorControls(self)
        self.operator_panels.append(panel)
        self.mdi = panel.mdi
        self.buttons.update(panel.buttons)
        lay.addWidget(panel)
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
        self.lbl_mushroom = _label("", "lrtMuted")
        estop.addWidget(self.lbl_mushroom, 0, QtCore.Qt.AlignRight)
        lay.addLayout(estop)
        btn = QtWidgets.QPushButton("E-STOP")
        btn.setObjectName("lrtMushroom")
        btn.setProperty("state", "armed")
        btn.setFixedSize(76, 76)
        btn.setToolTip("Grzyb E-STOP w HMI: dodatkowy element łańcucha E-STOP (HAL). Wciśnięty "
                       "odbiera zezwolenie; zwolnienie potwierdza E-STOP. Obwód sprzętowy maszyny "
                       "jest nadrzędny. Klawisz F1 = wciśnięcie.")
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
        reason = self._estop_cause(requested=self._estop_requested)
        if self.sim_cause:
            reason = f"E-STOP z symulacji: {self.sim_cause}"
            self.sim_cause = ""
        self._estop_requested = False
        self._set(estop=True, machine_on=False)
        self.show_alarm("err", reason, "safety")

    def _estop_cause(self, requested: bool = False) -> str:
        if pages._hal("lrt-estop2.0.fault"):
            return ("E-STOP: rozbieżność kanałów A/B obwodu E-STOP (styk albo przewód) — "
                    "test: wciśnij i zwolnij grzyb sprzętowy, potem Reset")
        loop = pages._hal("lrt-net.0.din-00")
        connected = pages._hal("lrt-net.0.connected")
        missed = pages._hal("lrt-net.0.missed")
        alive = pages._hal("watchdog.ok-out")
        delta = None if missed is None or not self._missed else int(missed) - self._missed[0]
        return model.estop_reason(None if loop is None else bool(loop),
                                  None if connected is None else bool(connected), delta,
                                  requested=requested or self.s.hmi_pressed,
                                  hmi_alive=None if alive is None else bool(alive))

    # ---- grzyb E-STOP w HMI (D35) -------------------------------------------------------
    def _pin(self, key: str, value: bool) -> None:
        pin = self.hmi_pins.get(key)
        if pin is not None:
            pin.set(bool(value))

    def _start_mushroom(self) -> None:
        missing = [k for k in ("ok", "hb", "wd", "ack") if not hasattr(self.hmi_pins.get(k), "set")
                   or type(self.hmi_pins[k]).__name__ == "DummyPin"]
        if missing:
            self.show_alarm("err", "Grzyb E-STOP w HMI niedostępny (brak pinów HAL linumert.hmi-*): "
                                   "łańcuch E-STOP pozostaje otwarty")
        self._pin("ok", True)  # grzyb zwolniony; E-STOP i tak zatrzaśnięty do potwierdzenia
        self._pin("wd", False)
        self._pin("ack", False)
        self._heartbeat = False
        self._hb_timer = QtCore.QTimer(self)
        self._hb_timer.timeout.connect(self._beat)
        self._hb_timer.start(100)
        QtCore.QTimer.singleShot(400, lambda: self._pin("wd", True))  # zbocze: uzbrojenie watchdoga

    def _beat(self) -> None:
        self._heartbeat = not self._heartbeat
        self._pin("hb", self._heartbeat)

    def press_estop(self) -> None:
        """Wciśnięcie grzyba: natychmiast, bez warunków i potwierdzeń."""
        self.s.hmi_pressed = True
        self._pin("ok", False)
        self._estop_requested = True
        ACTION.SET_ESTOP_STATE(True)
        if hasattr(self, "diag"):
            self.diag.add_log("err", "Grzyb E-STOP w HMI wciśnięty")
        self.refresh()

    def acknowledge_estop(self) -> None:
        """Zwolnienie grzyba = potwierdzenie E-STOP: uzbrojenie watchdoga i reset zatrzasku."""
        self.s.hmi_pressed = False
        self._pin("ok", True)
        self._pin("ack", True)  # zbocze: potwierdzenie zdarzenia w zatrzasku HAL lrt_hmi_ack
        self._pin("wd", False)
        QtCore.QTimer.singleShot(100, lambda: (self._pin("wd", True), self._pin("ack", False)))
        QtCore.QTimer.singleShot(300, lambda: ACTION.SET_ESTOP_STATE(False))
        QtCore.QTimer.singleShot(1500, self._check_acknowledge)
        if hasattr(self, "diag"):
            self.diag.add_log("info", "Grzyb E-STOP w HMI zwolniony: potwierdzenie E-STOP")
        self.refresh()

    def _check_acknowledge(self) -> None:
        if self.s.estop and not self.s.hmi_pressed:
            cause = self._estop_cause().replace("E-STOP: ", "")
            self.show_alarm("err", f"Potwierdzenie nieskuteczne: obwód E-STOP nadal otwarty ({cause})")

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
        if self.s.file and hasattr(self, "preflight"):
            self.preflight.request(self.s.file)

    def _positions(self, _w, absolute, relative, dtg, _joints) -> None:
        self.positions = (relative, absolute, dtg)
        self._refresh_dro()

    # ---- akcje (wyłącznie ACTION QtVCP) -----------------------------------------------------
    def set_mode(self, mode: str) -> None:
        if self.s.specialist and mode != "manual":
            self.show_alarm("warn", "Tryb specjalisty: dostępny tylko JOG")
            return
        if not self._allowed("mode"):
            return
        {"manual": ACTION.SET_MANUAL_MODE, "mdi": ACTION.SET_MDI_MODE,
         "auto": ACTION.SET_AUTO_MODE}[mode]()

    def cycle_start(self) -> None:
        if not self._allowed("start"):
            return
        if not self._confirm_limits():
            return
        ACTION.RUN(0)
        if hasattr(self.h, "start_timer"):
            self.h.start_timer()
        self.h.add_status(f"Start programu {os.path.basename(self.s.file)}")

    def _confirm_limits(self) -> bool:
        bad = self.preflight.violations(self.s.file) if hasattr(self, "preflight") else []
        if not bad:
            return True
        more = "\n".join(v.message() for v in bad[:4])
        answer = QtWidgets.QMessageBox.question(
            QtWidgets.QApplication.activeWindow(), "Program wyjdzie poza limity osi",
            f"{more}\n\nLinuxCNC zatrzyma maszynę w trakcie obróbki. Poprawiono układ detalu "
            "albo program? Uruchomić mimo to?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            self.h.add_status("Start anulowany: program poza limitami osi")
            return False
        return True

    def home_all(self) -> None:
        if self._allowed("home"):
            ACTION.SET_MACHINE_HOMING(-1)

    def toggle_power(self) -> None:
        if self._allowed("power"):
            ACTION.SET_MACHINE_STATE(not self.s.machine_on)

    def toggle_estop(self) -> None:
        if self.s.estop or self.s.hmi_pressed:
            self.acknowledge_estop()
        else:
            self.press_estop()

    def jog(self, axis: str, direction: int) -> None:
        if direction and not self._allowed("jog"):
            return
        if self.s.specialist:
            ACTION.SET_JOG_RATE(600 if getattr(INFO, "MACHINE_IS_METRIC", True) else 600 / 25.4)
        ACTION.DO_JOG(axis, direction)

    def set_specialist(self, enabled: bool) -> None:
        ACTION.ABORT()
        for axis in self.s.axes:
            ACTION.DO_JOG(axis, 0)
        self.virtual_session.finish()
        self.s.specialist = enabled
        if enabled:
            ACTION.SET_MANUAL_MODE()
            ACTION.SET_SPINDLE_STOP()
        if self.s.virtual:
            self.sim.client.send(cmd="recovery", on=enabled)
        self.refresh()

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
        import linumert_access_ui as access_ui

        permission = {"settings": "settings", "classic": "classic"}.get(area)
        if permission and not access_ui.require(self, permission, area):
            if self.current_area in self.areas:
                self.areas[self.current_area].setChecked(True)
            else:
                self.areas[area].setChecked(False)
            return
        self.current_area = area
        self.areas[area].setChecked(True)
        target = dict((a, b) for a, _t, _i, b in AREAS)[area]
        if target == "page:tools" and self.tools is None:
            target = "btn_tool"  # bez strony linumeRT: tabela narzędzi QtDragon
        if target == "page:cycles" and self.cycles is None:
            target = "page:program"
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
    def show_alarm(self, level: str, text: str, source: str = "") -> None:
        text = " ".join(str(text).split())
        if not text:
            return
        self.s.alarm = model.Alarm(level, text)
        if getattr(self, "diag", None) is not None:
            self.diag.add_log(level, text)
        self.alarm.add(level, text, source or ("controller" if level == "err" else ""))

    def clear_alarm(self) -> None:
        self.reset_alarms(False)

    def reset_alarms(self, double: bool = False) -> None:
        if double and (self.s.estop or self.s.hmi_pressed):
            self.acknowledge_estop()  # HAL odrzuci reset przy otwartym fizycznym safety
            QtCore.QTimer.singleShot(700, lambda: self.reset_alarms(False))
        self._alarm_causes()
        self.alarm.acknowledge()
        self.s.alarm = (model.Alarm(*self.alarm.entries[0][:2])
                        if self.alarm.entries else None)

    def _alarm_causes(self) -> None:
        active = set(getattr(self, "sim_active", set()))
        if self.s.estop:
            active.add("safety")
        if self.s.plant == "lost":
            active.add("plant")
        joints = getattr(self.status.stat, "joint", ())
        fault = any(j.get("fault") or j.get("min_hard_limit") or j.get("max_hard_limit")
                    for j in joints)
        if fault or self.s.estop or self.s.plant == "lost":
            active.add("controller")
        self.alarm.active = active

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
        self._alarm_causes()
        for panel in self.operator_panels:
            panel.refresh()
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
        text, hint, state = model.mushroom_view(s)
        self.buttons["estop"].setText(text)
        _restyle(self.buttons["estop"], state=state)
        self.lbl_mushroom.setText(hint)
        self.lbl_estop.setText("otwarty" if s.estop else "zamknięty")
        self.lbl_estop.setStyleSheet(f"color: {self.c['err'] if s.estop else self.c['ok']};"
                                     "font-weight: 600;")
        jog_ok = g["jog"]
        for key, btn in self.buttons.items():
            if key.startswith("jog_"):
                btn.setEnabled(jog_ok.enabled)
                btn.setToolTip(jog_ok.reason or btn.toolTip())
        self.lbl_jog_side.setText("" if jog_ok.enabled else jog_ok.reason)
        if getattr(self, "skin_host", None) is not None:
            self.skin_host.sync()

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


def install(handler, hmi_pins: dict | None = None) -> LinumertShell:
    return LinumertShell(handler, hmi_pins).install()
