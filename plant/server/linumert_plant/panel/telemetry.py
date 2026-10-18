"""Telemetria osi dla panelu: bufor pierścieniowy próbek (sesja 022).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 022.

Pętla ramek LRT-NET dopisuje próbkę co `period_s` czasu modelu (domyślnie 5 ms) — jedno
`deque.append` pod krótką własną blokadą, bez alokacji dużych struktur i bez I/O. Panel
(inny wątek) bierze kopię nowych próbek (`since`), więc nigdy nie trzyma blokady serwera
podczas serializacji ani wysyłki. Okno: `window_s` (domyślnie 10 s).
"""

from __future__ import annotations

import threading
from collections import deque

# Pola jednej osi w próbce (kolejność w krotce): pozycja zadana i rzeczywista [jedn. osi],
# błąd nadążania [jedn. osi], moment [promile znamionowego], prędkość [jedn./s], zgubione kroki.
FIELDS = ("cmd", "act", "ferr", "torque", "vel", "lost")
UNITS = {"cmd": "mm|°", "act": "mm|°", "ferr": "mm|°", "torque": "‰", "vel": "mm/s|°/s",
         "lost": "kroki"}


class Telemetry:
    """Bufor próbek `(t, wartości osi...)`; indeks próbki rośnie monotonicznie."""

    def __init__(self, drives: list[str], window_s: float = 10.0, period_s: float = 0.005):
        if not 0.0005 <= period_s <= 1.0:
            raise ValueError(f"okres próbkowania {period_s} s poza 0,0005–1")
        self.drives = list(drives)
        self.period_s = period_s
        self.window_s = window_s
        self._buf: deque[tuple] = deque(maxlen=int(window_s / period_s) + 1)
        self._lock = threading.Lock()
        self.count = 0  # liczba wszystkich dopisanych próbek
        self._next_t: float | None = None

    def due(self, t: float) -> bool:
        return self._next_t is None or t >= self._next_t - 1e-12

    def put(self, t: float, values: tuple) -> None:
        """`values` = płaska krotka len(drives) × len(FIELDS)."""
        with self._lock:
            self._buf.append((t, values))
            self.count += 1
        self._next_t = t + self.period_s

    def since(self, index: int | None = None) -> tuple[int, list[tuple]]:
        """Kopia próbek od indeksu `index` (None = całe okno). Zwraca (indeks pierwszej, próbki)."""
        with self._lock:
            data = list(self._buf)
            total = self.count
        first = total - len(data)
        if index is not None and index > first:
            data = data[min(index, total) - first:]
            first = min(index, total)
        return first, data

    def columns(self, index: int | None = None) -> dict:
        """Próbki kolumnami (JSON panelu): t i pola osi; `next` = indeks kolejnego odczytu."""
        first, data = self.since(index)
        n = len(FIELDS)
        out = {"first": first, "next": first + len(data), "t": [round(s[0], 6) for s in data],
               "drives": {}}
        for k, drive in enumerate(self.drives):
            out["drives"][drive] = {f: [s[1][k * n + i] for s in data]
                                    for i, f in enumerate(FIELDS)}
        return out
