# SPDX-License-Identifier: GPL-2.0-or-later
"""Kontrola programu po wczytaniu: limity osi i korekta długości narzędzia (w tle).

Model-Author: Claude. Diagnostyka: nic nie zatrzymuje sterownika; przed „Cykl start” ekran
pyta operatora, gdy program wyszedłby poza limity osi (LinuxCNC i tak zatrzymałby go w trakcie).
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt5 import QtCore


class Preflight(QtCore.QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, analyze=None, parent=None):
        super().__init__(parent)
        self._analyze = analyze
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._job = None
        self._key = None
        self.report = None
        self.text = "Limity osi: wczytaj program."
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self.poll)

    @staticmethod
    def machine_ini():
        ini = os.environ.get("INI_FILE_NAME", "")
        return ini if ini and Path(ini).is_file() else ""

    def _key_for(self, path, ini, var):
        key = []
        for required, item in ((True, path), (True, ini), (False, var)):
            if not item:
                continue
            try:
                info = os.stat(item)
            except OSError:
                if required:
                    return None
                key.append((str(item), None, None))  # brak pliku parametrów: dozwolony
                continue
            key.append((str(item), info.st_mtime_ns, info.st_size))
        return tuple(key)

    def request(self, path, ini=None):
        self.report = None
        self._key = None
        ini = ini or self.machine_ini()
        if not path or not ini:
            self.text = "Limity osi: brak programu albo INI maszyny."
            self.changed.emit()
            return
        analyze = self._analyze
        if analyze is None:
            from linumert.programs.limits import analyze_ngc

            analyze = analyze_ngc
        from linumert.programs.limits import parameter_file

        var = parameter_file(ini)
        key = self._key_for(path, ini, var)
        if key is None:
            self.text = "Limity osi: nie można odczytać programu."
            self.changed.emit()
            return
        self._job = (self._pool.submit(analyze, path, ini, var), key)
        self.text = "Limity osi: sprawdzanie…"
        self._timer.start()
        self.changed.emit()

    def poll(self):
        if self._job is None:
            self._timer.stop()
            return
        future, key = self._job
        if not future.done():
            return
        self._timer.stop()
        self._job = None
        try:
            self.report = future.result()
            self._key = key
        except Exception as exc:  # noqa: BLE001 - brak rs274 albo błąd programu
            self.report = None
            self.text = f"Limity osi niesprawdzone: {exc}"
            self.changed.emit()
            return
        self.text = self.describe(self.report)
        self.changed.emit()

    @staticmethod
    def describe(report):
        if report.violations:
            first = report.violations[0]
            return (f"UWAGA, program wyjdzie poza limity osi — {first.message()}. "
                    "Maszyna zatrzymałaby się w trakcie obróbki.")
        if report.cuts_without_tlo:
            return ("Limity osi: w porządku. Korekta długości narzędzia nieaktywna (G49): "
                    "G54 Z musi pochodzić z dotknięcia tym narzędziem.")
        return "Limity osi: w porządku."

    def violations(self, path, ini=None):
        """Przekroczenia dla bieżącego stanu pliku albo [] (brak wyniku nie blokuje startu)."""
        if self.report is None or not self.report.violations:
            return []
        ini = ini or self.machine_ini()
        from linumert.programs.limits import parameter_file

        current = self._key_for(path, ini, parameter_file(ini) if ini else None)
        return list(self.report.violations) if current == self._key else []
