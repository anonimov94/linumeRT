"""Pomiar wydajności ścieżek obliczeniowych poza RT (raport docs/raporty/WYDAJNOSC_*.md).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-05

    PYTHONPATH=core:simulation:plant/server:webhmi/server python tools/bench_wydajnosc.py
    LINUMERT_NATIVE=0 ... python tools/bench_wydajnosc.py      # wymuszona ścieżka Pythona
    ... python tools/bench_wydajnosc.py --profile               # cProfile najwolniejszych zadań
    python tools/bench_wydajnosc.py --compare przed.json po.json  # tabela przed/po

Programy: `config/sim/nc_files/linumert_*.ngc` (rs274, gdy moduł `gcode` jest dostępny,
inaczej podzbiór) oraz programy z generatorów (kieszeń + planowanie + kreskowanie, płaskorzeźba
z syntetycznego STL). Czas = najlepszy z `--repeat` przebiegów (`time.perf_counter`).
Wynik: tabela Markdown na stdout i opcjonalnie JSON (`--json`). Bez LinuxCNC w ruchu.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import math
import os
import pstats
import struct
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for sub in ("core", "simulation", "plant/server", "webhmi/server"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

PROGRAMS = ("linumert_demo", "linumert_neon_demo", "linumert_rowek", "linumert_kwadrat",
            "linumert_wiercenie", "linumert_kolizja", "linumert_g2_odbior")
STOCK_GEN = ';@STOCK BOX X100 Y80 Z20 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 MAT="aluminium"'
STOCK_RELIEF = ';@STOCK BOX X40 Y40 Z8 ORIGIN=TOP_FRONT_LEFT OFFSET=G54 MAT="drewno"'
# Narzędzia jak stat.tool_table: (T, długość, średnica) [mm]
TOOLS_DEMO = ((1, 45.0, 6.0), (2, 50.0, 10.0), (3, 55.0, 6.0), (4, 60.0, 8.0),
              (5, 70.0, 50.0), (6, 48.0, 6.0), (7, 52.0, 4.0))


# --------------------------------------------------------------------------- dane

def _registry():
    import importlib
    import pkgutil

    import linumert.generators as package
    from linumert.generators.registry import DEFAULT_REGISTRY

    if not DEFAULT_REGISTRY.names():
        for info in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"linumert.generators.{info.name}")
            if info.name != "registry" and hasattr(module, "register"):
                module.register()
    return DEFAULT_REGISTRY


def _generate(name: str, params: dict) -> list[str]:
    gen = _registry().latest(name)
    values, issues = gen.normalize(params)
    issues += gen.check(values, 1) if not issues else []
    if issues:
        raise ValueError(f"{name}: {[i.message() for i in issues]}")
    return gen.generate(values)


def program_generated() -> str:
    """Kieszeń 60×40×6, planowanie 100×80 i kreskowanie krzyżowe frezem D6 (T1)."""
    lines = [STOCK_GEN, "G21 G90 G17 G40 G49 G80 G54 G94", "T1 M6", "G43 H1", "S12000 M3"]
    lines += _generate("face_mill", {"x0": 0, "y0": 0, "x1": 100, "y1": 80, "depth": 0.5,
                                     "step_down": 0.5, "tool_d": 6, "feed": 1200})
    lines += _generate("pocket_rect", {"cx": 50, "cy": 40, "width": 60, "height": 40,
                                       "depth": 6, "step_down": 2, "tool_d": 6, "z_top": -0.5,
                                       "feed": 800})
    lines += _generate("shape_engrave", {"shape": "rectangle", "width": 30, "height": 20,
                                         "cx": 50, "cy": 40, "strategy": "crosshatch",
                                         "spacing": 1.0, "z_top": -6.5, "depth": 0.3,
                                         "step_down": 0.3, "tool_d": 6})
    return "\n".join(lines + ["M5", "M2"]) + "\n"


def wave_mesh(n: int = 27, size: float = 40.0) -> np.ndarray:
    """Powierzchnia falista n×n kwadratów (2n² trójkątów), Z w [-5, -1] mm."""
    g = np.linspace(0.0, size, n + 1)
    xx, yy = np.meshgrid(g, g)
    zz = -3.0 + 1.2 * np.sin(xx / 6.0) * np.cos(yy / 7.0) + 0.6 * np.sin((xx + yy) / 4.0)
    p = np.stack([xx, yy, zz], axis=-1)
    a, b, c, d = p[:-1, :-1], p[:-1, 1:], p[1:, 1:], p[1:, :-1]
    tris = np.concatenate([np.stack([a, b, c], axis=2).reshape(-1, 3, 3),
                           np.stack([a, c, d], axis=2).reshape(-1, 3, 3)])
    return tris.astype(float)


def sphere_mesh(n: int = 160, radius: float = 25.0) -> np.ndarray:
    """Kula z siatki szerokość × długość (2·n·(n-1) trójkątów)."""
    th = np.linspace(0.0, math.pi, n + 1)
    ph = np.linspace(0.0, 2 * math.pi, n + 1)
    tt, pp = np.meshgrid(th, ph, indexing="ij")
    p = np.stack([radius * np.sin(tt) * np.cos(pp), radius * np.sin(tt) * np.sin(pp),
                  radius * np.cos(tt)], axis=-1)
    a, b, c, d = p[:-1, :-1], p[:-1, 1:], p[1:, 1:], p[1:, :-1]
    tris = np.concatenate([np.stack([a, b, c], axis=2).reshape(-1, 3, 3),
                           np.stack([a, c, d], axis=2).reshape(-1, 3, 3)])
    area = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    return tris[area > 1e-12]


def write_binary_stl(path: Path, tris: np.ndarray) -> None:
    rec = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["v"] = tris
    path.write_bytes(b" " * 80 + struct.pack("<I", len(tris)) + rec.tobytes())


def write_ascii_stl(path: Path, tris: np.ndarray) -> None:
    out = ["solid bench"]
    for t in tris:
        out += ["facet normal 0 0 0", "outer loop"]
        out += [f"vertex {x:.6f} {y:.6f} {z:.6f}" for x, y, z in t]
        out += ["endloop", "endfacet"]
    path.write_text("\n".join(out + ["endsolid bench"]) + "\n", encoding="ascii")


def relief_settings():
    from linumert.generators.relief import ReliefSettings

    return ReliefSettings(tool_diameter=3.0, sample_step=0.1, stepover=0.5, safe_z=10.0,
                          feed=1500.0, plunge=300.0)


def program_relief() -> str:
    from linumert.generators.relief import plan_relief
    from linumert.programs.stl_section import Mesh

    text = plan_relief(Mesh(wave_mesh()), relief_settings()).gcode()
    return STOCK_RELIEF + "\n" + text


# --------------------------------------------------------------------------- pomiar

def best(fn: Callable[[], object], repeat: int) -> tuple[float, object]:
    times, result = [], None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    return min(times), result


def native_state() -> str:
    try:
        from linumert import native
    except ImportError:
        return "Python (kod sprzed linumert.native)"
    return "natywna (C)" if native.available() else f"Python ({native.reason()})"


def gcode_available() -> bool:
    try:
        import gcode  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


def run(repeat: int, profile: bool) -> dict:
    from linumert_sim.offline import OfflineJob, simulate
    from linumert_sim.path import load_path, parse_subset

    rows: list[dict] = []
    profiles: dict[str, str] = {}

    def add(area: str, data: str, seconds: float, note: str = "") -> None:
        rows.append({"area": area, "data": data, "ms": round(seconds * 1000, 2), "note": note})
        print(f"{area:<34} {data:<28} {seconds * 1000:10.1f} ms  {note}", file=sys.stderr)

    def prof(key: str, fn: Callable[[], object]) -> None:
        if not profile:
            return
        pr = cProfile.Profile()
        pr.enable()
        fn()
        pr.disable()
        buf = io.StringIO()
        pstats.Stats(pr, stream=buf).sort_stats("tottime").print_stats(12)
        profiles[key] = buf.getvalue()

    source = "rs274" if gcode_available() else "subset"
    nc = ROOT / "config" / "sim" / "nc_files"
    texts = {name: (nc / f"{name}.ngc").read_text(encoding="utf-8") for name in PROGRAMS}
    t_gen, texts["gen_kieszen_planowanie"] = best(program_generated, 1)
    add("generator CAM (kieszeń+planowanie)", "100×80 mm", t_gen)
    t_rel, texts["gen_plaskorzezba"] = best(program_relief, 1)
    add("generator płaskorzeźby plan_relief", "1458 trójkątów, 401×81", t_rel)

    tools = {"gen_kieszen_planowanie": ((1, 45.0, 6.0),), "gen_plaskorzezba": ((1, 40.0, 3.0),)}
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in texts.items():
            path = Path(tmp) / f"{name}.ngc"
            path.write_text(text, encoding="utf-8")
            prefer = "subset" if name.startswith("gen_") else "auto"
            try:
                t, ml = best(lambda path=path, prefer=prefer: load_path(path, prefer), repeat)
            except Exception as error:  # noqa: BLE001 - program poza podzbiorem: pomijamy
                add("ścieżka load_path", name, math.nan, f"błąd: {error}")
                continue
            fallback = prefer == "auto" and ml.source == "subset" and gcode_available()
            add(f"ścieżka load_path ({ml.source})", name, t, f"{len(ml)} odcinków"
                + (" (podzbiór po awarii procesu rs274: T/M6 bez działającego LinuxCNC)"
                   if fallback else ""))
            if name.startswith("gen_"):
                t, _ = best(lambda text=text: parse_subset(text), repeat)
                add("ścieżka parse_subset", name, t)
            # symulacja ze źródłem, które zadziałało: bez kosztu nieudanej próby rs274
            job = OfflineJob(program=text, tools=tools.get(name, TOOLS_DEMO), source=ml.source)
            t, res = best(lambda job=job: simulate(job), repeat)
            add("symulacja offline simulate", name, t,
                f"{res['segments']} odc., usunięto {res['removed_mm3']} mm³, "
                f"{len(res['events'])} zdarzeń")
            rows[-1]["removed_mm3"] = res["removed_mm3"]
            rows[-1]["events"] = len(res["events"])
            if name in ("gen_plaskorzezba", "gen_kieszen_planowanie", "linumert_demo"):
                prof(f"simulate {name}", lambda job=job: simulate(job))

        # podgląd ekranu Qt: Toolpath z MoveList płaskorzeźby i lokalizacja linii (30 Hz)
        from linumert.programs.toolpath import Toolpath, make_move

        ml = parse_subset(texts["gen_plaskorzezba"])

        def build():
            return Toolpath([make_move(int(ln), bool(k == 0), float(f), (a, b)) for ln, k, f, a, b
                             in zip(ml.line, ml.kind, ml.feed, ml.start, ml.end, strict=True)])

        t, tp = best(build, repeat)
        add("podgląd Toolpath (make_move)", "gen_plaskorzezba", t, f"{len(tp)} ruchów")
        last = tp.moves[-1]
        t, _ = best(lambda: tp.locate(last.line, last.end), repeat)
        add("podgląd Toolpath.locate", "ostatnia linia", t)

        # STL: odczyt, przekrój, eksport materiału
        from linumert.programs.stl_section import Mesh, read_stl, section_xy

        sphere = sphere_mesh()
        bpath, apath = Path(tmp) / "kula.stl", Path(tmp) / "kula_ascii.stl"
        write_binary_stl(bpath, sphere)
        write_ascii_stl(apath, sphere_mesh(80))
        t, mesh = best(lambda: read_stl(bpath), repeat)
        add("STL read_stl (binarny)", f"{len(mesh.triangles)} trójkątów", t)
        t, amesh = best(lambda: read_stl(apath), repeat)
        add("STL read_stl (ASCII)", f"{len(amesh.triangles)} trójkątów", t)
        t, paths = best(lambda: section_xy(mesh, 0.3), repeat)
        add("STL section_xy", f"{len(mesh.triangles)} trójkątów", t,
            f"{sum(len(p) for p in paths)} punktów")
        prof("section_xy", lambda: section_xy(mesh, 0.3))

        from linumert.generators.relief import ball_tip_height, plan_relief

        wave = wave_mesh()
        t, _ = best(lambda: plan_relief(Mesh(wave), relief_settings()), 1)
        add("płaskorzeźba plan_relief", "1458 trójkątów, 32481 pkt", t)
        t, _ = best(lambda: [ball_tip_height(wave, 20.0 + 0.01 * i, 20.0, 1.6)
                             for i in range(200)], repeat)
        add("płaskorzeźba ball_tip_height ×200", "1458 trójkątów", t)
        prof("plan_relief", lambda: plan_relief(Mesh(wave), relief_settings()))

        from linumert.programs.stock import parse_stock_line
        from linumert_sim.placement import place_stock
        from linumert_sim.stl import write_stl


        smap = place_stock(parse_stock_line(STOCK_GEN), (0.0, 0.0, 0.0))
        t, n = best(lambda: write_stl(smap, Path(tmp) / "material.stl"), repeat)
        add("eksport materiału write_stl", f"{smap.nx}×{smap.ny} komórek", t, f"{n} trójkątów")

    # brama WebHMI 50 Hz (atrapa maszyny)
    from linumert_webhmi.backend import FakeBackend
    from linumert_webhmi.gateway import Gateway

    gw = Gateway(FakeBackend())
    t, _ = best(lambda: [gw.step() for _ in range(500)], repeat)
    add("brama WebHMI Gateway.step ×500", "FakeBackend", t, f"{t / 500 * 1e6:.0f} µs/obieg")

    # Plant: pełna ramka LRT-NET (kodowanie, rdzeń C, odpowiedź)
    try:
        from linumert_plant import core_binding
        from linumert_plant.build_machine import build_machine
        from linumert_plant.server import PlantConfig, PlantServer
        from test_master import Master

        core_binding.load_library()
        machine = core_binding.PlantMachine(build_machine(
            ROOT / "config" / "machines" / "mill_servo_table.yaml", seed=1))
        server = PlantServer(machine, PlantConfig(seed=1))
        master = Master(len(server.drives), transport=server.handle)
        t, _ = best(lambda: [master.exchange() for _ in range(2000)], repeat)
        add("Plant ramka LRT-NET ×2000", "mill_servo_table", t,
            f"{t / 2000 * 1e6:.0f} µs/ramka przy okresie 1000 µs")
    except Exception as error:  # noqa: BLE001 - rdzeń C niezbudowany: wiersz z adnotacją
        add("Plant ramka LRT-NET ×2000", "mill_servo_table", math.nan, f"pominięte: {error}")

    return {"date": time.strftime("%Y-%m-%d %H:%M"), "native": native_state(),
            "source": source, "python": sys.version.split()[0], "numpy": np.__version__,
            "cpu": os.cpu_count(), "rows": rows, "profiles": profiles}


def markdown(result: dict) -> str:
    out = [f"Pomiar {result['date']}, Python {result['python']}, numpy {result['numpy']}, "
           f"ścieżka symulacji: {result['native']}, źródło ścieżki plików: {result['source']}.",
           "", "| Obszar | Dane | Czas [ms] | Uwagi |", "|---|---|---:|---|"]
    for r in result["rows"]:
        ms = "—" if math.isnan(r["ms"]) else f"{r['ms']:.1f}"
        out.append(f"| {r['area']} | {r['data']} | {ms} | {r['note']} |")
    for key, text in result["profiles"].items():
        out += ["", f"cProfile `{key}` (tottime):", "", "```", text.strip(), "```"]
    return "\n".join(out) + "\n"


def compare(paths: list[Path]) -> str:
    """Tabela z kilku pomiarów `--json` (kolumny w kolejności plików, przyspieszenie: 1. / ost.)."""
    results = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    names = [p.stem.removeprefix("bench_") for p in paths]
    keys: list[tuple[str, str]] = []
    for result in results:
        for r in result["rows"]:
            key = (r["area"].split(" (")[0], r["data"])
            if key not in keys:
                keys.append(key)
    out = [" · ".join(f"{n}: {r['native']}, {r['date']}" for n, r in zip(names, results,
                                                                        strict=True)), "",
           "| Obszar | Dane | " + " | ".join(f"{n} [ms]" for n in names) + " | × |",
           "|---|---|" + "---:|" * (len(names) + 1)]
    for key in keys:
        cells = []
        for result in results:
            ms = next((r["ms"] for r in result["rows"]
                       if (r["area"].split(" (")[0], r["data"]) == key), math.nan)
            cells.append(ms)
        first, last = cells[0], cells[-1]
        ratio = f"{first / last:.1f}" if math.isfinite(first) and math.isfinite(last) \
            and last > 0 else "—"
        text = ["—" if not math.isfinite(c) else f"{c:.1f}" for c in cells]
        out.append(f"| {key[0]} | {key[1]} | " + " | ".join(text) + f" | {ratio} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--compare", type=Path, nargs="+",
                        help="pliki --json do zestawienia (bez nowego pomiaru)")
    args = parser.parse_args(argv)
    if args.compare:
        sys.stdout.write(compare(args.compare))
        return 0
    result = run(max(1, args.repeat), args.profile)
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stdout.write(markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
