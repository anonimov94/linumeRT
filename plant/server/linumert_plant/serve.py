"""Uruchomienie serwera Plant z wiersza poleceń (`python -m linumert_plant serve`).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 016.

Błędna konfiguracja (machine.yaml, plant.yaml, brak szablonu napędu, brak rdzenia C) kończy
się czytelnym komunikatem i kodem 1 — Plant nie startuje, więc napędy pozostają wyłączone
(docs/PLANT.md §8). Po starcie żaden błąd ramki ani modelu nie kończy procesu.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

from linumert.machine.schema import MachineConfigError

from .server import PlantConfig, PlantConfigError, PlantServer, load_plant_config


def add_parser(sub) -> None:
    serve = sub.add_parser("serve", help="serwer LRT-NET (UDP) wirtualnej obrabiarki")
    serve.add_argument("machine", type=Path, nargs="?", default=None,
                       help="machine.yaml (zamiast pola machine w plant.yaml)")
    serve.add_argument("--plant", type=Path, default=None, help="plant.yaml")
    mode = serve.add_mutually_exclusive_group()
    mode.add_argument("--lockstep", dest="mode", action="store_const", const="lockstep",
                      help="czas z ramek (testy, CI; deterministyczny)")
    mode.add_argument("--realtime", dest="mode", action="store_const", const="realtime",
                      help="zegar hosta (VM-B)")
    serve.add_argument("--listen", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.add_argument("--seed", type=int, default=None)
    serve.add_argument("--trace", type=Path, default=None, help="plik śladu (.csv albo .jsonl)")
    serve.add_argument("--frames", type=int, default=None, help="zakończ po N ramkach")
    serve.add_argument("--dir", type=Path, default=None, help="katalog biblioteki napędów")


def _config(args: argparse.Namespace) -> PlantConfig:
    cfg = load_plant_config(args.plant) if args.plant else PlantConfig()
    if args.machine is not None:
        cfg.machine = args.machine
    for name in ("mode", "listen", "port", "seed"):
        value = getattr(args, name)
        if value is not None:
            setattr(cfg, name, value)
    if args.trace is not None:
        cfg.trace_path = args.trace
        cfg.trace_format = "jsonl" if args.trace.suffix == ".jsonl" else "csv"
    if cfg.machine is None:
        raise PlantConfigError("brak machine.yaml (argument albo pole machine w plant.yaml)")
    cfg.check()
    return cfg


def build_server(cfg: PlantConfig, library_dir: Path | None = None) -> PlantServer:
    """machine.yaml → model C → serwer (z plikiem stanu enkoderów absolutnych i śladem)."""
    from .build_machine import build_machine
    from .core_binding import PlantMachine
    from .plant_state import apply_state, load_state
    from .trace import TraceWriter

    model = build_machine(cfg.machine, library_dir, seed=cfg.seed)
    machine = PlantMachine(model)
    if cfg.state_file is not None and cfg.state_file.exists():
        apply_state(machine, load_state(cfg.state_file))
    server = PlantServer(machine, cfg)
    if cfg.trace_path is not None:
        server.trace = TraceWriter(cfg.trace_path, server.drives, cfg.trace_format)
    return server


def run_serve(args: argparse.Namespace) -> int:
    from .core_binding import PlantCoreUnavailable
    from .plant_state import PlantStateError, save_state

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = _config(args)
        server = build_server(cfg, args.dir)
        sock = server.bind()
    except MachineConfigError as exc:
        print("Plant nie wystartował — błąd konfiguracji maszyny:\n"
              + "\n".join(f"  {e}" for e in exc.errors), file=sys.stderr)
        return 1
    except (PlantConfigError, PlantStateError, PlantCoreUnavailable) as exc:
        print(f"Plant nie wystartował: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Plant nie wystartował: gniazdo UDP: {exc}", file=sys.stderr)
        return 1
    signal.signal(signal.SIGTERM, lambda *_: server.stop())
    print(f"Plant: {server.machine.model.name}, {len(server.drives)} osi LRT-NET, "
          f"{cfg.mode}, UDP {cfg.listen}:{cfg.port}", flush=True)
    try:
        server.serve(sock, args.frames)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        if server.trace is not None:
            server.trace.close()
        if cfg.state_file is not None:
            save_state(server.machine, cfg.state_file)
    s = server.stats
    print(f"Plant: ramki {s.received}, odrzucone {s.rejected}, utracone {s.lost}, "
          f"spóźnione {s.late}; ślad SHA-256 {server.digest}", flush=True)
    return 0
