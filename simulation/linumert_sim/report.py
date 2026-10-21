"""Raport symulacji: statyczny HTML z podsumowaniem, zdarzeniami i widokiem z góry (sesja 059).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-20

Jeden plik bez JavaScriptu i zasobów zewnętrznych; kolory z `docs/design/tokens.yaml`.
Zawartość: program, czas symulacji, długość ruchów szybkich i roboczych, objętość usuniętego
materiału, zdarzenia K-3xx (czas, linia, narzędzie, pozycja) oraz widok z góry — mapa wysokości
materiału (PNG w data: URI, zapis biblioteką standardową) i ślad narzędzia (SVG).
Opcjonalnie zrzut widoku 3D z ekranu (`view_png`). Raport nie jest dokumentem odbioru maszyny.
"""

from __future__ import annotations

import base64
import html
import math
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .engine import Event, SimEngine
from .zmap import StockMap

C = {"bg": "#0a0c0f", "panel": "#12171d", "line": "#26303a", "fg": "#e8eef4", "fg2": "#9aa7b4",
     "fg3": "#66727e", "teal": "#2dd4bf", "amber": "#fbbf24", "ok": "#4ade80", "okbg": "#11301d",
     "err": "#f87171", "errbg": "#341416"}
MAX_PATH_POINTS = 4000
MAX_EVENTS = 500

CSS = f"""
body{{margin:0;background:{C['bg']};color:{C['fg']};font:14px/1.45 "IBM Plex Sans",system-ui,
sans-serif}} main{{max-width:1100px;margin:0 auto;padding:24px 16px}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:{C['fg2']}}}
h2{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:{C['fg2']};
margin:24px 0 8px}} .card{{background:{C['panel']};border:1px solid {C['line']};
border-radius:14px;padding:16px;margin:12px 0}} table{{border-collapse:collapse;width:100%}}
td,th{{text-align:left;padding:6px 8px;border-top:1px solid {C['line']};vertical-align:top}}
th{{color:{C['fg3']};font-weight:600;font-size:12px}} .mono{{font-family:"JetBrains Mono",
ui-monospace,monospace;font-size:12px}} .pass{{color:{C['ok']};background:{C['okbg']}}}
.fail{{color:{C['err']};background:{C['errbg']}}} .badge{{display:inline-block;padding:2px 10px;
border-radius:8px;font-weight:600}} .top{{position:relative}} .top img,.top svg{{width:100%;
height:auto;display:block}} .top svg{{position:absolute;inset:0}} img.view{{max-width:100%}}
"""


@dataclass
class SimLog:
    """Przebieg jednej symulacji: program, czas i zdarzenia (z czasem względem startu)."""

    program: str = ""
    t0: float | None = None
    t1: float | None = None
    events: list[tuple[float, Event]] = field(default_factory=list)
    dropped_events: int = 0

    def reset(self, program: str = "") -> None:
        self.program, self.t0, self.t1 = program, None, None
        self.events.clear()
        self.dropped_events = 0

    def tick(self, t: float, events: list[Event] = ()) -> None:
        if self.t0 is None:
            self.t0 = t
        self.t1 = t
        for e in events:
            if len(self.events) < MAX_EVENTS:
                self.events.append((t - self.t0, e))
            else:
                self.dropped_events += 1

    @property
    def duration(self) -> float:
        return 0.0 if self.t0 is None else self.t1 - self.t0


def path_lengths(path) -> dict[str, float]:
    """Długość śladu wierzchołka narzędzia [mm] wg rodzaju ruchu (rapid, feed)."""
    out = {"rapid": 0.0, "feed": 0.0}
    for a, b in zip(path, path[1:], strict=False):
        if b[3] in out:
            out[b[3]] += math.dist(a[:3], b[:3])
    return out


