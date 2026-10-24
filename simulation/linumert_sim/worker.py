"""Worker symulacji offline: proces potomny (nice 10), kolejka, anulowanie, cache SHA-256.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24 (sesja 052; CLAUDE.md §5: symulacja w osobnym procesie)

    w = SimWorker(cache_dir)            # start procesu potomnego
    job_id = w.submit(OfflineJob(program=text, tools=((1, 40.0, 6.0),)))
    for msg in w.messages(timeout=0.1): ...   # {"ev": "progress"|"done"|"cancelled"|"error", ...}
    w.cancel(job_id); w.close()

Zadania wykonują się po kolei w jednym procesie potomnym (`spawn`, `os.nice` ≥ 10). Wynik
`done` z tym samym kluczem (`OfflineJob.key()`) trafia do cache: w pamięci i — gdy podano
`cache_dir` — do pliku `<sha256>.json`; ponowne `submit` zwraca go bez liczenia (`cached`).
`start_listener(callback)` wywołuje `callback(msg)` z wątku pomocniczego (most do sygnałów Qt:
`screens/linumert/linumert_sim_worker.py`). Bez UI i bez LinuxCNC. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import multiprocessing as mp
import os
import queue
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

from .offline import Cancelled, OfflineJob, simulate

NICE = 10


def _worker_main(jobs, control, out, nice: int) -> None:
    """Pętla procesu potomnego: zadania z `jobs`, anulowania z `control`, komunikaty do `out`."""
    with contextlib.suppress(OSError):
        os.nice(max(0, nice - os.nice(0)))
    out.put({"ev": "ready", "pid": os.getpid(), "nice": os.nice(0)})
    cancelled: set[int] = set()

    def drain() -> None:
        while True:
            try:
                cancelled.add(control.get_nowait())
            except queue.Empty:
                return

    while True:
        item = jobs.get()
        if item is None:
            return
        job_id, job = item
        drain()
        if job_id in cancelled:
            out.put({"ev": "cancelled", "id": job_id, "text": "anulowano przed startem"})
            continue

        def is_cancelled(job_id=job_id) -> bool:
            drain()
            return job_id in cancelled

        def progress(fraction: float, job_id=job_id) -> None:
            out.put({"ev": "progress", "id": job_id, "fraction": round(fraction, 4)})

        try:
            result = simulate(job, progress, is_cancelled)
        except Cancelled as exc:
            out.put({"ev": "cancelled", "id": job_id, "text": str(exc)})
        except Exception as exc:  # noqa: BLE001 - błąd programu nie zatrzymuje workera
            out.put({"ev": "error", "id": job_id, "text": f"{type(exc).__name__}: {exc}"})
        else:
            out.put({"ev": "done", "id": job_id, "result": result})


class SimWorker:
    def __init__(self, cache_dir: Path | str | None = None, nice: int = NICE):
        ctx = mp.get_context("spawn")
        self._jobs = ctx.Queue()
        self._control = ctx.Queue()
        self._out = ctx.Queue()
        self._local: queue.Queue = queue.Queue()     # wyniki z cache (bez procesu)
        self._ids = itertools.count(1)
        self._keys: dict[int, str] = {}
        self._cache: dict[str, dict] = {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._listener: threading.Thread | None = None
        self._stop = threading.Event()
        self.proc = ctx.Process(target=_worker_main, name="linumert-sim",
                                args=(self._jobs, self._control, self._out, nice), daemon=True)
        self.proc.start()

    # ---- cache -----------------------------------------------------------------------------
    def cached(self, key: str) -> dict | None:
        if key in self._cache:
            return self._cache[key]
        if self.cache_dir:
            path = self.cache_dir / f"{key}.json"
            try:
                result = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            if result.get("key") == key:
                self._cache[key] = result
                return result
        return None

    def _store(self, result: dict) -> None:
        key = result.get("key")
        if not key:
            return
        self._cache[key] = result
        if self.cache_dir:
            tmp = self.cache_dir / f"{key}.json.tmp"
            tmp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.cache_dir / f"{key}.json")

    # ---- zadania ---------------------------------------------------------------------------
    def submit(self, job: OfflineJob) -> int:
        job_id = next(self._ids)
        key = job.key()
        self._keys[job_id] = key
        hit = self.cached(key)
        if hit is not None:
            self._local.put({"ev": "done", "id": job_id, "result": hit, "cached": True})
        else:
            self._jobs.put((job_id, job))
        return job_id

    def cancel(self, job_id: int) -> None:
        self._control.put(job_id)

    def _handle(self, msg: dict) -> dict:
        if msg.get("ev") == "done" and not msg.get("cached"):
            self._store(msg["result"])
            msg.setdefault("cached", False)
        return msg

    def messages(self, timeout: float = 0.0) -> Iterator[dict]:
        """Komunikaty gotowe teraz; pierwszy czeka do `timeout` s."""
        wait = timeout
        while True:
            try:
                yield self._handle(self._local.get_nowait())
                continue
            except queue.Empty:
                pass
            try:
                msg = self._out.get(timeout=wait) if wait > 0 else self._out.get_nowait()
            except queue.Empty:
                return
            wait = 0.0
            yield self._handle(msg)

    def wait(self, job_id: int, timeout: float = 60.0,
             on_message: Callable[[dict], None] | None = None) -> dict:
        """Czeka na koniec zadania (done/cancelled/error); do testów i narzędzi CLI."""
        import time

        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for msg in self.messages(timeout=0.1):
                if on_message is not None:
                    on_message(msg)
                if msg.get("id") == job_id and msg["ev"] in ("done", "cancelled", "error"):
                    return msg
        raise TimeoutError(f"zadanie {job_id}: brak wyniku po {timeout} s")

    # ---- wątek pomocniczy dla ekranu --------------------------------------------------------
    def start_listener(self, callback: Callable[[dict], None]) -> None:
        if self._listener is not None:
            raise RuntimeError("listener już działa")

        def loop() -> None:
            while not self._stop.is_set():
                for msg in self.messages(timeout=0.1):
                    callback(msg)

        self._listener = threading.Thread(target=loop, name="linumert-sim-listener",
                                          daemon=True)
        self._listener.start()

    def close(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._listener is not None:
            self._listener.join(timeout)
        if self.proc.is_alive():
            self._jobs.put(None)
            self.proc.join(timeout)
            if self.proc.is_alive():
                self.proc.terminate()
                self.proc.join(timeout)

    def __enter__(self) -> SimWorker:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
