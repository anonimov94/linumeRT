"""Raport symulacji HTML (sesja 059): podsumowanie, zdarzenia, widok z góry, PNG.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import re
import struct
import zlib

import numpy as np
import pytest

from linumert_sim.cutter import make_cutter
from linumert_sim.engine import Sample, SimEngine
from linumert_sim.report import (
    SimLog,
    height_png,
    initial_volume,
    path_lengths,
    png_gray,
    render,
    write_report,
)
from linumert_sim.zmap import StockMap


def _run(rapid_into_stock: bool):
    eng = SimEngine()
    eng.set_stock(StockMap("BOX", 0, 0, 60, 40, -20, 0, cell=0.5), "aluminium")
    eng.set_tools({1: make_cutter(1, 80, 8, "flat", {"d": 8, "l": 40, "flute_length": 20})})
    log = SimLog()
    log.reset("plyta.ngc")
    t = 100.0
    moves = [((-10, 20, 80), "rapid"), ((-10, 20, 78), "feed")]
    moves += [((-10 + i, 20, 78), "feed") for i in range(1, 70)]
    if rapid_into_stock:
        moves += [((30, 10, 85), "rapid"), ((30, 10, 77), "rapid")]
    for i, (nose, motion) in enumerate(moves):
        t += 0.05
        log.tick(t, eng.step(Sample(t, nose, 1, 8000, motion, line=10 + i)))
    return eng, log


def test_summary_and_clean_run():
    eng, log = _run(False)
    page = render(eng, log, title="Płyta")
    assert "<title>Płyta</title>" in page and "plyta.ngc" in page
    assert "bez kolizji i przeciążeń" in page and "brak zdarzeń" in page
    assert log.duration == pytest.approx(0.05 * 70, abs=1e-6)
    lengths = path_lengths(eng.path)
    assert lengths["feed"] == pytest.approx(69 + 2, abs=0.5) and lengths["rapid"] < 1
    removed = float(re.search(r"Usunięto</th><td>([0-9.]+) cm³", page).group(1))
    assert removed == pytest.approx((initial_volume(eng.stock) - eng.stock.volume()) / 1000,
                                    abs=0.01) and removed > 0.5
    assert "<script" not in page and "http" not in page  # bez zasobów zewnętrznych


def test_events_listed_with_time_and_line():
    eng, log = _run(True)
    page = render(eng, log)
    assert "wykryto kolizje / przeciążenia" in page and "K-302" in page
    t, e = next((t, e) for t, e in log.events if e.code == "K-302")
    assert t > 3 and e.line >= 79 and f'<td class="mono">{e.line}</td>' in page


def test_png_is_valid_grayscale():
    data = png_gray(np.array([[0, 128, 255], [10, 20, 30]]))
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w, h, depth, color = struct.unpack(">IIBB", data[16:26])
    assert (w, h, depth, color) == (3, 2, 8, 0)
    idat = data[data.index(b"IDAT") + 4:data.index(b"IEND") - 8]
    assert zlib.decompress(idat) == bytes([0, 0, 128, 255, 0, 10, 20, 30])


def test_height_map_and_cylinder_volume():
    s = StockMap("CYL", -20, -20, 20, 20, -10, 0, cell=0.25)
    assert initial_volume(s) == pytest.approx(s.volume(), rel=1e-9)
    assert initial_volume(s) == pytest.approx(np.pi * 20 ** 2 * 10, rel=0.01)
    png = height_png(s)
    assert png.startswith(b"\x89PNG") and struct.unpack(">II", png[16:24]) == (s.nx, s.ny)


def test_view_png_and_atomic_write(tmp_path):
    eng, log = _run(False)
    out = write_report(tmp_path / "r.html", eng, log, view_png=png_gray(np.zeros((2, 2))))
    page = out.read_text(encoding="utf-8")
    assert "Widok symulacji" in page and page.count("data:image/png;base64,") == 2
    assert not list(tmp_path.glob("*.tmp"))


def test_without_stock():
    page = render(SimEngine(), SimLog())
    assert "Widok z góry" not in page and "0.0 s" in page


def test_live_export_report_command(tmp_path, capsys):
    import json

    from linumert_sim.live import Live

    eng, log = _run(True)
    live = Live.__new__(Live)
    live.engine, live.log = eng, log
    live.command({"cmd": "export_report", "path": str(tmp_path / "r.html")})
    msg = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert msg["ev"] == "report" and msg["events"] == len(log.events)
    assert "K-302" in (tmp_path / "r.html").read_text(encoding="utf-8")
    live.command({"cmd": "export_report", "path": str(tmp_path / "brak" / "r.html")})
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["ev"] == "error"
    live.engine.stock = eng.stock
    live.command({"cmd": "stock_reset"})
    assert log.events == [] and log.program == "plyta.ngc"


def test_timeline_links_and_table_share_times_and_truncation_is_visible(monkeypatch):
    from unittest.mock import Mock

    import linumert.alarms.catalog as catalog
    from linumert_sim.engine import Event
    from linumert_sim.report import MAX_EVENTS

    engine, log = _run(False)
    loader = Mock(wraps=catalog.load_catalog)
    monkeypatch.setattr(catalog, "load_catalog", loader)
    log.tick(log.t0 + 10, [Event("K-305", "collision", 42, 1, (1, 2, 3))] * (MAX_EVENTS + 1))
    page = render(engine, log)
    loader.assert_called_once_with()
    assert log.dropped_events == 1 and "po limicie 500: 1" in page
    assert 'href="#event-0"' in page and 'id="event-0" data-time="10.000000"' in page
    assert "10.00 s · K-305 · linia 42 · T1" in page
    assert "ZATRZYMANIE" not in page and "Zdarzenia zatrzymujące" not in page
    log.reset()
    assert log.dropped_events == 0 and not log.events


@pytest.mark.parametrize("png", ["not base64!", "bm90IHBuZw==", 123])
def test_live_rejects_invalid_snapshot_without_overwriting_report(tmp_path, capsys, png):
    from linumert_sim.live import Live

    live = Live.__new__(Live)
    live.engine, live.log = _run(False)
    target = tmp_path / "existing.html"
    target.write_text("preserve")
    live.command({"cmd": "export_report", "path": str(target), "view_png": png})
    assert target.read_text() == "preserve" and '"ev": "error"' in capsys.readouterr().out