def png_gray(values: np.ndarray) -> bytes:
    """Obraz PNG w odcieniach szarości (8 bit) z tablicy 0…255; wiersz 0 = góra obrazu."""
    img = np.ascontiguousarray(values, dtype=np.uint8)
    h, w = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def height_png(smap: StockMap) -> bytes:
    """Mapa wysokości: jasne = wysoko (nietknięte), ciemne = głębiej; brak materiału = czarne."""
    h = smap.h
    span = max(smap.z_top - smap.z_bottom, 1e-9)
    v = np.where(np.isfinite(h), 40 + 215 * (np.clip(h, smap.z_bottom, smap.z_top)
                                             - smap.z_bottom) / span, 0)
    return png_gray(np.flipud(v))  # oś Y maszyny w górę obrazu


def _top_view(smap: StockMap, path) -> str:
    w, h = smap.x1 - smap.x0, smap.y1 - smap.y0
    png = base64.b64encode(height_png(smap)).decode()
    step = max(1, len(path) // MAX_PATH_POINTS)
    pts = path[::step]
    lines = []
    for kind, color, dash in (("feed", C["teal"], ""), ("rapid", C["amber"], "4 3")):
        segs = [f"M{a[0] - smap.x0:.2f} {smap.y1 - a[1]:.2f}L{b[0] - smap.x0:.2f} "
                f"{smap.y1 - b[1]:.2f}" for a, b in zip(pts, pts[1:], strict=False)
                if b[3] == kind]
        if segs:
            lines.append(f'<path d="{"".join(segs)}" fill="none" stroke="{color}" '
                         f'stroke-width="{max(w, h) / 400:.3f}" stroke-dasharray="{dash}" '
                         'vector-effect="non-scaling-stroke"/>')
    return (f'<div class="top"><img alt="mapa wysokości materiału" '
            f'src="data:image/png;base64,{png}" style="image-rendering:pixelated">'
            f'<svg viewBox="0 0 {w:.3f} {h:.3f}" preserveAspectRatio="none">'
            f'{"".join(lines)}</svg></div>')


def _row(label: str, value: str) -> str:
    return f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"


def _timeline(log: SimLog) -> str:
    duration = max(log.duration, 0.001)
    points = []
    for i, (t, event) in enumerate(log.events):
        x = 20 + min(max(t / duration, 0), 1) * 960
        color = C["err"] if event.stop else C["amber"]
        title = html.escape(f"{t:.2f} s · {event.code} · linia {event.line} · T{event.tool}")
        points.append(f'<a href="#event-{i}"><circle cx="{x:.3f}" cy="30" r="5" '
                      f'fill="{color}"><title>{title}</title></circle></a>')
    return ('<h2>Oś czasu zdarzeń</h2><div class="card">'
            '<svg viewBox="0 0 1000 65" role="img" aria-label="Oś czasu zdarzeń">'
            f'<path d="M20 30H980" stroke="{C["fg3"]}"/>{"".join(points)}'
            f'<text x="20" y="60" fill="{C["fg2"]}">0 s</text>'
            f'<text x="980" y="60" text-anchor="end" fill="{C["fg2"]}">'
            f'{log.duration:.2f} s</text></svg>'
            '<p class="sub">Czas od początku tej symulacji; znacznik prowadzi do zdarzenia. '
            f'Pominięte zdarzenia po limicie {MAX_EVENTS}: {log.dropped_events}.</p></div>')


def initial_volume(smap: StockMap) -> float:
    """Objętość nietkniętej przygotówki [mm³] (jak `StockMap.reset`: walec = komórki w kole)."""
    cells = smap.nx * smap.ny
    if smap.shape == "CYL":
        cx, cy = (smap.x0 + smap.x1) / 2, (smap.y0 + smap.y1) / 2
        r = min(smap.x1 - smap.x0, smap.y1 - smap.y0) / 2
        xx, yy = np.meshgrid(smap.xs - cx, smap.ys - cy)
        cells = int(np.count_nonzero(xx * xx + yy * yy <= r * r))
    return cells * smap.cell * smap.cell * (smap.z_top - smap.z_bottom)


def render(engine: SimEngine, log: SimLog, title: str = "Raport symulacji",
           view_png: bytes | None = None) -> str:
    """HTML raportu symulacji (podsumowanie, zdarzenia, widok z góry, opcjonalny zrzut)."""
    smap = engine.stock
    # Jeden odczyt katalogu na raport, również przy 500 zdarzeniach. Osobny
    # proces musi wrócić do próbkowania zamiast parsować YAML dla każdego wiersza.
    try:
        from linumert.alarms.catalog import load_catalog

        catalog = load_catalog()
    except Exception:  # noqa: BLE001 - raport działa także bez katalogu rdzenia
        catalog = None

    def description(event):
        if catalog is not None:
            try:
                return catalog.format(event.code, "pl", **event.params)
            except (KeyError, ValueError, TypeError):
                pass
        return f"{event.code} {event.params}"

    lengths = path_lengths(engine.path)
    stops = [e for _t, e in log.events if e.stop]
    ok = not stops
    rows = [_row("Program", log.program or "—"),
            _row("Czas symulacji", f"{log.duration:.1f} s"),
            _row("Ruchy robocze (G1/G2/G3)", f"{lengths['feed']:.1f} mm"),
            _row("Ruchy szybkie (G0)", f"{lengths['rapid']:.1f} mm"),
            _row("Kolizje i przeciążenia (diagnostyka)", str(len(stops))),
            _row("Ostrzeżenia", str(len(log.events) - len(stops)))]
    if smap is not None:
        volume = smap.volume()
        rows.append(_row("Materiał", engine.material or "—"))
        rows.append(_row("Objętość materiału", f"{volume / 1000:.2f} cm³"))
        removed = max(initial_volume(smap) - volume, 0.0)
        rows.append(_row("Usunięto", f"{removed / 1000:.2f} cm³"))
    events = "".join(
        f'<tr id="event-{i}" data-time="{t:.6f}"><td class="mono">{t:.2f} s</td>'
        f'<td class="mono">{html.escape(e.code)}</td>'
        f"<td>{html.escape(description(e))}</td><td class=\"mono\">{e.line}</td>"
        f'<td class="mono">T{e.tool}</td><td class="mono">'
        f'{" ".join(f"{v:.2f}" for v in e.pos)}</td></tr>'
        for i, (t, e) in enumerate(log.events))
    badge = (f'<span class="badge {"pass" if ok else "fail"}">'
             f'{"bez kolizji i przeciążeń" if ok else "wykryto kolizje / przeciążenia"}</span>')
    parts = [f"<h1>{html.escape(title)}</h1>",
             '<p class="sub">linumeRT · symulacja materiału 2.5D i reguł kolizji; '
             f"nie zastępuje próby na maszynie. {badge}</p>",
             f'<div class="card"><table>{"".join(rows)}</table></div>',
             _timeline(log),
             "<h2>Zdarzenia</h2>",
             '<div class="card">' + (
                 "<table><tr><th>Czas</th><th>Kod</th><th>Opis</th><th>Linia</th>"
                 f"<th>Narzędzie</th><th>Pozycja G53 [mm]</th></tr>{events}</table>"
                 if events else '<p class="sub">brak zdarzeń</p>') + "</div>"]
    if smap is not None:
        parts += ["<h2>Widok z góry</h2>",
                  '<div class="card">' + _top_view(smap, engine.path)
                  + '<p class="sub">jaśniej = wyżej; linia ciągła = ruch roboczy, '
                    "przerywana = G0</p></div>"]
    if view_png:
        parts += ["<h2>Widok symulacji</h2>",
                  '<div class="card"><img class="view" alt="zrzut widoku" '
                  f'src="data:image/png;base64,{base64.b64encode(view_png).decode()}"></div>']
    return ('<!doctype html><html lang="pl"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>"
            + "".join(parts) + "</main></body></html>\n")


def write_report(path: str | Path, engine: SimEngine, log: SimLog, **kwargs) -> Path:
    """Zapis atomowy raportu (plik tymczasowy obok + rename)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(render(engine, log, **kwargs), encoding="utf-8")
    tmp.replace(path)
    return path
