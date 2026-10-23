# SPDX-License-Identifier: GPL-2.0-or-later
"""Model nakładki linumeRT na QtDragon: stan, reguły dostępności akcji, formatowanie, styl.

Model-Author: Claude · HMI-PoC (2026-10-19).

Bez Qt i bez LinuxCNC: testy w zwykłym pytest (`tests/test_hmi_shell_model.py`). Część Qt
(`linumert_shell.py`) tylko przepisuje sygnały STATUS do `ShellState` i pyta ten moduł, co pokazać
i co wolno włączyć. Reguły są warstwą wygody operatora, nie funkcją bezpieczeństwa: LinuxCNC
i tak odrzuca niedozwolone komendy, a E-STOP to obwód sprzętowy (CLAUDE.md §6).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Kopia docs/design/tokens.yaml (kolory i rozmiary) na wypadek braku pliku albo PyYAML;
# zgodność pilnuje test. Wygląd wyłącznie z tokenów (CLAUDE.md §6a).
TOKENS_FALLBACK = {
    "kolory": {
        "bg": "#0a0c0f", "bg2": "#0f1317", "panel": "#12171d", "raise": "#182029",
        "line": "#26303a", "line2": "#34404c", "fg": "#e8eef4", "fg2": "#9aa7b4",
        "fg3": "#66727e", "teal": "#2dd4bf", "teal2": "#5eead4", "tealbg": "#0e2c29",
        "amber": "#fbbf24", "amberbg": "#2a2110", "ok": "#4ade80", "okbg": "#11301d",
        "err": "#f87171", "errbg": "#341416", "info": "#7dd3fc", "infobg": "#132634",
    },
    "rozmiary": {
        "min_tekst_px": 12, "dro_px": 28, "cel_dotykowy_px": 44, "odstep_px": 8,
        "promien_kart_px": 14, "promien_przyciskow_px": 12,
    },
}

FONT_UI = '"IBM Plex Sans", "DejaVu Sans", sans-serif'
FONT_NUM = '"JetBrains Mono", "DejaVu Sans Mono", monospace'

MODES = ("manual", "mdi", "auto")
MODE_LABEL = {"manual": "JOG", "mdi": "MDI", "auto": "AUTO"}
DRO_VIEWS = ("work", "machine", "dtg")
DRO_VIEW_LABEL = {"work": "Układ detalu", "machine": "Układ maszyny", "dtg": "Do przejechania"}


def repo_root(here: str | None = None) -> str:
    """Katalog repozytorium z położenia ekranu (dowiązanie z konfiguracji → realpath)."""
    here = os.path.dirname(os.path.realpath(here or __file__))
    return os.path.normpath(os.path.join(here, "..", ".."))


def load_tokens(path: str | None = None) -> dict:
    """Tokeny wyglądu z docs/design/tokens.yaml; przy braku pliku albo PyYAML kopia wbudowana."""
    path = path or os.path.join(repo_root(), "docs", "design", "tokens.yaml")
    try:
        import yaml

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict) and "kolory" in data and "rozmiary" in data:
            return data
    except (OSError, ImportError, ValueError):
        pass
    return TOKENS_FALLBACK


def icon_path(name: str) -> str:
    return os.path.join(repo_root(), "docs", "design", "ikony", f"{name}.svg")


@dataclass
class Alarm:
    level: str  # "err" | "warn" | "info"
    text: str


@dataclass
class ShellState:
    """Stan maszyny widziany przez nakładkę (wypełniany sygnałami STATUS QtVCP)."""

    specialist: bool = False
    virtual: bool = False
    estop: bool = True
    machine_on: bool = False
    mode: str = "manual"
    interp: str = "idle"  # idle | run | paused
    homed: set[str] = field(default_factory=set)
    axes: tuple[str, ...] = ("X", "Y", "Z")
    file: str = ""
    line: int = 0
    total_lines: int = 0
    tool: int = 0
    feed: float = 0.0
    feed_override: float = 1.0
    rapid_override: float = 1.0
    spindle_requested: float = 0.0
    spindle_actual: float = 0.0
    spindle_override: float = 1.0
    spindle_dir: int = 0
    metric: bool = True
    user_system: str = "G54"
    plant: str | None = None  # None = brak lrt_net (symulator); "ok" | "lost"
    alarm: Alarm | None = None
    hmi_pressed: bool = False  # grzyb E-STOP w HMI wciśnięty (pin linumert.hmi-estop-ok = 0, D35)

    @property
    def all_homed(self) -> bool:
        return all(a in self.homed for a in self.axes)

    @property
    def running(self) -> bool:
        return self.interp in ("run", "paused")


@dataclass(frozen=True)
class Gate:
    enabled: bool
    reason: str = ""


def gates(s: ShellState) -> dict[str, Gate]:
    """Które przyciski nakładki są aktywne i dlaczego nie (podpowiedź dla operatora)."""
    def need(ok: bool, reason: str) -> Gate:
        return Gate(True) if ok else Gate(False, reason)

    ready = not s.estop and s.machine_on
    idle = s.interp == "idle"
    first = ("E-STOP aktywny" if s.estop else "maszyna wyłączona" if not s.machine_on else "")
    g = {
        "estop": Gate(True),
        "power": need(not s.estop, "najpierw zwolnij E-STOP"),
        "mode": need(ready and not s.running, first or "program w toku"),
        "home": need(ready and idle, first or "program w toku"),
        "jog": need(ready and idle and s.mode == "manual", first or (
            "program w toku" if not idle else "przełącz na JOG")),
        "mdi": need(ready and idle and s.all_homed and not s.specialist, first or (
            "tryb specjalisty: tylko JOG" if s.specialist else
            "program w toku" if not idle else "najpierw bazowanie")),
        "start": need(ready and not s.specialist and s.all_homed and bool(s.file) and s.interp != "run", first or (
            "najpierw bazowanie" if not s.all_homed else "brak programu" if not s.file
            else "program w toku")),
        "pause": need(s.running, "brak programu w toku"),
        # Stop (abort) jest bezpieczny w każdym trybie: dostępny zawsze przy włączonej maszynie.
        "stop": need(ready, first),
        "step": need(ready and not s.specialist and s.all_homed and bool(s.file), first or (
            "najpierw bazowanie" if not s.all_homed else "brak programu")),
    }
    return g


def machine_pill(s: ShellState) -> tuple[str, str]:
    """Tekst i poziom kolorystyczny stanu maszyny w górnym pasku."""
    if s.estop:
        return ("E-STOP · grzyb HMI" if s.hmi_pressed else "E-STOP"), "err"
    if not s.machine_on:
        return "Maszyna wyłączona", "warn"
    if s.interp == "run":
        return "Program w toku", "ok"
    if s.interp == "paused":
        return "Wstrzymany", "warn"
    if not s.all_homed:
        return "Niebazowana", "warn"
    return "Gotowa", "ok"


def plant_pill(s: ShellState) -> tuple[str, str]:
    if s.plant is None:
        return "Symulator LinuxCNC", "info"
    if s.plant == "ok":
        return "Plant · LRT-NET", "ok"
    return "Plant · brak łącza", "err"


def fmt_pos(value: float, metric: bool = True) -> str:
    return f"{value:.4f}"


def fmt_int(value: float) -> str:
    """Liczba całkowita z odstępem tysięcy (18 000), jak na makiecie 01."""
    return f"{round(value):,}".replace(",", " ")


def fmt_pct(value: float) -> str:
    return f"{round(value * 100)} %"


def error_level(kind: int, kinds: dict[str, int]) -> str:
    """Poziom alarmu z rodzaju komunikatu LinuxCNC (`linuxcnc.NML_ERROR` itd.)."""
    if kind in (kinds.get("NML_ERROR"), kinds.get("OPERATOR_ERROR")):
        return "err"
    return "info"


def program_window(lines: list[str], current: int, before: int = 1, after: int = 3
                   ) -> list[tuple[int, str, bool]]:
    """Wycinek programu wokół bieżącej linii (numeracja od 1): (nr, tekst, czy bieżąca)."""
    if not lines:
        return []
    cur = min(max(current, 1), len(lines))
    start = max(1, cur - before)
    end = min(len(lines), start + before + after)
    return [(n, lines[n - 1].rstrip(), n == cur) for n in range(start, end + 1)]


def shell_qss(tokens: dict) -> str:
    """Arkusz stylu nakładki wyłącznie z tokenów (kolory, promienie, cele dotykowe)."""
    c, r = tokens["kolory"], tokens["rozmiary"]
    touch, card, btn = r["cel_dotykowy_px"], r["promien_kart_px"], r["promien_przyciskow_px"]
    small = r["min_tekst_px"]
    return f"""
