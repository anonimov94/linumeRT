"""Zapis przebiegów Plant do pliku w osobnym wątku (CSV albo JSON Lines).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 016.

Pętla serwera tylko wkłada wiersz do ograniczonej kolejki (`put_nowait`); dysk obsługuje wątek
zapisu. Pełna kolejka nie blokuje pętli — wiersz jest pomijany i liczony w `dropped`.
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

FIELDS = ("statusword", "actual_pos", "following_error", "torque_pct", "error_code")


class TraceWriter:
    def __init__(self, path: Path | str, drives: list[str], fmt: str = "csv",
                 maxsize: int = 20_000):
        if fmt not in ("csv", "jsonl"):
            raise ValueError(f"nieznany format śladu {fmt!r} (csv, jsonl)")
        self.path = Path(path)
        self.drives = list(drives)
        self.fmt = fmt
        self.dropped = 0
        self.written = 0
        self.error: str | None = None
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", newline="\n")
        if fmt == "csv":
            cols = ["seq", "time_ns"] + [f"{d}.{f}" for d in self.drives for f in FIELDS]
            self._file.write(",".join(cols) + "\n")
        self._thread = threading.Thread(target=self._run, name="plant-trace", daemon=True)
        self._thread.start()

    def put(self, seq: int, time_ns: int, axes) -> None:
        row = (seq, time_ns, tuple(tuple(getattr(a, f) for f in FIELDS) for a in axes))
        try:
            self._queue.put_nowait(row)
        except queue.Full:
            self.dropped += 1

    def _line(self, row) -> str:
        seq, time_ns, axes = row
        if self.fmt == "csv":
            values = [seq, time_ns] + [v for axis in axes for v in axis]
            return ",".join(str(v) for v in values) + "\n"
        data = {"seq": seq, "time_ns": time_ns,
                "axes": {d: dict(zip(FIELDS, a, strict=True))
                         for d, a in zip(self.drives, axes, strict=True)}}
        return json.dumps(data, separators=(",", ":")) + "\n"

    def _run(self) -> None:
        while True:
            row = self._queue.get()
            if row is None:
                break
            try:
                self._file.write(self._line(row))
                self.written += 1
            except (OSError, ValueError) as exc:
                self.error = str(exc)  # zapis wyłączony, serwer działa dalej
        self._file.close()

    def close(self) -> None:
        """Opróżnia kolejkę i zamyka plik."""
        if self._thread.is_alive():
            self._queue.put(None)
            self._thread.join(timeout=10)
