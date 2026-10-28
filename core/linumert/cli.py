"""Headless CLI. SPDX-License-Identifier: GPL-2.0-or-later. Model-Author: Codex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .machine.schema import MachineConfigError


def registry():
    """A fresh registry without global registration or GUI side effects."""
    from .generators import basic, contours, drilling, engraving, pockets, shapes, surfacing
    from .generators.registry import GeneratorRegistry

    result = GeneratorRegistry()
    for module in (basic, drilling, pockets, contours, surfacing, shapes, engraving):
        module.register(result)
    return result


def _tool(text: str) -> tuple[int, float, float]:
    import math

    try:
        number, length, diameter = text.split(":")
        row = (int(number), float(length), float(diameter))
        if row[0] <= 0 or not all(math.isfinite(x) and x > 0 for x in row[1:]):
            raise ValueError
        return row
    except ValueError as exc:
        raise argparse.ArgumentTypeError("narzędzie: T:DŁUGOŚĆ:ŚREDNICA, dodatnie mm") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linumert-lite", description="linumeRT lite — CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("generators", help="dostępne generatory CAM 2D")
    compile_cmd = commands.add_parser("compile", help=".lnx → G-code; zapis atomowy")
    compile_cmd.add_argument("program", type=Path)
    compile_cmd.add_argument("--out", type=Path)
    machine = commands.add_parser("machine", help="walidacja maszyny i skale napędów")
    machine.add_argument("path", type=Path)
    config = commands.add_parser("config", help="eksport konfiguracji LinuxCNC sim/Plant")
    config.add_argument("machine", type=Path)
    config.add_argument("--target", choices=("sim", "plant"), required=True)
    config.add_argument("--out", type=Path, required=True)
    config.add_argument("--write", action="store_true", help="zapis z kopią zapasową")
    config.add_argument("--test-mode", action="store_true", help="bypass HMI tylko w symulacji")
    simulate = commands.add_parser("simulate", help="diagnostyczna symulacja 2.5D do JSON")
    simulate.add_argument("program", type=Path)
    simulate.add_argument("--out", type=Path)
    simulate.add_argument("--tool", type=_tool, action="append", default=[])
    simulate.add_argument("--source", choices=("subset", "rs274"), default="subset")
    args = parser.parse_args(argv)
    try:
        if args.command == "generators":
            reg = registry()
            for name in reg.names():
                print(f"{name} v{reg.latest(name).version}")
        elif args.command == "compile":
            from .programs.compiler import compile_file

            print(compile_file(args.program, args.out, registry=registry()))
        elif args.command == "machine":
            from .machine.drives.drive_real import counts_per_unit
            from .machine.drives.machine_drives import load_machine_drives

            cfg, drives = load_machine_drives(args.path)
            print(json.dumps({"name": cfg.machine.name, "axes": [a.letter for a in cfg.axes],
                              "drives": {name: {"template": inst.template_id,
                                                "counts_per_unit": counts_per_unit(inst.params)}
                                         for name, inst in drives.items()}}, indent=2))
        elif args.command == "config":
            from .machine.lite_config import build

            diff, backup = build(args.machine, args.target, args.out,
                                 write=args.write, test_mode=args.test_mode)
            if diff:
                print(diff, end="")
            if backup:
                print(f"Kopia: {backup}", file=sys.stderr)
            return 1 if diff and not args.write else 0
        elif args.command == "simulate":
            from linumert_sim.offline import OfflineJob, simulate

            from .programs.lnx import atomic_write

            result = simulate(OfflineJob(args.program.read_text(encoding="utf-8"),
                                         tools=tuple(args.tool), source=args.source))
            text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            if args.out:
                atomic_write(args.out, text)
            else:
                print(text, end="")
    except (OSError, ValueError, RuntimeError, MachineConfigError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
