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


class HandlerClass(_upstream.HandlerClass):
    """Ekran linumeRT: QtDragon w nakładce linumeRT (LINUMERT_SHELL=0 wyłącza nakładkę)."""

    shell = None

    def initialized__(self):
        super().initialized__()
        self.w.setWindowTitle("linumeRT")
        if os.environ.get("LINUMERT_SHELL", "1") != "0":
            import linumert_shell

            self.shell = linumert_shell.install(self)
            if os.environ.get("LINUMERT_SHELL_SELFTEST"):
                import linumert_shell_selftest

                self._selftest = linumert_shell_selftest.maybe_start(self.shell)

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

    def add_status(self, message, alertLevel=_upstream.DEFAULT):
        super().add_status(message, alertLevel)
        if self.shell is not None and alertLevel != _upstream.DEFAULT:
            level = "warn" if alertLevel == _upstream.WARNING else "err"
            self.shell.show_alarm(level, message)


def get_handlers(halcomp, widgets, paths):
    return [HandlerClass(halcomp, widgets, paths)]
