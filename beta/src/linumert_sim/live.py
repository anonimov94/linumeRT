"""Proces symulacji na żywo przy LinuxCNC (osobny proces, nice 10; CLAUDE.md §5).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-19 (symulacja HMI).

    python -m linumert_sim.live --ini <plik.ini> [--machine machine.yaml] [--rate 100]

Co 1/rate s czyta `linuxcnc.stat` (pozycja nosa w G53, narzędzie, obroty, rodzaj ruchu, linia),
prowadzi materiał przygotówki i reguły `SimEngine`. Raportuje kolizje i przeciążenia.
Nie tworzy kanału komend LinuxCNC i nie uczestniczy w zezwoleniu na ruch (2026-10-20).

Protokół z ekranem: polecenia JSON na stdin (po jednym w linii), zdarzenia JSON na stdout.
Mapa wysokości przygotówki: plik `float32` (np.memmap), ścieżka w zdarzeniu `stock`.
Polecenia: {"cmd": "stock", "line": ";@STOCK ..."} | {"cmd": "stock_reset"} |
{"cmd": "machine", "path": ...} | {"cmd": "tools"} | {"cmd": "estop", "on": bool} |
{"cmd": "export_stl", "path": ...} | {"cmd": "export_report", "path": ...} | {"cmd": "quit"}.
Zdarzenia: ready, stock, machine, tools, pos (≤ 30 Hz), map (zmiana materiału, ≤ 10 Hz),
event (K-3xx), stl, report, error. Raport (`report.py`) obejmuje przebieg od wczytania
programu albo odnowienia materiału.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import queue
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

from linumert.tools.tbl import INCH

from .engine import Sample, SimEngine
from .machine import Machine, load_machine
from .placement import OFFSET_INDEX, find_stock_line, place_stock, read_var_offsets
from .report import SimLog, write_report
from .tooldata import cutters, ini_value, open_db, read_ini, table_units

POS_PERIOD = 1 / 30
MAP_PERIOD = 0.1


LOG = os.environ.get("LINUMERT_SIM_LOG")  # dziennik zdarzeń (JSON w liniach), np. do testów


def emit(**msg) -> None:
    text = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    if LOG and msg.get("ev") != "pos":
        try:
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except OSError:
            pass


def _stdin_reader(q: queue.Queue) -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            q.put(json.loads(line))
        except json.JSONDecodeError:
            emit(ev="error", text=f"niepoprawne polecenie: {line[:80]}")
    q.put({"cmd": "quit"})


class Live:
    def __init__(self, ini_path: str, machine_path: str | None, linuxcnc_mod):
        self.lc = linuxcnc_mod
        self.ini_path = Path(ini_path).resolve()
        self.ini = read_ini(self.ini_path)
        self.to_mm = INCH if table_units(self.ini_path) == "inch" else 1.0
        self.stat = self.lc.stat()
        self.engine = SimEngine()
        self.log = SimLog()
        self.map_file: Path | None = None
        self.map: np.ndarray | None = None
        self.map_version = -1
        self.file = None
        self.stock_line: str | None = None
        self.table_key = None
        self.db = None
        self.tbl = None
        self._resume_trace = []
        self._resume_key = None
        self._resume_time = None
        machine_path = machine_path or ini_value(self.ini, "LINUMERT", "MACHINE_YAML")
        if machine_path:
            self.load_machine(str(self._rel(machine_path)))

    def _rel(self, value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else self.ini_path.parent / p

    def _xyz_mm(self, values):
        return tuple(float(value) * self.to_mm for value in values[:3])

    # ---- polecenia ------------------------------------------------------------------------
    def load_machine(self, path: str) -> None:
        try:
            m = load_machine(path)
        except ValueError as exc:
            emit(ev="error", text=f"model maszyny: {exc}")
            return
        self.engine.set_machine(m)
        emit(ev="machine", name=m.name, path=m.path,
             bodies=[{"name": b.name, "shape": b.shape, "attached": b.attached,
                      "size": b.size, "position": b.position} for b in m.bodies],
             axis_force=m.axis_force, travel=m.travel)

    def set_stock(self, line: str | None) -> None:
        if not line:
            self.engine.set_stock(None)
            self.stock_line = None
            emit(ev="event", code="K-321", kind="warning", line=0, tool=0, pos=[0, 0, 0],
                 pair=[], stop=False, text=self._k321())
            emit(ev="stock", defined=False)
            return
        try:
            from linumert.programs.stock import StockError, parse_stock_line
        except ImportError as exc:  # pydantic 2 niedostępny w tym interpreterze
            emit(ev="error", text=f"brak modułu przygotówki: {exc}")
            return
        try:
            stock = parse_stock_line(line)
        except StockError as exc:
            emit(ev="error", text=f"przygotówka: {exc}")
            return
        try:
            self.stat.poll()
        except self.lc.error as exc:
            emit(ev="error", text=f"położenie przygotówki: brak statusu LinuxCNC: {exc}")
            return
        if getattr(self.stat, "g5x_index", None) == OFFSET_INDEX[stock.offset]:
            origin = tuple(self.stat.g5x_offset[:3])
        else:
            var = ini_value(self.ini, "RS274NGC", "PARAMETER_FILE", "linuxcnc.var")
            origin = read_var_offsets(self._rel(var)).get(stock.offset)
            if origin is None:
                emit(ev="error", text=f"położenie przygotówki: brak danych {stock.offset}; "
                     "wybierz ten układ w LinuxCNC albo udostępnij zapisane parametry")
                return
        origin = self._xyz_mm(origin)
        smap = place_stock(stock, origin)
        self.engine.set_stock(smap, stock.material)
        self.stock_line = line
        self._open_map(smap)
        emit(ev="stock", defined=True, line=line, shape=smap.shape, nx=smap.nx, ny=smap.ny,
             cell=smap.cell, x0=smap.x0, y0=smap.y0, x1=smap.x1, y1=smap.y1,
             z0=smap.z_bottom, z1=smap.z_top, origin=list(origin), material=stock.material,
             file=str(self.map_file))

    def _k321(self) -> str:
        try:
            from linumert.alarms.catalog import load_catalog

            return load_catalog().format("K-321", "pl")
        except Exception:  # noqa: BLE001
            return "K-321 brak przygotówki"

    def _open_map(self, smap) -> None:
        base = Path("/dev/shm") if Path("/dev/shm").is_dir() else Path(tempfile.gettempdir())
        if self.map_file is None:
            self.map_file = base / f"linumert_zmap_{os.getpid()}.f32"
        self.map = np.memmap(self.map_file, dtype=np.float32, mode="w+",
                             shape=(smap.ny, smap.nx))
        self.map[:] = smap.display()
        self.map.flush()
        self.map_version = smap.version

    def reload_tools(self, force: bool = False) -> None:
        self.stat.poll()
        table = [(t.id, float(t.zoffset) * self.to_mm, float(t.diameter) * self.to_mm)
                 for t in self.stat.tool_table
                 if t.id > 0]
        key = tuple(table)
        if key == self.table_key and not force:
            return
        self.table_key = key
        db_tools = {}
        try:
            if self.db is None:
                self.db, self.tbl = open_db(self.ini_path)
            db_tools = {t.number: t for t in self.db.tools()}
        except Exception as exc:  # noqa: BLE001 - symulacja działa dalej na walcach z tool.tbl
            emit(ev="error", text=f"baza narzędzi: {exc}")
        self.engine.set_tools(cutters(db_tools, table))
        emit(ev="tools", tools={n: {"kind": c.kind, "d": round(c.diameter, 3), "gauge": c.gauge,
                                    "cut_top": c.cut_top, "stickout": c.stickout,
                                    "neck_r": c.neck_r, "holder_r": c.holder_r,
                                    "hand": c.hand, "max_rpm": c.max_rpm,
                                    "profile": self._profile(c)}
                                for n, c in self.engine.tools.items()})

    @staticmethod
    def _profile(c) -> list[list[float]]:
        """Obrys (r, z) do bryły w widoku: od wierzchołka do nosa wrzeciona."""
        rs = np.linspace(0, c.radius, 12)
        pts = [[float(r), float(z)] for r, z in zip(rs, c.lower(rs), strict=True)]
        pts.append([c.radius, c.cut_top])
        for _name, r, z0, z1 in c.parts():
            pts += [[r, z0], [r, z1]]
        return pts

    # ---- pętla ----------------------------------------------------------------------------
    def sample(self, now: float) -> Sample:
        s = self.stat
        nose = self._xyz_mm(s.actual_position)
        sp = s.spindle[0] if s.spindle else {}
        rpm = 0.0
        if sp and sp.get("enabled") and sp.get("direction"):
            rpm = abs(float(sp.get("speed", 0.0))) * (1 if sp.get("direction") > 0 else -1)
        motion = {1: "rapid", 2: "feed", 3: "feed", 5: "feed"}.get(int(s.motion_type), "feed")
        line = int(s.motion_line or s.current_line or 0)
        return Sample(now, nose, int(s.tool_in_spindle), rpm, motion, line)

    def run(self, rate: float, commands: queue.Queue) -> None:
        period = 1 / rate
        last_pos = last_map = 0.0
        active_codes = None
        self.reload_tools(force=True)
        emit(ev="ready", ini=str(self.ini_path), pid=os.getpid())
        while True:
            t0 = time.monotonic()
            try:
                while True:
                    c = commands.get_nowait()
                    if not self.command(c):
                        return
            except queue.Empty:
                pass
            try:
                self.stat.poll()
            except self.lc.error as exc:
                emit(ev="error", text=f"linuxcnc.stat: {exc}")
                time.sleep(1.0)
                continue
            if self.stat.file != self.file:
                self.file = self.stat.file
                self.log.reset(Path(self.file).name if self.file else "")
                if self.file:
                    line = find_stock_line(self.file)
                    if line:
                        self.set_stock(line)
                    elif self.stock_line is None:
                        self.set_stock(None)
            self.reload_tools()
            sample = self.sample(t0)
            events = self.engine.step(sample)
            self.record_resume_sample(sample)
            self.log.tick(t0, events)
            codes = sorted({key[0] for key in self.engine._active})
            if codes != active_codes:
                active_codes = codes
                emit(ev="alarms", active=codes)
            for e in events:
                # Pole stop jest wskazaniem modelu, nigdy komendą do maszyny.
                emit(ev="event", sim_time=t0 - self.log.t0, **e.to_dict())
            smap = self.engine.stock
            if smap is not None and self.map is not None and smap.version != self.map_version \
                    and t0 - last_map >= MAP_PERIOD:
                self.map[:] = smap.display()
                self.map_version = smap.version
                last_map = t0
                emit(ev="map", version=smap.version, volume=round(smap.volume(), 1))
            if t0 - last_pos >= POS_PERIOD:
                last_pos = t0
                cutter = self.engine.tools.get(sample.tool)
                gauge = cutter.gauge if cutter else 0.0
                ld = self.engine.load
                emit(ev="pos", nose=[round(v, 3) for v in sample.nose],
                     tip=[round(sample.nose[0], 3), round(sample.nose[1], 3),
                          round(sample.nose[2] - gauge, 3)],
                     tool=sample.tool, rpm=round(sample.rpm), motion=sample.motion,
                     line=sample.line,
                     load={"mrr": round(ld.mrr, 1), "power": round(ld.power),
                           "torque": round(ld.torque, 3), "torque_limit":
                           round(ld.torque_limit, 3), "force": round(ld.force),
                           "axis": {a: [round(f), round(lim)] for a, (f, lim)
                                    in ld.axis.items()}})
            time.sleep(max(period - (time.monotonic() - t0), 0.0))

    def command(self, c: dict) -> bool:
        name = c.get("cmd")
        if name == "quit":
            return False
        if name == "stock":
            self.set_stock(c.get("line"))
        elif name == "stock_reset":
            self.engine.reset_stock()
            self.log.reset(self.log.program)
        elif name == "machine":
            self.load_machine(str(c.get("path", "")))
        elif name == "tools":
            self.reload_tools(force=True)
        elif name in ("recovery", "estop"):
            # Starsze HMI wysyła te polecenia; nie przywracają sterowania safety.
            emit(ev="info", text="Symulacja jest diagnostyczna; nie steruje E-STOP ani STO")
        elif name == "export_stl":
            self.export_stl(str(c.get("path", "")))
        elif name == "export_report":
            self.export_report(str(c.get("path", "")), c.get("view_png"))
        elif name == "resume_preview":
            self.resume_preview()
        else:
            emit(ev="error", text=f"nieznane polecenie {name!r}")
        return True

    def resume_preview(self) -> None:
        from linumert.programs.resume import ResumeRefused, ResumeSettings

        from .resume import preview_reentry

        try:
            self.stat.poll()
            if self.stat.interp_state not in (self.lc.INTERP_IDLE, self.lc.INTERP_PAUSED):
                raise ResumeRefused("Najpierw wstrzymaj program.")
            blocked = {180, 190, 330, 331, 410, 420, 730, 760, *range(810, 900, 10)}
            if blocked.intersection(self.stat.gcodes):
                raise ResumeRefused("Płaszczyzna, korekcja lub cykl poza zakresem podglądu D38.")
            sample = self.sample(time.monotonic())
            cutter = self.engine.tools.get(sample.tool)
            if cutter is None:
                raise ResumeRefused("Brak zdefiniowanego narzędzia.")
            tip = (*sample.nose[:2], sample.nose[2] - cutter.gauge)
            path = list(self._resume_trace)
            if not path or math.dist(path[-1], tip) > 0.25:
                raise ResumeRefused("Brak aktualnego śladu cięcia w punkcie zatrzymania.")
            path.append(tip)
            settings = ResumeSettings(**{key: float(ini_value(
                self.ini, "LINUMERT", setting, str(default))) for key, setting, default in (
                    ("overlap", "RESUME_OVERLAP", 2), ("clearance", "RESUME_CLEARANCE", 1),
                    ("pitch", "RESUME_HELIX_PITCH", 1), ("feed", "RESUME_FEED", 200))})
            plan = preview_reentry(self.engine, path, sample.tool, settings)
        except (ResumeRefused, ValueError) as exc:
            emit(ev="resume_preview", ok=False, text=str(exc))
            return
        emit(ev="resume_preview", ok=True, points=plan.points, entry=plan.entry,
             overlap=plan.overlap, feed=settings.feed,
             text="Podgląd w układzie maszyny, sprawdzony na kopii materiału. "
                  "Nie odtwarza programu ani stanu modalnego; automatyczne wykonanie wyłączone.")

    def record_resume_sample(self, sample) -> None:
        cutter = self.engine.tools.get(sample.tool)
        key = (self.file, sample.tool, cutter.diameter, cutter.gauge) if cutter else None
        if key != self._resume_key or (self._resume_time is not None and
                                       sample.t - self._resume_time > 1):
            self._resume_trace.clear()
        self._resume_key, self._resume_time = key, sample.t
        if cutter is None or sample.motion != "feed":
            self._resume_trace.clear()
            return
        tip = (*sample.nose[:2], sample.nose[2] - cutter.gauge)
        if not self._resume_trace or math.dist(self._resume_trace[-1], tip) >= 0.05:
            self._resume_trace.append(tip)
            del self._resume_trace[:-5000]

    def export_stl(self, path: str) -> None:
        if self.engine.stock is None or not path:
            emit(ev="error", text="eksport STL: brak przygotówki albo ścieżki")
            return
        from .stl import write_stl

        try:
            n = write_stl(self.engine.stock, path)
        except OSError as exc:
            emit(ev="error", text=f"eksport STL: {exc}")
            return
        emit(ev="stl", path=path, triangles=n)

    def export_report(self, path: str, view_png=None) -> None:
        if not path:
            emit(ev="error", text="raport symulacji: brak ścieżki")
            return
        try:
            png = None
            if view_png is not None:
                if not isinstance(view_png, str) or len(view_png) > 12 * 1024 * 1024:
                    raise ValueError("Niepoprawny rozmiar zrzutu widoku.")
                png = base64.b64decode(view_png, validate=True)
                if not png.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Zrzut widoku nie jest obrazem PNG.")
            write_report(path, self.engine, self.log,
                         title=f"Raport symulacji {self.log.program}".strip(), view_png=png)
        except (OSError, ValueError) as exc:
            emit(ev="error", text=f"raport symulacji: {exc}")
            return
        emit(ev="report", path=path, events=len(self.log.events))

    def close(self) -> None:
        if self.map_file is not None:
            try:
                self.map_file.unlink()
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="linumeRT: symulacja materiału i kolizji na żywo")
    ap.add_argument("--ini", required=True)
    ap.add_argument("--machine")
    ap.add_argument("--rate", type=float, default=100.0)
    args = ap.parse_args(argv)
    try:
        os.nice(10)
    except OSError:
        pass
    try:
        import linuxcnc
    except ImportError:
        emit(ev="error", text="brak modułu linuxcnc (uruchom w środowisku LinuxCNC)")
        return 2
    try:
        live = Live(args.ini, args.machine, linuxcnc)
    except ValueError as exc:
        emit(ev="error", text=f"konfiguracja symulacji: {exc}")
        return 2
    commands: queue.Queue = queue.Queue()
    threading.Thread(target=_stdin_reader, args=(commands,), daemon=True).start()
    try:
        live.run(args.rate, commands)
    finally:
        live.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["Live", "Machine", "main"]

