"""Raport prototypu: statyczny HTML z wykresami SVG (sesja 024).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 024.

Jeden plik na scenariusz (`<nazwa>.html`) i spis `index.html` w katalogu raportów
(domyślnie `docs/raporty/prototypy/`). Bez JavaScriptu i bez zasobów zewnętrznych; kolory
z `docs/design/tokens.yaml`. Wykresy: pozycja zadana i rzeczywista, błąd nadążania,
prędkość i moment — na oś (pierwszy napęd osi), z telemetrii serwera Plant.
"""

from __future__ import annotations

import html
import time
from pathlib import Path

from .scenario import ScenarioResult

C = {"bg": "#0a0c0f", "panel": "#12171d", "line": "#26303a", "fg": "#e8eef4", "fg2": "#9aa7b4",
     "fg3": "#66727e", "teal": "#2dd4bf", "info": "#7dd3fc", "amber": "#fbbf24", "ok": "#4ade80",
     "okbg": "#11301d", "err": "#f87171", "errbg": "#341416"}
MAX_POINTS = 600

CSS = f"""
body{{margin:0;background:{C['bg']};color:{C['fg']};font:14px/1.45 "IBM Plex Sans",system-ui,
sans-serif}} main{{max-width:1100px;margin:0 auto;padding:24px 16px}}
h1{{font-size:22px;margin:0 0 4px}}
h2{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;
color:{C['fg2']};margin:24px 0 8px}} .sub{{color:{C['fg2']}}}
.card{{background:{C['panel']};border:1px solid {C['line']};border-radius:14px;padding:16px;
margin:12px 0}} table{{border-collapse:collapse;width:100%}}
td,th{{text-align:left;padding:6px 8px;border-top:1px solid {C['line']};vertical-align:top}}
th{{color:{C['fg3']};font-weight:600;font-size:12px}} .mono{{font-family:"JetBrains Mono",
ui-monospace,monospace;font-size:12px}} .pass{{color:{C['ok']};background:{C['okbg']}}}
.fail{{color:{C['err']};background:{C['errbg']}}} .badge{{display:inline-block;padding:2px 10px;
border-radius:8px;font-weight:600}} svg{{width:100%;height:auto;display:block}}
a{{color:{C['info']}}} pre{{white-space:pre-wrap;color:{C['fg2']}}}
"""


def _badge(ok: bool) -> str:
    return f'<span class="badge {"pass" if ok else "fail"}">{"PASS" if ok else "FAIL"}</span>'


def _downsample(t: list[float], ys: list[list[float]]) -> tuple[list[float], list[list[float]]]:
    step = max(1, len(t) // MAX_POINTS)
    return t[::step], [y[::step] for y in ys]


def svg_chart(t: list[float], series: list[tuple[str, str, list[float]]], unit: str,
              width: int = 1000, height: int = 160) -> str:
    """Wykres liniowy SVG: `series` = [(nazwa, kolor, wartości)] na wspólnej osi Y."""
    if len(t) < 2:
        return '<p class="sub">brak danych</p>'
    t, ys = _downsample(t, [s[2] for s in series])
    pad_l, pad_r, pad_t, pad_b = 64, 12, 22, 22
    lo = min(min(y) for y in ys)
    hi = max(max(y) for y in ys)
    if hi - lo < 1e-12:
        lo, hi = lo - 1, hi + 1
    span_t = t[-1] - t[0] or 1.0
    w, h = width - pad_l - pad_r, height - pad_t - pad_b

    def xy(tt: float, v: float) -> str:
        return f"{pad_l + (tt - t[0]) / span_t * w:.1f},{pad_t + (hi - v) / (hi - lo) * h:.1f}"

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg">',
             f'<rect x="{pad_l}" y="{pad_t}" width="{w}" height="{h}" fill="none" '
             f'stroke="{C["line"]}"/>']
    for frac in (0.0, 0.5, 1.0):
        v = hi - frac * (hi - lo)
        y = pad_t + frac * h
        parts.append(f'<text x="{pad_l - 6}" y="{y + 4:.1f}" fill="{C["fg3"]}" font-size="11" '
                     f'text-anchor="end" font-family="monospace">{v:.4g}</text>')
    for frac in (0.0, 0.5, 1.0):
        tt = t[0] + frac * span_t
        parts.append(f'<text x="{pad_l + frac * w:.1f}" y="{height - 6}" fill="{C["fg3"]}" '
                     f'font-size="11" text-anchor="middle" font-family="monospace">'
                     f'{tt:.2f} s</text>')
    x = pad_l
    for (name, color, _vals), y in zip(series, ys, strict=True):
        pts = " ".join(xy(tt, v) for tt, v in zip(t, y, strict=True))
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.5" points="{pts}"/>')
        parts.append(f'<text x="{x}" y="14" fill="{color}" font-size="12" '
                     f'font-family="monospace">{html.escape(name)}</text>')
        x += 14 + 8 * len(name)
    parts.append(f'<text x="{width - pad_r}" y="14" fill="{C["fg3"]}" font-size="11" '
                 f'text-anchor="end" font-family="monospace">{html.escape(unit)}</text></svg>')
    return "".join(parts)


