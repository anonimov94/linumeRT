"""Nagrywanie przebiegu telemetrii do CSV (sesja 022).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 022.

Zapis robi wątek panelu (`pump()` co ≤ 50 ms), nie pętla ramek: rejestrator czyta nowe próbki
z bufora `Telemetry`. Gdy zapis nie nadąży za oknem bufora, utracone próbki są liczone
(`dropped`) zamiast blokować serwer. Kolumny: `t` [s czasu modelu] i `<napęd>.<pole>`.
"""

from __future__ import annotations

import csv
import re
import time
from pathlib import Path

from .telemetry import FIELDS, Telemetry

NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}\.csv$")


class Recorder:
    def __init__(self, telemetry: Telemetry, store: Path):
        self.telemetry = telemetry
        self.store = store
        self.path: Path | None = None
        self._file = None
        self._writer = None
        self._next = 0
        self.rows = 0
        self.dropped = 0

    @property
    def active(self) -> bool:
        return self._file is not None

    def start(self, name: str | None = None) -> Path:
        if self.active:
            raise RuntimeError(f"nagrywanie już trwa ({self.path.name})")
        name = name or time.strftime("przebieg_%Y%m%d_%H%M%S.csv")
        if not name.endswith(".csv"):
            name += ".csv"
        if not NAME_RE.match(name):
            raise ValueError(f"nazwa pliku „{name}”: dozwolone litery, cyfry, _ . -")
        self.store.mkdir(parents=True, exist_ok=True)
        self.path = self.store / name
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["t"] + [f"{d}.{f}" for d in self.telemetry.drives for f in FIELDS])
        self._next = self.telemetry.count  # od bieżącej chwili
        self.rows = self.dropped = 0
        return self.path

    def pump(self) -> int:
        """Dopisuje nowe próbki; zwraca liczbę zapisanych wierszy."""
        if not self.active:
            return 0
        first, data = self.telemetry.since(self._next)
        if first > self._next:
            self.dropped += first - self._next
        for t, values in data:
            self._writer.writerow([f"{t:.6f}"] + [f"{v:.6g}" for v in values])
        self._next = first + len(data)
        self.rows += len(data)
        return len(data)

    def stop(self) -> Path | None:
        if not self.active:
            return None
        self.pump()
        self._file.close()
        self._file = self._writer = None
        return self.path

    def status(self) -> dict:
        return {"active": self.active, "file": self.path.name if self.path else None,
                "rows": self.rows, "dropped": self.dropped}

    def files(self) -> list[dict]:
        if not self.store.is_dir():
            return []
        return [{"name": p.name, "bytes": p.stat().st_size}
                for p in sorted(self.store.glob("*.csv")) if NAME_RE.match(p.name)]
