# SPDX-License-Identifier: GPL-2.0-or-later
"""Handler ekranu linumeRT (QtVCP): wzorzec patch na kopii handlera QtDragon.

Model-Author: Claude · sesja 005; nakładka HMI-PoC 2026-10-19.

`linumert_upstream_handler.py` to niezmieniona kopia `qtdragon_handler.py` z LinuxCNC 2.9.10
(GPL-2, UPSTREAM.md). Własne zmiany linumeRT żyją wyłącznie tutaj, w klasie pochodnej, i w
modułach `linumert_shell*.py` (nakładka: powłoka i widok „Maszyna”), więc aktualizacja upstream =
podmiana kopii i diff (procedura w UPSTREAM.md).
"""

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)  # linumert_shell, linumert_shell_model obok handlera


def _load_upstream():
    path = os.path.join(_HERE, "linumert_upstream_handler.py")
    spec = importlib.util.spec_from_file_location("linumert_upstream_handler", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_upstream = _load_upstream()

from linumert_keyboard import NumericKeyboardMixin


class HandlerClass(NumericKeyboardMixin, _upstream.HandlerClass):
    """Ekran linumeRT: QtDragon w nakładce linumeRT (LINUMERT_SHELL=0 wyłącza nakładkę)."""

    shell = None

    def initialized__(self):
        super().initialized__()
        self.w.setWindowTitle("linumeRT")
        # D35: piny grzyba E-STOP w HMI i sygnału życia (config/hal/linumert_hmi_estop.hal);
        # tworzone zawsze, bo łączy je postgui.
        qhal = _upstream.QHAL
        pins = {key: qhal.newpin(name, qhal.HAL_BIT, qhal.HAL_OUT) for key, name in
                (("ok", "hmi-estop-ok"), ("hb", "hmi-heartbeat"), ("wd", "hmi-wd-enable"),
                 ("ack", "hmi-ack"))}
        pins["retract_own"] = qhal.newpin("retract-own", qhal.HAL_BIT, qhal.HAL_OUT)
        pins["retract_target"] = qhal.newpin("retract-target", qhal.HAL_FLOAT, qhal.HAL_OUT)
        if os.environ.get("LINUMERT_SHELL", "1") == "0":
            self._classic_heartbeat(pins)
        else:
            import linumert_shell

            self.shell = linumert_shell.install(self, pins)
            # Reset E-STOP przez grzyb lub podwójny Reset powłoki: przycisk E-STOP/RESET QtDragon ukryty.
            self.w.action_estop.hide()
            if os.environ.get("LINUMERT_SHELL_SELFTEST"):
                import linumert_shell_selftest

                self._selftest = linumert_shell_selftest.maybe_start(self.shell)

    def _classic_heartbeat(self, pins):
        """Tryb klasyczny (bez nakładki): HMI żyje, grzyba HMI brak; E-STOP przyciskiem QtDragon.

        Każde żądanie resetu E-STOP z procesu ekranu (przycisk QtDragon, klawisz) najpierw potwierdza
        zdarzenie (impuls hmi-ack) i ponownie uzbraja watchdog; reset z innego procesu (np. komenda
        LinuxCNC) dalej nie zamknie łańcucha bez potwierdzenia (D35, przegląd Codexa P2).
        """
        from PyQt5 import QtCore

        pins["ok"].set(True)
        pins["wd"].set(False)
        pins["ack"].set(False)
        self._hb_state = False

        def beat():
            self._hb_state = not self._hb_state
            pins["hb"].set(self._hb_state)

        self._hb_timer = QtCore.QTimer()
        self._hb_timer.timeout.connect(beat)
        self._hb_timer.start(100)
        QtCore.QTimer.singleShot(400, lambda: pins["wd"].set(True))
        import linuxcnc

        # Podmiana w KLASIE Action: przycisk QtDragon (ActionButton) ma własną instancję Action.
        cls = type(_upstream.ACTION)
        original = cls.SET_ESTOP_STATE

        def set_estop_state(action, state):
            reset = state is False or (not isinstance(state, bool)
                                       and state == linuxcnc.STATE_ESTOP_RESET)
            if not reset:
                return original(action, state)
            pins["ack"].set(True)  # zbocze: potwierdzenie zdarzenia
            pins["wd"].set(False)
            QtCore.QTimer.singleShot(100, lambda: (pins["wd"].set(True), pins["ack"].set(False)))
            QtCore.QTimer.singleShot(300, lambda: original(action, False))
            return None

        cls.SET_ESTOP_STATE = set_estop_state
        self.classic_pins = pins
        if os.environ.get("LINUMERT_SHELL_SELFTEST"):
            import linumert_shell_selftest

            self._selftest = linumert_shell_selftest.maybe_start_classic(self)

    def hard_limit_tripped(self, obj, tripped, list_of_tripped):
        # QtDragon 2.9.10 zgłasza „Hard limits tripped” przy każdym sygnale, także tripped=False
        # wysyłanym na starcie; tu komunikat tylko przy faktycznym zadziałaniu, z listą osi.
        self.w.chk_override_limits.setEnabled(tripped)
        if not tripped:
            self.w.chk_override_limits.setChecked(False)
            return
        hits = [j for j, hit in enumerate(list_of_tripped or [])
                if isinstance(hit, (list, tuple)) and any(hit)]
        # Krańcówka wspólna z czujnikiem bazowania jest aktywna w trakcie bazowania (LinuxCNC
        # ją wtedy ignoruje): to nie alarm.
        joint = _upstream.STATUS.stat.joint
        hits = [j for j in hits if not joint[j]["homing"]]
        if list_of_tripped and not hits:
            return
        where = f" (stawy {', '.join(map(str, hits))})" if hits else ""
        self.add_status(f"Zadziałała krańcówka sprzętowa{where}", _upstream.CRITICAL)

    def kb_jog(self, state, joint, direction, fast=False, linear=True):
        if self.shell is None or not self.shell.s.specialist:
            return super().kb_jog(state, joint, direction, fast, linear)
        # W trybie wycofania także klawiatura (w tym Shift) ma wolny ruch ciągły.
        if state and not self.shell._allowed("jog"):
            return
        scale = 1 if _upstream.INFO.MACHINE_IS_METRIC or not linear else 25.4
        _upstream.ACTION.JOG(joint, direction if state else 0, 10 / scale, 0)

    def on_keycall_ESTOP(self, event, state, shift, cntrl):
        # F1: wciśnięcie grzyba HMI (zwolnienie tylko świadomie, przyciskiem grzyba)
        if state and self.shell is not None:
            self.shell.press_estop()
        elif state:
            super().on_keycall_ESTOP(event, state, shift, cntrl)

    def add_status(self, message, alertLevel=_upstream.DEFAULT):
        super().add_status(message, alertLevel)
        if self.shell is not None and alertLevel != _upstream.DEFAULT:
            level = "warn" if alertLevel == _upstream.WARNING else "err"
            self.shell.show_alarm(level, message)


def get_handlers(halcomp, widgets, paths):
    return [HandlerClass(halcomp, widgets, paths)]