#lrtRoot, #lrtRoot QWidget#lrtPage {{ background: {c['bg']}; color: {c['fg']}; font-family: {FONT_UI}; }}
#lrtTopBar, #lrtBottomBar {{ background: {c['bg2']}; border: 0; }}
#lrtTopBar {{ border-bottom: 1px solid {c['line']}; }}
#lrtBottomBar {{ border-top: 1px solid {c['line']}; }}
QFrame#lrtRail {{ background: {c['bg2']}; border: none; border-right: 1px solid {c['line']}; }}
QFrame#lrtTopBar, QFrame#lrtBottomBar {{ border-left: none; border-right: none; }}
QWidget#lrtClassic {{ border: none; }}
#lrtRoot QCheckBox {{ color: {c['fg']}; background: transparent; }}
#lrtRoot QScrollArea {{ border: none; background: {c['bg']}; }}
#lrtRoot QLabel {{ color: {c['fg']}; background: transparent; }}
QLabel#lrtLogo {{ font-size: 20px; font-weight: 700; }}
QLabel#lrtMuted, QLabel#lrtCardTitle {{ color: {c['fg2']}; font-size: {small}px; }}
QLabel#lrtMuted[dirty="true"] {{ color: {c['amber']}; font-weight: 600; }}
QLabel#lrtCardTitle {{ letter-spacing: 1px; font-weight: 600; }}
QLabel#lrtProgram {{ font-family: {FONT_NUM}; color: {c['fg']}; }}
QLabel#lrtClock {{ font-family: {FONT_NUM}; font-size: 20px; }}
QLabel[pill="ok"], QLabel[pill="warn"], QLabel[pill="err"], QLabel[pill="info"] {{
    border-radius: {btn + 4}px; padding: 6px 14px; font-weight: 600; }}
