# SPDX-License-Identifier: GPL-2.0-or-later
"""Most worker symulacji offline → sygnały Qt dla ekranu (sesja 052).

Model-Author: Claude · 2026-10-24. `SimWorker` (simulation/linumert_sim/worker.py) liczy w procesie
potomnym z nice 10; jego wątek pomocniczy przekazuje komunikaty tutaj, a sygnały Qt trafiają do
wątku GUI kolejką zdarzeń (połączenie między wątkami). GUI nigdy nie czeka na symulację.
Bez komend LinuxCNC i pinów HAL. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from PyQt5 import QtCore


class SimWorkerBridge(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, float)     # (id zadania, ułamek 0–1)
    finished = QtCore.pyqtSignal(int, object, bool)  # (id, wynik dict, z cache)
    cancelled = QtCore.pyqtSignal(int, str)
    failed = QtCore.pyqtSignal(int, str)

    def __init__(self, cache_dir=None, parent=None, worker=None):
        super().__init__(parent)
        if worker is None:
            from linumert_sim.worker import SimWorker

            worker = SimWorker(cache_dir)
        self.worker = worker
        self.worker.start_listener(self._dispatch)

    def submit(self, job) -> int:
        return self.worker.submit(job)

    def cancel(self, job_id: int) -> None:
        self.worker.cancel(job_id)

    def close(self) -> None:
        self.worker.close()

    def _dispatch(self, msg: dict) -> None:
        """Wątek pomocniczy workera: tylko emisja sygnałów (bez dotykania widżetów)."""
        ev, job_id = msg.get("ev"), int(msg.get("id", 0))
        if ev == "progress":
            self.progress.emit(job_id, float(msg["fraction"]))
        elif ev == "done":
            self.finished.emit(job_id, msg["result"], bool(msg.get("cached")))
        elif ev == "cancelled":
            self.cancelled.emit(job_id, str(msg.get("text", "")))
        elif ev == "error":
            self.failed.emit(job_id, str(msg.get("text", "")))
