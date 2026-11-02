"""Symulacja programu offline: ścieżka → materiał, kolizje, czas (sesja 052).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

`simulate(job)` liczy jeden program bez LinuxCNC w ruchu: ścieżka z `path.load_path`
(rs274, gdy dostępny, inaczej interpreter podzbioru), przygotówka z linii `;@STOCK`,
narzędzia jak `stat.tool_table` (nr, długość, średnica), reguły `SimEngine` (K-3xx).
Czas: G1/łuki z F, G0 z `rapid` — bez przyspieszeń (szacunek dolny; porównanie z Plant: 053).
Wynik to słownik JSON (do cache po SHA-256 zadania i do ekranu). Anulowanie: `cancelled()`
sprawdzane co odcinek. Proces potomny i kolejka: `worker.py`. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .engine import Sample, SimEngine
from .path import KIND_RAPID, MoveList, load_path

VERSION = 1                 # zmiana wyniku przy tym samym wejściu → nowy klucz cache


class Cancelled(Exception):
    """Zadanie anulowane przez ekran."""


@dataclass(frozen=True)
class OfflineJob:
    program: str                                        # tekst G-code
    stock: str | None = None                            # linia ;@STOCK (domyślnie z programu)
    tools: tuple[tuple[int, float, float], ...] = ()    # (T, długość, średnica) [mm]
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)  # układ detalu w G53 [mm]
    rapid: float = 5000.0                               # [mm/min] G0
    dt: float = 0.05                                    # [s] krok próbek SimEngine
    source: str = "auto"                                # auto | rs274 | subset

    def key(self) -> str:
        """SHA-256 wejścia (program, przygotówka, narzędzia, opcje, wersja modelu)."""
        data = json.dumps({"v": VERSION, **asdict(self)}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


def stock_line(job: OfflineJob) -> str | None:
    if job.stock:
        return job.stock
    for line in job.program.splitlines()[:200]:
        if line.strip().upper().startswith(";@STOCK"):
            return line.strip()
    return None


def movelist(job: OfflineJob) -> MoveList:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "program.ngc"
        path.write_text(job.program, encoding="utf-8")
        return load_path(path, job.source)


def simulate(job: OfflineJob, progress: Callable[[float], None] | None = None,
             cancelled: Callable[[], bool] | None = None) -> dict:
    from .placement import place_stock
    from .tooldata import cutters

    ml = movelist(job)
    engine = SimEngine()
    notes = list(ml.notes)
    line = stock_line(job)
    smap = None
    if line:
        from linumert.programs.stock import parse_stock_line

        stock = parse_stock_line(line)
        smap = place_stock(stock, job.origin)
        engine.set_stock(smap, stock.material)
    else:
        notes.append("Brak linii ;@STOCK — symulacja bez materiału (K-321).")
    engine.set_tools(cutters({}, list(job.tools)))
    volume0 = smap.volume() if smap is not None else 0.0

    events: list[dict] = []
    t = 0.0
    times = {"rapid": 0.0, "feed": 0.0}
    n = len(ml)
    ox, oy, oz = job.origin

    def nose(p, tool: int) -> tuple[float, float, float]:
        gauge = engine.tools[tool].gauge if tool in engine.tools else 0.0
        return (p[0] + ox, p[1] + oy, p[2] + oz + gauge)

    # Pozycja przed programem jest nieznana (rs274: odcinek zerowy, podzbiór: 0,0,0), więc
    # pierwszy ruch liczy się tylko do czasu; materiał i kolizje od jego końca.
    if n:
        engine.step(Sample(0.0, nose(ml.end[0], int(ml.tool[0])), int(ml.tool[0]),
                           float(ml.spindle[0]), "rapid", int(ml.line[0])))
    for i in range(n):
        if cancelled is not None and cancelled():
            raise Cancelled(f"anulowano po {i} z {n} odcinków")
        rapid = int(ml.kind[i]) == KIND_RAPID
        feed = job.rapid if rapid else float(ml.feed[i])
        a, b = ml.start[i].astype(float), ml.end[i].astype(float)
        dist = math.dist(a, b)
        seconds = dist / feed * 60.0 if feed > 0 else 0.0
        times["rapid" if rapid else "feed"] += seconds
        tool = int(ml.tool[i])
        if i == 0:
            t += seconds
            continue
        steps = max(1, math.ceil(seconds / job.dt))
        for k in range(1, steps + 1):
            sample = Sample(t + seconds * k / steps, nose(a + (b - a) * (k / steps), tool),
                            tool, float(ml.spindle[i]), "rapid" if rapid else "feed",
                            int(ml.line[i]))
            events += [e.to_dict() for e in engine.step(sample)]
        t += seconds
        if progress is not None and (i % 200 == 0 or i == n - 1):
            progress((i + 1) / n)
    lo, hi = ml.bounds()
    return {
        "version": VERSION, "key": job.key(), "source": ml.source, "segments": n,
        "lines": len(ml.lines()), "length_mm": round(ml.length(), 3),
        "time_s": round(t, 3), "time_rapid_s": round(times["rapid"], 3),
        "time_feed_s": round(times["feed"], 3),
        "bounds": [[round(float(v), 3) for v in lo], [round(float(v), 3) for v in hi]],
        "stock": line, "removed_mm3": round(volume0 - smap.volume(), 1) if smap else 0.0,
        "events": events, "notes": notes,
    }