def render(res: ScenarioResult) -> str:
    scen = res.scenario
    esc = html.escape
    rows = "".join(f"<tr><td>{_badge(c.passed)}</td><td>{esc(c.name)}</td>"
                   f'<td class="mono">{esc(c.detail)}</td></tr>' for c in res.criteria)
    alarms = ", ".join(f"{k} ({v:.3f} s)" for k, v in sorted(res.alarms.items(),
                                                             key=lambda kv: kv[1])) or "brak"
    charts = []
    tele = res.telemetry or {}
    t = tele.get("t", [])
    drives = tele.get("drives", {})
    for letter in res.positions:
        name = (res.axis_drives.get(letter) or [None])[0]
        if name is None or name not in drives:
            continue
        d = drives[name]
        charts.append(f"<h2>Oś {esc(letter)} · napęd {esc(name)}</h2><div class='card'>"
                      + svg_chart(t, [("zadana", C["teal"], d["cmd"]),
                                      ("rzeczywista", C["info"], d["act"])], "mm | °")
                      + svg_chart(t, [("błąd nadążania", C["amber"], d["ferr"])], "mm | °",
                                  height=120)
                      + svg_chart(t, [("prędkość", C["teal"], d["vel"])], "mm/s | °/s",
                                  height=120)
                      + svg_chart(t, [("moment", C["amber"], d["torque"])], "‰", height=120)
                      + "</div>")
    vers = " · ".join(f"{k} {v}" for k, v in res.versions.items())
    stats = ", ".join(f"{k} {v}" for k, v in res.stats.items() if k != "digest")
    reqs = ", ".join(scen.requirements) or "—"
    log = esc("\n".join(res.log[-60:]))
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>linumeRT · scenariusz {esc(scen.name)}</title><style>{CSS}</style></head>
<body><main>
<p class="sub">linumeRT · raport prototypu Plant</p>
<h1>{esc(scen.name)} {_badge(res.passed)}</h1>
<p class="sub">{esc(scen.description)}</p>
<div class="card"><table>
<tr><th>Maszyna</th><td class="mono">{esc(scen.machine.name)}</td></tr>
<tr><th>Program</th><td class="mono">{esc(scen.program.name if scen.program else "—")}</td></tr>
<tr><th>Master</th><td>{esc(res.master)} · ziarno {scen.seed} · {scen.duration} s</td></tr>
<tr><th>Wymagania</th><td class="mono">{esc(reqs)}</td></tr>
<tr><th>Alarmy</th><td class="mono">{esc(alarms)}</td></tr>
<tr><th>Zdarzenia</th><td class="mono">{esc(", ".join(res.events) or "brak")}</td></tr>
<tr><th>Ramki</th><td class="mono">{esc(stats)}</td></tr>
<tr><th>Ślad SHA-256</th><td class="mono">{esc(str(res.stats.get("digest", "—")))}</td></tr>
<tr><th>Wersje</th><td class="mono">{esc(vers)}</td></tr>
</table></div>
<h2>Kryteria</h2><div class="card"><table><tr><th>Wynik</th><th>Kryterium</th><th>Wartość</th></tr>
{rows}</table></div>
{"".join(charts)}
<h2>Przebieg kroków</h2><div class="card"><pre class="mono">{log}</pre></div>
<p class="sub">Wygenerowano {time.strftime("%Y-%m-%d %H:%M")} · NIEZWERYFIKOWANE NA SPRZĘCIE</p>
</main></body></html>
"""


def write(results: list[ScenarioResult], out: Path) -> Path:
    """Zapisuje raporty i spis; zwraca ścieżkę `index.html`."""
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for res in results:
        fname = f"{res.scenario.name}{'' if res.master == 'mock' else '_' + res.master}.html"
        (out / fname).write_text(render(res), encoding="utf-8", newline="\n")
        crit = sum(c.passed for c in res.criteria)
        rows.append(f"<tr><td>{_badge(res.passed)}</td><td><a href='{fname}'>"
                    f"{html.escape(res.scenario.name)}</a></td><td>{html.escape(res.master)}</td>"
                    f"<td class='mono'>{html.escape(res.scenario.machine.name)}</td>"
                    f"<td>{crit}/{len(res.criteria)}</td></tr>")
    index = out / "index.html"
    index.write_text(f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>linumeRT · raporty prototypu</title><style>{CSS}</style></head><body><main>
<h1>Raporty prototypu Plant</h1>
<p class="sub">Scenariusze z <span class="mono">plant/scenarios/</span>,
<span class="mono">tools/run_scenario.py</span>.</p>
<div class="card"><table><tr><th>Wynik</th><th>Scenariusz</th><th>Master</th><th>Maszyna</th>
<th>Kryteria</th></tr>{"".join(rows)}</table></div></main></body></html>
""", encoding="utf-8", newline="\n")
    return index
