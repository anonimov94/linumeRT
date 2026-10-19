# SPDX-License-Identifier: GPL-2.0-or-later
"""Samotest nakładki linumeRT w działającym GUI (Xvfb + LinuxCNC RIP).

Model-Author: Claude · HMI-PoC (2026-10-19).

Włączany wyłącznie zmienną środowiska `LINUMERT_SHELL_SELFTEST=<katalog wyników>`; bez niej
moduł nie jest importowany. Klika prawdziwe przyciski nakładki w procesie GUI (te same sloty co
operator), po każdym kroku zapisuje zrzut okna `NN_nazwa.png` i stan do `wynik.json`; LinuxCNC
zamyka wywołujący (okno potwierdzenia QtDragon przy zamykaniu nie blokuje testu). Uruchamia go `tests/test_hmi_shell_gui.py` (marker `linuxcnc`) i
`tools/dev/hmi-demo.sh`.

Scenariusz (Start → lista gotowości): zwolnienie E-STOP → maszyna WŁ. → bazowanie → MDI G0 → program w AUTO → Wstrzymaj →
Wznów → Stop → JOG X+ → obszary szyny (QtDragon) → powrót do „Maszyna” → Diagnostyka → Produkcja
(korekcja posuwu 80 %, start od linii 6 do końca programu, korekcja 100 %) → grzyb HMI
(wciśnięcie, nieskuteczny reset inną drogą, zwolnienie, brak sygnału życia → watchdog, potwierdzenie).
"""

from __future__ import annotations

import json
import os
import time

from PyQt5 import QtCore, QtWidgets
from qtvcp.core import Action, Status

STATUS = Status()
ACTION = Action()

PROGRAM = """( linumeRT · samotest nakładki: kwadrat 40 x 40 mm bez wymiany narzędzia )
( oś Z symulatora: -120…0 mm, więc wysokość bezpieczna Z-2 )
G21 G90 G17 G40 G49 G80
G0 Z-2
G0 X20 Y20
G1 Z-4 F300
G1 X60 F600
G1 Y60
G1 X20
G1 Y20
G0 Z-2
M2
"""


def _external_reset() -> None:
    """Reset E-STOP z pominięciem ekranu (jak komenda innego programu): linuxcnc.command()."""
    import linuxcnc

    linuxcnc.command().state(linuxcnc.STATE_ESTOP_RESET)


def _hal_value(name: str):
    try:
        import hal

        return bool(hal.get_value(name))
    except Exception:  # noqa: BLE001 - brak pinu
        return None


