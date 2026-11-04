"""Usługa symulacji: materiał, kolizje, czas — bez grafiki.

SPDX-License-Identifier: GPL-2.0-or-later

Silnik symulacji (``linumert_sim``) liczy zdejmowanie materiału, kolizje i czas. W projekcie
beta **nie ma renderera OpenGL** (``render_view.py`` usunięty), więc wyniki wracają jako dane:
objętości, granice, czasy, lista zdarzeń z parami kolizji i notatki modelu. GUI rysuje podgląd
u siebie (SVG/canvas/WebGL) albo pokazuje liczby — backend jest ten sam dla każdego frontu.
"""

from __future__ import annotations

from linumert_sim.offline import Cancelled, OfflineJob, simulate
from linumert_sim.path import InterpreterUnavailable

from ..errors import InvalidRequest
from ..schema import ProgramName, SimResultOut, SimRunRequest
from .paths import ProjectPaths
from .program import ProgramService

STOCK_PREFIX = ";@STOCK"


def normalize_stock(line: str) -> str | None:
    """Linia przygotówki z GUI → format silnika.

    Silnik czyta linię ``;@STOCK BOX X100 Y80 Z20 …`` (taką samą, jaką wkleja się
    w program). GUI wygodniej podać sam kształt, więc brakujący przedrostek dokładamy.
    """
    text = (line or "").strip()
    if not text:
        return None
    if text.upper().startswith(STOCK_PREFIX):
        return text
    return f"{STOCK_PREFIX} {text}"


class SimService:
    """Operacje domeny ``sim``."""

    domain = "sim"

    def __init__(self, paths: ProjectPaths, programs: ProgramService | None = None):
        self.paths = paths
        self.programs = programs

    def run(self, request: SimRunRequest) -> SimResultOut:
        text = self._program_text(request)
        job = OfflineJob(
            program=text,
            stock=normalize_stock(request.stock),
            tools=tuple((int(n), float(length), float(diameter))
                        for n, length, diameter in request.tools),
            origin=tuple(request.origin),
            rapid=request.rapid,
            dt=request.dt,
            source="auto",
        )
        try:
            result = simulate(job)
        except Cancelled as exc:
            raise InvalidRequest(f"symulacja przerwana: {exc}") from exc
        except (InterpreterUnavailable, ValueError, KeyError) as exc:
            raise InvalidRequest(f"symulacja nie powiodła się: {exc}") from exc

        events = [e for e in result.get("events", []) if isinstance(e, dict)]
        collisions = [list(e.get("pair", [])) for e in events if e.get("kind") == "collision"]
        bounds = result.get("bounds") or [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        low, high = (list(bounds) + [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])[:2]
        return SimResultOut(
            ok=True,
            volume_removed_mm3=float(result.get("removed_mm3", 0.0)),
            seconds=float(result.get("time_s", 0.0)),
            rapid_seconds=float(result.get("time_rapid_s", 0.0)),
            feed_seconds=float(result.get("time_feed_s", 0.0)),
            length_mm=float(result.get("length_mm", 0.0)),
            lines=int(result.get("lines", 0)),
            segments=int(result.get("segments", 0)),
            collisions=collisions,
            events=events,
            notes=[str(n) for n in result.get("notes", [])],
            bounds={"min_x": float(low[0]), "min_y": float(low[1]), "min_z": float(low[2]),
                    "max_x": float(high[0]), "max_y": float(high[1]), "max_z": float(high[2])},
            stock_line=str(result.get("stock") or ""),
            cache_key=str(result.get("key", "")),
            # Bez tego GUI nie wie, czy wynik jest pełny: interpreter podzbioru pomija
            # pętle o-word i G53, więc removed_mm3 bywa 0 mimo realnego skrawania.
            source=str(result.get("source") or ""),
            message=f"{result.get('lines', 0)} linii, {result.get('segments', 0)} odcinków",
        )

    def _program_text(self, request: SimRunRequest) -> str:
        if request.program:
            return request.program
        if request.name:
            if self.programs is None:
                raise InvalidRequest("usługa programów nie jest skonfigurowana")
            return self.programs.read(ProgramName(name=request.name)).text
        raise InvalidRequest("podaj program (tekst) albo name")


__all__ = ["SimService"]