QLabel[pill="ok"] {{ background: {c['okbg']}; color: {c['ok']}; border: 1px solid {c['ok']}; }}
QLabel[pill="warn"] {{ background: {c['amberbg']}; color: {c['amber']}; border: 1px solid {c['amber']}; }}
QLabel[pill="err"] {{ background: {c['errbg']}; color: {c['err']}; border: 1px solid {c['err']}; }}
QLabel[pill="info"] {{ background: {c['infobg']}; color: {c['info']}; border: 1px solid {c['info']}; }}
QFrame#lrtAlarm {{ border: 0; }}
QFrame#lrtAlarm[level="err"] {{ background: {c['errbg']}; }}
QFrame#lrtAlarm[level="warn"] {{ background: {c['amberbg']}; }}
QFrame#lrtAlarm[level="info"] {{ background: {c['infobg']}; }}
QFrame#lrtAlarm QLabel {{ font-family: {FONT_NUM}; }}
QFrame#lrtAlarm[level="err"] QLabel {{ color: {c['err']}; }}
QFrame#lrtAlarm[level="warn"] QLabel {{ color: {c['amber']}; }}
QFrame#lrtAlarm[level="info"] QLabel {{ color: {c['info']}; }}
QFrame#lrtCard {{ background: {c['panel']}; border: 1px solid {c['line']}; border-radius: {card}px; }}
QLabel#lrtAxis {{ color: {c['teal']}; font-size: {r['dro_px']}px; font-weight: 700; }}
QLabel#lrtDro {{ font-family: {FONT_NUM}; font-size: {r['dro_px'] + 18}px; font-weight: 500; }}
QLabel#lrtDroSmall {{ font-family: {FONT_NUM}; color: {c['fg2']}; font-size: 18px; }}
QLabel#lrtHomed[homed="true"] {{ color: {c['ok']}; }}
QLabel#lrtHomed[homed="false"] {{ color: {c['fg3']}; }}
QLabel#lrtTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#lrtBig {{ font-family: {FONT_NUM}; font-size: {r['dro_px'] + 4}px; }}
QLabel#lrtCode {{ font-family: {FONT_NUM}; color: {c['fg3']}; padding: 4px 10px; }}
QLabel#lrtCode[current="true"] {{ color: {c['fg']}; background: {c['tealbg']};
    border-left: 3px solid {c['teal']}; border-radius: 6px; }}