class SelfTest(QtCore.QObject):
    def __init__(self, shell, out_dir: str):
        super().__init__(shell)
        self.shell = shell
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.steps: list[dict] = []
        self.errors: list[str] = []
        self.program = os.path.join(out_dir, "linumert_hmi_selftest.ngc")
        with open(self.program, "w", encoding="utf-8") as fh:
            fh.write(PROGRAM)
        self.plan = self._plan()
        self.index = 0
        self.wait_until = None
        self.deadline = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self, delay_ms: int = 3000) -> None:
        QtCore.QTimer.singleShot(delay_ms, lambda: self.timer.start(200))

    # ---- scenariusz -------------------------------------------------------------------------
    def _plan(self) -> list[tuple]:
        s, b = self.shell.s, self.shell.buttons
        click = self._click
        return [
            ("01_start", None, None, 0),
            # Kroki 02–04 przyciskami listy gotowości widoku Start
            ("02_estop_zwolniony", lambda: self._start_action("estop"), lambda: not s.estop, 5),
            ("03_maszyna_wl", lambda: self._start_action("power"), lambda: s.machine_on, 5),
            ("04_bazowanie", lambda: self._start_action("homed"), lambda: s.all_homed, 90),
            ("04b_start_gotowosc", None, None, 1),
            ("04c_maszyna", lambda: click(self.shell.areas["machine"]), None, 1),
            ("05_tryb_mdi", lambda: click(b["mode_mdi"]), lambda: s.mode == "mdi", 5),
            ("06_mdi_g0", self._mdi, lambda: self._settled(), 30),
            ("07_program", lambda: ACTION.OPEN_PROGRAM(self.program),
             lambda: s.file.endswith("linumert_hmi_selftest.ngc"), 10),
            ("08_tryb_auto", lambda: click(b["mode_auto"]), lambda: s.mode == "auto", 5),
            ("09_cykl_start", lambda: click(b["start"]), lambda: s.interp == "run" and s.line >= 4,
             15),
            ("10_wstrzymany", lambda: click(b["pause"]), lambda: s.interp == "paused", 5),
            ("11_wznowiony", lambda: click(b["pause"]), lambda: s.interp == "run", 5),
            ("12_stop", lambda: click(b["stop"]), lambda: s.interp == "idle", 10),
            ("13_tryb_jog", lambda: click(b["mode_manual"]), lambda: s.mode == "manual", 5),
            ("14_jog_x_plus", self._jog, lambda: self._settled(), 10),
            ("15_obszar_program", lambda: click(self.shell.areas["program"]), None, 1),
            ("16_obszar_narzedzia", lambda: click(self.shell.areas["tools"]), None, 1),
            ("17_obszar_qtdragon", lambda: click(self.shell.areas["classic"]), None, 1),
            ("18_maszyna", lambda: click(self.shell.areas["machine"]), None, 1),
            ("19_diagnostyka", lambda: click(self.shell.areas["diag"]),
             lambda: self.shell.diag.joints.rowCount() >= len(s.axes), 5),
            ("20_produkcja", lambda: click(self.shell.areas["production"]), None, 1),
            ("21_korekcja_posuwu_80", lambda: self.shell.production.sliders["feed"][0].setValue(80),
             lambda: round(s.feed_override * 100) == 80, 5),
            ("22_tryb_auto", lambda: click(b["mode_auto"]), lambda: s.mode == "auto", 5),
            ("23_start_od_linii", self._from_line,
             lambda: s.interp == "run" and s.line >= 6, 15),
            ("24_program_koniec", None, lambda: s.interp == "idle", 60),
            ("25_korekcja_100", lambda: click(self._reset_feed()),
             lambda: round(s.feed_override * 100) == 100, 5),
            # D35: grzyb E-STOP w HMI w łańcuchu HAL
            ("26_grzyb_wcisniety", lambda: click(b["estop"]),
             lambda: s.estop and s.hmi_pressed and not s.machine_on, 5),
            ("27_reset_obejsciem", lambda: ACTION.SET_ESTOP_STATE(False), None, 2),
            ("28_grzyb_zwolniony", lambda: click(b["estop"]), lambda: not s.estop, 5),
            ("29_brak_sygnalu_zycia", self.shell._hb_timer.stop, lambda: s.estop, 8),
            ("30_potwierdzenie", self._resume_heartbeat, lambda: not s.estop, 5),
            ("31_maszyna_wl", lambda: click(b["power"]), lambda: s.machine_on, 5),
            # Przegląd Codexa P1: E-STOP z innej przyczyny (tu programowy) → reset bezpośrednią
            # komendą LinuxCNC (inny proces niż ekran) nieskuteczny → potwierdzenie grzybem działa.
            ("32_estop_programowy", lambda: ACTION.SET_ESTOP_STATE(True), lambda: s.estop, 5),
            ("33_reset_komenda", _external_reset, None, 2),
            ("34_potwierdzenie_grzybem", lambda: click(b["estop"]), lambda: not s.estop, 5),
        ]

    @staticmethod
    def _click(widget) -> None:
        if not widget.isEnabled():
            raise RuntimeError(f"przycisk „{widget.text()}” nieaktywny: {widget.toolTip()}")
        widget.click()

    def _from_line(self) -> None:
        page = self.shell.production
        page.spin_line.setValue(6)
        page.refresh()
        if not page.btn_from_line.isEnabled():
            raise RuntimeError(f"start od linii nieaktywny: {page.lbl_from_line.text()}")
        page.run_from_line(confirm=False)  # okno potwierdzenia pomija tylko samotest

    def _reset_feed(self):
        return self.shell.production.reset_buttons["feed"]

    def _resume_heartbeat(self) -> None:
        self.shell._hb_timer.start(100)
        QtCore.QTimer.singleShot(300, lambda: self._click(self.shell.buttons["estop"]))

    def _start_action(self, key: str) -> None:
        page = self.shell.start
        page.refresh()
        btn = page.row_widgets[key][3]
        if not btn.isVisible():
            raise RuntimeError(f"brak akcji przy „{key}” na liście gotowości")
        self._click(btn)

    def _mdi(self) -> None:
        self.shell.mdi.setText("G0 X100 Y80 Z-10")
        self._click(self.shell.buttons["mdi"])
        self._start_pos = None

    def _jog(self) -> None:
        btn = self.shell.buttons["jog_X1"]
        if not btn.isEnabled():
            raise RuntimeError(f"JOG nieaktywny: {btn.toolTip()}")
        btn.pressed.emit()
        QtCore.QTimer.singleShot(700, btn.released.emit)
        self._jog_released_at = time.monotonic() + 0.7

    def _settled(self) -> bool:
        """Ruch zakończony: interpreter bezczynny i brak prędkości (krótko po komendzie)."""
        if getattr(self, "_jog_released_at", 0) > time.monotonic():
            return False
        STATUS.stat.poll()
        return STATUS.stat.interp_state == 1 and abs(STATUS.stat.current_vel) < 1e-6 \
            and STATUS.stat.inpos

    # ---- pętla ------------------------------------------------------------------------------
    def _tick(self) -> None:
        now = time.monotonic()
        if self.wait_until is not None:
            name, check, _timeout = self.plan[self.index]
            ok = check() if check else now >= self.deadline
            if not ok and now < self.deadline:
                return
            if check and not ok:
                self.errors.append(f"{name}: przekroczony czas oczekiwania")
            self._record(name, ok if check else True)
            self.wait_until = None
            self.index += 1
        if self.index >= len(self.plan):
            self._finish()
            return
        name, action, check, timeout = self.plan[self.index]
        try:
            if action:
                action()
        except Exception as exc:  # noqa: BLE001 - błąd kroku trafia do wyniku testu
            self.errors.append(f"{name}: {exc}")
            self._record(name, False)
            self.index += 1
            return
        self.plan[self.index] = (name, check, timeout)
        self.wait_until = True
        self.deadline = now + max(timeout, 0.6)

    def _record(self, name: str, ok: bool) -> None:
        QtWidgets.QApplication.processEvents()
        path = os.path.join(self.out, f"{name}.png")
        self.shell.w.grab().save(path)
        s = self.shell.s
        rel = self.shell.positions[0]
        self.steps.append({
            "step": name, "ok": ok, "estop": s.estop, "machine_on": s.machine_on,
            "mode": s.mode, "interp": s.interp, "homed": sorted(s.homed), "line": s.line,
            "file": os.path.basename(s.file), "x": round(rel[0], 3), "y": round(rel[1], 3),
            "z": round(rel[2], 3), "area": self.shell.stack.currentIndex(),
            "page": {v: k for k, v in self.shell.pages.items()}[self.shell.stack.currentIndex()],
            "ready": self.shell.start.lbl_ready.text(),
            "hmi_pressed": s.hmi_pressed,
            "hmi_chain": _hal_value("lrt_hmi_bypass.out"),
            "hmi_alive": _hal_value("watchdog.ok-out"),
            "alarm": s.alarm.text if s.alarm else "",
            "start_enabled": self.shell.buttons["start"].isEnabled(),
            "diag_joints": self.shell.diag.joints.rowCount(),
            "diag_drives": self.shell.diag.drives.rowCount(),
            "log": self.shell.diag.log.count(),
            "feed_override": round(s.feed_override * 100),
            "run_time": self.shell.production.lbl_time.text(),
        })

    def _finish(self) -> None:
        self.timer.stop()
        with open(os.path.join(self.out, "wynik.json"), "w", encoding="utf-8") as fh:
            json.dump({"steps": self.steps, "errors": self.errors}, fh, indent=2,
                      ensure_ascii=False)


