"""Uruchomienie serwera Plant z wiersza poleceń (`python -m linumert_plant serve`).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 016.

Błędna konfiguracja (machine.yaml, plant.yaml, brak szablonu napędu, brak rdzenia C) kończy
się czytelnym komunikatem i kodem 1 — Plant nie startuje, więc napędy pozostają wyłączone
(docs/PLANT.md §8). Po starcie żaden błąd ramki ani modelu nie kończy procesu.

Projekt beta: panel web został usunięty (aplikacja bez GUI). `serve` uruchamia wyłącznie
serwer LRT-NET; telemetria i parametry live są dostępne przez API headless.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from pathlib import Path

from linumert.machine.schema import MachineConfigError

from .server import PlantConfig, PlantConfigError, PlantServer, load_plant_config
from .vfd import start_servers


def add_parser(sub) -> None:
    _add_serve_args(sub.add_parser("serve", help="serwer LRT-NET (UDP) wirtualnej obrabiarki"))


def _add_serve_args(serve) -> None:
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
    serve.add_argument("--report", type=Path, default=None,
                       help="raport JSON na zakończenie (statystyki, wyrocznia REQ-VM-06)")
    serve.add_argument("--dir", type=Path, default=None, help="katalog biblioteki napędów")
    serve.add_argument("--state-dir", type=Path, default=Path("state"),
                       help="katalog presetów i nagrań CSV telemetrii (domyślnie state/)")


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
    from .build_machine import build_model
    from .core_binding import PlantMachine
    from .machine_drives import load_machine_drives
    from .plant_state import apply_state, load_state
    from .trace import TraceWriter

    mcfg, drives = load_machine_drives(cfg.machine, library_dir)
    model = build_model(mcfg, drives, seed=cfg.seed)
    machine = PlantMachine(model)
    if cfg.state_file is not None and cfg.state_file.exists():
        apply_state(machine, load_state(cfg.state_file))
    spindle = drives.get(mcfg.spindle.drive)
    server = PlantServer(machine, cfg, spindle_template=None if spindle is None else spindle.params,
                         drive_params={name: inst.params for name, inst in drives.items()})
    if cfg.trace_path is not None:
        server.trace = TraceWriter(cfg.trace_path, server.drives, cfg.trace_format)
    return server


def run_serve(args: argparse.Namespace) -> int:
    from .core_binding import PlantCoreUnavailable
    from .plant_state import PlantStateError, save_state

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Krótszy interwał przełączania wątków skraca opóźnienie odpowiedzi LRT-NET.
    sys.setswitchinterval(0.0005)
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
    vfd_servers: list = []
    if cfg.vfd is not None:
        try:
            vfd_servers = start_servers(cfg.vfd, server.spindle, server._lock, server.vfd_faults)
        except OSError as exc:
            sock.close()
            print(f"Plant nie wystartował: falownik (pty/Modbus TCP): {exc}", file=sys.stderr)
            return 1
    signal.signal(signal.SIGTERM, lambda *_: server.stop())
    print(f"Plant: {server.machine.model.name}, {len(server.drives)} osi LRT-NET, "
          f"{cfg.mode}, UDP {cfg.listen}:{cfg.port}", flush=True)
    for srv in vfd_servers:
        where = getattr(srv, "link", None) or f"Modbus TCP {cfg.vfd.modbus_listen}:{srv.port}"
        print(f"Plant: falownik wrzeciona — {where}", flush=True)
    try:
        server.serve(sock, args.frames)
    except KeyboardInterrupt:
        pass
    finally:
        for srv in vfd_servers:
            srv.close()
        sock.close()
        if server.trace is not None:
            server.trace.close()
        if cfg.state_file is not None:
            save_state(server.machine, cfg.state_file)
    s = server.stats
    print(f"Plant: ramki {s.received}, odrzucone {s.rejected}, utracone {s.lost}, "
          f"spóźnione {s.late}; ślad SHA-256 {server.digest}", flush=True)
    o = server.oracle
    print(f"Plant: wyrocznia {'PASS' if o.passed else 'FAIL'} (naruszenia {o.total}, "
          f"sprawdzone ramki {o.checked})", flush=True)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(server.report(), ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    return 0