QProgressBar {{ background: {c['raise']}; border: 0; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {c['teal']}; border-radius: 3px; }}
QProgressBar[level="warn"]::chunk {{ background: {c['amber']}; }}
#lrtRoot QPushButton {{ background: {c['raise']}; color: {c['fg']}; border: 1px solid {c['line2']};
    border-radius: {btn}px; min-height: {touch}px; padding: 0 14px; font-size: 14px; }}
#lrtRoot QPushButton:hover {{ border-color: {c['teal']}; }}
#lrtRoot QPushButton:disabled {{ color: {c['fg3']}; border-color: {c['line']}; background: {c['bg2']}; }}
#lrtRoot QPushButton:checked {{ background: {c['tealbg']}; color: {c['teal']}; border-color: {c['teal']}; }}
QToolButton#lrtRailBtn {{ background: transparent; border: 0; border-radius: {btn}px; min-height: 64px;
    color: {c['fg2']}; font-size: {small}px; padding: 6px 2px; }}
QToolButton#lrtRailBtn:hover {{ background: {c['raise']}; }}
QToolButton#lrtRailBtn:checked {{ background: {c['tealbg']}; color: {c['fg']}; font-weight: 600; }}
QPushButton[role="start"] {{ background: {c['teal']}; color: {c['bg']}; border-color: {c['teal']}; font-weight: 700; }}
QPushButton[role="start"]:disabled {{ background: {c['tealbg']}; color: {c['fg3']}; }}
QPushButton[role="pause"] {{ background: {c['amberbg']}; color: {c['amber']}; border-color: {c['amber']}; }}
QPushButton[role="stop"] {{ background: {c['errbg']}; color: {c['err']}; border-color: {c['err']}; }}
QPushButton#lrtMushroom {{ border-radius: 38px; font-weight: 800; font-size: 13px; color: {c['fg']};
    min-height: 0; padding: 0; }}
QPushButton#lrtMushroom[state="armed"] {{ background: {c['err']}; border: 5px solid {c['amber']}; }}
QPushButton#lrtMushroom[state="pressed"] {{ background: {c['errbg']}; color: {c['err']};
    border: 5px solid {c['err']}; }}
QPushButton#lrtMushroom[state="latched"] {{ background: {c['err']}; border: 5px solid {c['err']};
    color: {c['bg']}; }}
QPushButton[role="estop"] {{ background: {c['errbg']}; color: {c['err']}; border: 2px solid {c['err']};
    font-weight: 700; min-width: 120px; }}
QPushButton[role="estop"][active="false"] {{ background: {c['okbg']}; color: {c['ok']}; border-color: {c['ok']}; }}
QPushButton[role="power"][active="true"] {{ background: {c['okbg']}; color: {c['ok']}; border-color: {c['ok']}; }}
QPushButton[role="jog"] {{ font-family: {FONT_NUM}; font-size: 16px; min-width: 64px; }}
QLineEdit#lrtMdi {{ background: {c['bg2']}; color: {c['fg']}; border: 1px solid {c['line2']};
    border-radius: {btn}px; min-height: {touch}px; padding: 0 12px; font-family: {FONT_NUM};
    font-size: 16px; }}
