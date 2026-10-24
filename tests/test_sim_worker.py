# SPDX-License-Identifier: GPL-2.0-or-later
"""Symulacja offline i worker: reguły K-3xx, nice 10, anulowanie, cache SHA-256, most Qt (052).

Model-Author: Claude · 2026-10-24. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest
from linumert_sim.offline import Cancelled, OfflineJob, simulate
from linumert_sim.worker import SimWorker

ROOT = Path(__file__).resolve().parents[1]
STOCK = ';@STOCK BOX X120 Y80 Z30 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 TOP=1 MAT="aluminium"'
PROGRAM = f"""{STOCK}
G21 G90
T1 M6
S12000 M3
G0 X10 Y10 Z5
G1 Z-1 F200
G1 X30 F600
G1 Y30
G0 Z5
M5
G1 Z-2.5 F200
G0 Z5
G0 X50 Y50
G0 Z-2
M2
"""
TOOLS = ((1, 40.0, 6.0),)


def _long_program(n: int = 4000) -> str:
    rows = [STOCK, "G21 G90", "T1 M6", "S10000 M3", "G0 X5 Y5 Z2", "G1 Z-0.5 F100"]
    rows += [f"G1 X{5 + (i % 2) * 100} Y{5 + i * 0.01:.3f} F300" for i in range(n)]
    return "\n".join(rows + ["M2"]) + "\n"


def test_simulate_rules_time_and_material():
    r = simulate(OfflineJob(program=PROGRAM, tools=TOOLS))
    assert [(e["code"], e["line"]) for e in r["events"]] == [("K-301", 11), ("K-302", 14)]
    assert r["removed_mm3"] > 500
    # Czas: posuwy z F, G0 z `rapid`; pierwszy ruch tylko do czasu.
    assert r["time_feed_s"] == pytest.approx((6 / 200 + 20 / 600 + 20 / 600 + 7.5 / 200) * 60,
                                             rel=1e-3)
    assert r["time_s"] == pytest.approx(r["time_feed_s"] + r["time_rapid_s"])
    assert r["key"] == OfflineJob(program=PROGRAM, tools=TOOLS).key()
    json.dumps(r)                                   # wynik serializowalny (cache, ekran)


def test_simulate_without_stock_notes_and_key_changes():
    r = simulate(OfflineJob(program=PROGRAM.replace(STOCK, ""), tools=TOOLS))
    assert r["removed_mm3"] == 0 and any(";@STOCK" in n for n in r["notes"])
    a = OfflineJob(program=PROGRAM, tools=TOOLS)
    assert a.key() == OfflineJob(program=PROGRAM, tools=TOOLS).key()
    assert a.key() != OfflineJob(program=PROGRAM, tools=((1, 41.0, 6.0),)).key()
    assert a.key() != OfflineJob(program=PROGRAM + "\n", tools=TOOLS).key()


def test_simulate_cancel_and_progress():
    calls: list[float] = []
    with pytest.raises(Cancelled):
        simulate(OfflineJob(program=_long_program(), tools=TOOLS), calls.append,
                 lambda: len(calls) >= 1)
    assert calls and calls[-1] < 1.0


@pytest.fixture(scope="module")
def worker(tmp_path_factory):
    w = SimWorker(tmp_path_factory.mktemp("cache"))
    yield w
    w.close()


def _ready(w: SimWorker) -> dict:
    for msg in w.messages(timeout=30):
        if msg["ev"] == "ready":
            return msg
    raise AssertionError("worker nie zgłosił gotowości")


def test_worker_runs_niced_child_and_caches(worker):
    ready = _ready(worker)
    assert ready["pid"] == worker.proc.pid != os.getpid()
    assert os.getpriority(os.PRIO_PROCESS, worker.proc.pid) >= 10
    job = OfflineJob(program=PROGRAM, tools=TOOLS)
    seen: list[dict] = []
    first = worker.wait(worker.submit(job), 60, seen.append)
    assert first["ev"] == "done" and not first["cached"]
    assert any(m["ev"] == "progress" for m in seen)
    assert (worker.cache_dir / f"{job.key()}.json").is_file()
    t0 = time.monotonic()
    second = worker.wait(worker.submit(job), 5)
    assert second["cached"] and second["result"] == first["result"]
    assert time.monotonic() - t0 < 1.0
    # Nowy proces (np. po restarcie ekranu) czyta wynik z pliku.
    with SimWorker(worker.cache_dir) as other:
        hit = other.wait(other.submit(job), 5)
        assert hit["cached"] and hit["result"]["key"] == job.key()


def test_worker_cancel_running_and_queued(worker):
    long_job = OfflineJob(program=_long_program(20000), tools=TOOLS)
    running = worker.submit(long_job)
    queued = worker.submit(OfflineJob(program=_long_program(20001), tools=TOOLS))
    after = worker.submit(OfflineJob(program="G0 X1 Y1 Z1\nG1 X2 F100\n"))
    for msg in worker.messages(timeout=30):
        if msg.get("id") == running and msg["ev"] == "progress":
            break
    worker.cancel(queued)
    worker.cancel(running)
    assert worker.wait(running, 60)["ev"] == "cancelled"
    assert worker.wait(queued, 60)["ev"] == "cancelled"
    assert worker.wait(after, 60)["ev"] == "done"           # worker działa dalej
    assert not (worker.cache_dir / f"{long_job.key()}.json").exists()


def test_worker_reports_program_error(worker):
    msg = worker.wait(worker.submit(OfflineJob(program="G0 X0 Y0\nG2 X10 Y0 R2 F100\n")), 60)
    assert msg["ev"] == "error" and "promień" in msg["text"]


def test_qt_bridge_emits_signals_in_gui_thread(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt5")
    from PyQt5 import QtCore

    sys.path.insert(0, str(ROOT / "screens" / "linumert"))
    from linumert_sim_worker import SimWorkerBridge

    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    bridge = SimWorkerBridge(tmp_path)
    got: dict = {}
    gui = QtCore.QThread.currentThread()
    bridge.progress.connect(lambda i, f: got.setdefault("progress", f))
    bridge.finished.connect(
        lambda i, r, c: got.update(done=r, thread=QtCore.QThread.currentThread() is gui))
    try:
        bridge.submit(OfflineJob(program=PROGRAM, tools=TOOLS))
        end = time.monotonic() + 60
        while "done" not in got and time.monotonic() < end:
            app.processEvents(QtCore.QEventLoop.AllEvents, 50)
            time.sleep(0.01)
    finally:
        bridge.close()
    assert got["done"]["events"] and got["thread"] and "progress" in got