def maybe_start(shell) -> SelfTest | None:
    out = os.environ.get("LINUMERT_SHELL_SELFTEST")
    if not out:
        return None
    test = SelfTest(shell, out)
    test.start()
    return test


class ClassicSelfTest(QtCore.QObject):
    """Samotest trybu klasycznego (LINUMERT_SHELL=0, przegląd Codexa P2): reset przyciskiem QtDragon,
    brak sygnału życia → E-STOP, reset komendą z innego procesu nieskuteczny, wznowienie sygnału
    życia + przycisk QtDragon → zezwolenie, bez BYPASS i bez restartu ekranu."""

    def __init__(self, handler, out_dir: str):
        super().__init__(handler.w)
        self.h = handler
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.steps: list[dict] = []
        self.errors: list[str] = []
        clear = STATUS.estop_is_clear
        btn = handler.w.action_estop
        timer = handler._hb_timer
        self.plan = [
            ("c01_start", None, None, 0),
            ("c02_reset_przyciskiem", btn.click, lambda: clear(), 5),
            ("c03_brak_sygnalu_zycia", timer.stop, lambda: not clear(), 8),
            ("c04_reset_komenda", lambda: (timer.start(100), _external_reset()), None, 2),
            ("c05_reset_przyciskiem", btn.click, lambda: clear(), 5),
        ]
        self.index = 0
        self.waiting = False
        self.deadline = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        QtCore.QTimer.singleShot(3000, lambda: self.timer.start(200))

    def _tick(self) -> None:
        now = time.monotonic()
        name, action, check, timeout = self.plan[self.index]
        if self.waiting:
            ok = check() if check else now >= self.deadline
            if not ok and now < self.deadline:
                return
            if check and not ok:
                self.errors.append(f"{name}: przekroczony czas oczekiwania")
            STATUS.stat.poll()
            self.h.w.grab().save(os.path.join(self.out, f"{name}.png"))
            self.steps.append({"step": name, "ok": ok if check else True,
                               "estop": not STATUS.estop_is_clear(),
                               "hmi_chain": _hal_value("lrt_hmi_bypass.out"),
                               "hmi_alive": _hal_value("watchdog.ok-out"),
                               "hmi_acked": _hal_value("lrt_hmi_ack.out")})
            self.waiting = False
            self.index += 1
            if self.index >= len(self.plan):
                self.timer.stop()
                with open(os.path.join(self.out, "wynik.json"), "w", encoding="utf-8") as fh:
                    json.dump({"steps": self.steps, "errors": self.errors}, fh, indent=2,
                              ensure_ascii=False)
            return
        if action:
            try:
                action()
            except Exception as exc:  # noqa: BLE001 - błąd kroku trafia do wyniku testu
                self.errors.append(f"{name}: {exc}")
        self.waiting = True
        self.deadline = now + max(timeout, 0.6)


def maybe_start_classic(handler) -> ClassicSelfTest | None:
    out = os.environ.get("LINUMERT_SHELL_SELFTEST")
    return ClassicSelfTest(handler, out) if out else None