QLineEdit#lrtMdi:focus {{ border-color: {c['teal']}; }}
QLabel#lrtValue {{ font-family: {FONT_NUM}; font-size: 15px; }}
QLabel#lrtBit {{ font-family: {FONT_NUM}; font-size: {small}px; border-radius: 6px; padding: 4px;
    min-width: 28px; }}
QLabel#lrtBit[on="false"] {{ background: {c['raise']}; color: {c['fg3']}; }}
QLabel#lrtBit[on="true"] {{ background: {c['okbg']}; color: {c['ok']}; }}
QTableWidget#lrtTable, QListWidget#lrtLog {{ background: {c['bg2']}; color: {c['fg']}; border: 0;
    border-radius: {btn}px; font-family: {FONT_NUM}; font-size: 13px; }}
QTableWidget#lrtTable::item {{ padding: 4px 8px; border-bottom: 1px solid {c['line']}; }}
QHeaderView::section {{ background: {c['panel']}; color: {c['fg2']}; border: 0;
    border-bottom: 1px solid {c['line2']}; padding: 6px 8px; font-size: {small}px; }}
QSlider#lrtSlider::groove:horizontal {{ background: {c['raise']}; height: 8px; border-radius: 4px; }}
QSlider#lrtSlider::sub-page:horizontal {{ background: {c['teal']}; border-radius: 4px; }}
QSlider#lrtSlider::handle:horizontal {{ background: {c['fg']}; width: 24px; margin: -10px 0;
    border-radius: 12px; }}
QSpinBox#lrtSpin {{ background: {c['bg2']}; color: {c['fg']}; border: 1px solid {c['line2']};
    border-radius: {btn}px; min-height: {touch}px; padding: 0 12px; font-family: {FONT_NUM};
    font-size: 16px; }}
QLabel#lrtTitleSmall {{ font-size: 16px; font-weight: 600; }}
QLabel#lrtDot {{ font-size: 18px; }}
QLabel#lrtDot[level="ok"] {{ color: {c['ok']}; }}
QLabel#lrtDot[level="warn"] {{ color: {c['amber']}; }}
QLabel#lrtDot[level="err"] {{ color: {c['err']}; }}
QLabel#lrtDot[level="info"] {{ color: {c['info']}; }}
QToolTip {{ background: {c['raise']}; color: {c['fg']}; border: 1px solid {c['line2']}; }}
"""


# ---- diagnostyka (CiA 402, LRT-NET, alarmy) ---------------------------------------------------

CIA402_STATES = (  # (maska, wartość, nazwa, poziom) według 6041h, kolejność ma znaczenie
    (0x4F, 0x08, "Błąd", "err"),
    (0x4F, 0x0F, "Reakcja na błąd", "err"),
    (0x4F, 0x40, "Wyłączony (switch on disabled)", "warn"),
    (0x6F, 0x21, "Gotowy do załączenia", "warn"),
    (0x6F, 0x23, "Załączony", "warn"),
    (0x6F, 0x27, "Praca", "ok"),
    (0x6F, 0x07, "Szybki stop", "err"),
)


def cia402_state(statusword: int) -> tuple[str, str]:
    """Stan napędu CiA 402 ze słowa 6041h: (nazwa, poziom)."""
    for mask, value, name, level in CIA402_STATES:
        if statusword & mask == value:
            return name, level
    return "Rozruch (not ready)", "info"


def drive_fault_codes(drive_h: str) -> dict[int, str]:
    """Kod 603Fh → alarm katalogu z listy LRT_DRIVE_FAULT_LIST w plant/core/drive.h."""
    import re

    return {int(code, 16): alarm for code, alarm in
            re.findall(r"X\(\w+,\s*\d+,\s*(0x[0-9A-Fa-f]+),\s*\"([EWKP]-\d{4})\"\)", drive_h)}


def catalog_texts(catalog: list) -> dict[str, str]:
    """Kod alarmu → tekst polski z core/linumert/alarms/catalog.yaml (lista wpisów)."""
    return {e["code"]: e.get("pl", "") for e in catalog or [] if isinstance(e, dict) and "code" in e}


def alarm_text(code: str, texts: dict[str, str], **params) -> str:
    """„E-4201 · tekst” z parametrami; brakujące parametry jako „?”."""
    import string

    text = texts.get(code, "")
    fields = {f for _, f, _, _ in string.Formatter().parse(text) if f}
    values = {f: params.get(f, "?") for f in fields}
    try:
        text = text.format(**values)
    except (KeyError, IndexError, ValueError):
        pass
    return f"{code} · {text}" if text else code


def drive_error_text(error_code: int, faults: dict[int, str], texts: dict[str, str],
                     axis: str = "?") -> str:
    if not error_code:
        return "—"
    code = faults.get(error_code)
    if code is None:
        return f"603Fh = 0x{error_code:04X}"
    return alarm_text(code, texts, axis=axis, error_code=f"0x{error_code:04X}", ms="?")


LINK_COUNTERS = (  # (pin lrt-net.0.*, etykieta)
    ("sent", "Ramki wysłane"),
    ("received", "Odpowiedzi"),
    ("missed", "Cykle bez odpowiedzi"),
    ("bad-frames", "Odpowiedzi odrzucone"),
    ("send-errors", "Błędy wysyłania"),
    ("plant-lost", "Plant: utracone"),
    ("plant-late", "Plant: spóźnione"),
    ("plant-jitter-us", "Plant: jitter [µs]"),
    ("reply-age", "Wiek odpowiedzi [cykle]"),
)


# ---- produkcja ------------------------------------------------------------------------------

@dataclass
class RunClock:
    """Czas pracy programu: liczy tylko stan „run” (pauza i bezczynność nie)."""

    elapsed: float = 0.0
    since: float | None = None

    def update(self, interp: str, now: float) -> None:
        if interp == "run":
            if self.since is None:
                self.since = now
        elif self.since is not None:
            self.elapsed += now - self.since
            self.since = None

    def value(self, now: float) -> float:
        return self.elapsed + (now - self.since if self.since is not None else 0.0)

    def reset(self) -> None:
        self.elapsed, self.since = 0.0, None


def fmt_duration(seconds: float) -> str:
    total = max(int(seconds), 0)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def run_from_line_gate(s: ShellState, line: int) -> Gate:
    """Start od linii: jak Cykl start, plus numer w zakresie programu."""
    base = gates(s)["start"]
    if not base.enabled:
        return base
    if s.interp != "idle":
        return Gate(False, "program w toku")
    if not 1 <= line <= max(s.total_lines, 1):
        return Gate(False, f"linia poza zakresem 1–{s.total_lines}")
    return Gate(True)


RUN_FROM_LINE_WARNING = ("Start od linii {line} pomija wcześniejsze bloki: wybór narzędzia (M6), "
                         "obroty wrzeciona (S/M3), chłodziwo, układ detalu i tryby G. Sprawdź, czy "
                         "maszyna jest w stanie, jakiego wymaga linia {line}.")


# ---- start (lista gotowości) ---------------------------------------------------------------

@dataclass(frozen=True)
class CheckItem:
    key: str
    label: str
    level: str  # ok | warn | err | info
    detail: str
    action: str = ""  # klucz akcji powłoki: estop | power | home | program | production | ""


def checklist(s: ShellState, drive_fault: bool | None = None) -> list[CheckItem]:
    """Lista gotowości widoku Start (kolejność pracy operatora)."""
    unhomed = [a for a in s.axes if a not in s.homed]
    items = [
        CheckItem("estop", "Obwód E-STOP", "err" if s.estop else "ok",
                  ("grzyb HMI wciśnięty" if s.hmi_pressed else
                   "otwarty: usuń przyczynę i potwierdź grzybem w HMI") if s.estop else "zamknięty",
                  "estop" if s.estop else ""),
        CheckItem("power", "Zasilanie napędów", "ok" if s.machine_on else "err",
                  "włączone" if s.machine_on else "maszyna wyłączona",
                  "" if s.machine_on or s.estop else "power"),
        CheckItem("homed", "Bazowanie osi", "ok" if not unhomed else "warn",
                  "wszystkie osie zbazowane" if not unhomed else
                  f"niebazowane: {', '.join(unhomed)}",
                  "" if not unhomed or not s.machine_on else "home"),
    ]
    if s.plant is None:
        items.append(CheckItem("plant", "Łącze z maszyną", "info",
                               "symulator LinuxCNC (bez Plant)"))
    else:
        items.append(CheckItem("plant", "Łącze LRT-NET (Plant)", "ok" if s.plant == "ok" else "err",
                               "połączone" if s.plant == "ok" else "brak odpowiedzi Plant"))
    if drive_fault is not None:
        items.append(CheckItem("drives", "Napędy", "err" if drive_fault else "ok",
                               "awaria napędu: zobacz Diagnostykę" if drive_fault else "bez awarii",
                               "diag" if drive_fault else ""))
    items += [
        CheckItem("program", "Program", "ok" if s.file else "warn",
                  os.path.basename(s.file) if s.file else "nie wybrano programu",
                  "" if s.file else "program"),
        CheckItem("tool", "Narzędzie w uchwycie", "ok" if s.tool else "warn",
                  f"T{s.tool}" if s.tool else "brak (T0): wymiana M6 w MDI albo w programie"),
    ]
    overrides = [f"{name} {fmt_pct(v)}" for name, v in
                 (("F", s.feed_override), ("S", s.spindle_override), ("G0", s.rapid_override))
                 if abs(v - 1.0) > 0.005]
    items.append(CheckItem("overrides", "Korekcje", "warn" if overrides else "ok",
                           ", ".join(overrides) if overrides else "100 %",
                           "production" if overrides else ""))
    return items


def ready_to_run(items: list[CheckItem]) -> bool:
    return all(i.level in ("ok", "info") for i in items
               if i.key in ("estop", "power", "homed", "plant", "drives", "program"))


ACTION_LABEL = {"estop": "Potwierdź grzybem", "power": "Włącz", "home": "Bazuj wszystkie",
                "program": "Wybierz program", "production": "Produkcja", "diag": "Diagnostyka"}


def estop_reason(loop_closed: bool | None, connected: bool | None, missed_delta: int | None,
                 requested: bool = False, hmi_alive: bool | None = None) -> str:
    """Przyczyna przejścia w E-STOP z odczytów HAL (None = brak pinu, np. symulator)."""
    if requested:
        return "E-STOP: grzyb E-STOP w HMI wciśnięty"
    if hmi_alive is False:
        return "E-STOP: brak sygnału życia HMI (watchdog) — ekran nie odpowiadał"
    if loop_closed is False:
        return "E-STOP: pętla E-STOP otwarta (grzybek albo obwód bezpieczeństwa, din-00)"
    if connected is False or (missed_delta or 0) >= 20:
        tail = f", {missed_delta} cykli bez odpowiedzi" if missed_delta else ""
        return f"E-STOP: przerwa łącza LRT-NET z Plant{tail}"
    if loop_closed is None and connected is None:
        return "E-STOP: sygnał zezwolenia LinuxCNC (emc-enable-in) wyłączony"
    return "E-STOP: łańcuch bezpieczeństwa HAL zwolnił zezwolenie (przyczyna przejściowa)"


def mushroom_view(s: ShellState) -> tuple[str, str, str]:
    """Grzyb E-STOP w HMI: (napis, podpis, stan stylu: pressed | latched | armed)."""
    if s.hmi_pressed:
        return "E-STOP", "wciśnięty · kliknij, aby zwolnić i potwierdzić", "pressed"
    if s.estop:
        return "E-STOP", "obwód otwarty · potwierdź grzybem", "latched"
    return "E-STOP", "gotowy · kliknij, aby zatrzymać", "armed"

