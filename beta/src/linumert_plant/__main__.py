"""Wiersz poleceń Plant: `python -m linumert_plant drive|machine <polecenie>`.

Polecenia napędów: list, show, validate, clone, schema, instances. Maszyna (sesja 014):
`machine build <machine.yaml> [--keys] [--run]` — model z machine.yaml, z --run próba w rdzeniu C.
Serwer LRT-NET (sesja 016): `serve [machine.yaml] [--plant plant.yaml] [--lockstep|--realtime]`;
z panelem web (sesja 022): `serve --panel PORT` albo `panel [--panel-port PORT]`.
Z katalogu głównego repozytorium to samo działa jako `python -m plant ...` (plant/__main__.py).

Model-Author: Claude · sesja 013 (REQ-VD-03). Kody wyjścia: 0 = OK, 1 = błąd danych, 2 = użycie.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import serve as serve_cli
from .drive_library import (
    LIBRARY_DIR,
    clone_instance,
    clone_template,
    load_library,
    load_template_file,
    resolve_instance,
    save_template,
)
from .drive_template import Issue, TemplateError, json_schema, total_inertia
from .machine_drives import MachineConfigError, load_machine_drives


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plant", description="Plant: wirtualna maszyna")
    sub = parser.add_subparsers(dest="group", required=True)
    drive = sub.add_parser("drive", help="biblioteka napędów wirtualnych")
    drive.add_argument("--dir", type=Path, default=None,
                       help=f"katalog biblioteki (domyślnie {LIBRARY_DIR})")
    cmds = drive.add_subparsers(dest="command", required=True)
    cmds.add_parser("list", help="wypisz szablony")
    show = cmds.add_parser("show", help="pokaż szablon jako YAML")
    show.add_argument("id")
    val = cmds.add_parser("validate", help="sprawdź plik szablonu")
    val.add_argument("path", type=Path)
    clone = cmds.add_parser("clone", help="sklonuj szablon albo instancję pod nowym id")
    clone.add_argument("source", help="id szablonu albo id instancji (z --machine)")
    clone.add_argument("new_id")
    clone.add_argument("--machine", type=Path, default=None,
                       help="machine.yaml z listą drives: (źródło = instancja)")
    clone.add_argument("--name", default=None, help="nazwa wyświetlana kopii")
    clone.add_argument("--force", action="store_true", help="nadpisz istniejący szablon")
    cmds.add_parser("schema", help="wypisz JSON Schema szablonu")
    inst = cmds.add_parser("instances", help="rozwiąż napędy z machine.yaml (szablon + overrides)")
    inst.add_argument("machine", type=Path)
    machine = sub.add_parser("machine", help="wirtualna obrabiarka z machine.yaml")
    mcmds = machine.add_subparsers(dest="command", required=True)
    build = mcmds.add_parser("build", help="zbuduj model maszyny z machine.yaml")
    build.add_argument("machine", type=Path)
    build.add_argument("--keys", action="store_true", help="wypisz klucze konfiguracji rdzenia C")
    build.add_argument("--run", action="store_true",
                       help="uruchom model w rdzeniu C (wymaga kompilatora, Linux/WSL)")
    build.add_argument("--dir", type=Path, default=None, help="katalog biblioteki napędów")
    serve_cli.add_parser(sub)
    return parser


def _print_errors(exc: MachineConfigError) -> None:
    print("Błąd:\n" + "\n".join(f"  {e}" for e in exc.errors), file=sys.stderr)


def _run_machine(args: argparse.Namespace) -> int:
    from .build_machine import build_machine

    try:
        model = build_machine(args.machine, args.dir)
    except MachineConfigError as exc:
        _print_errors(exc)
        return 1
    if args.keys:
        print(model.to_text(), end="")
        return 0
    kin = model.kinematics
    print(f"Maszyna {model.name}: {len(model.joints)} osi, {len(model.drives)} napędów, "
          f"{len(model.links)} członów łańcucha")
    if kin:
        print(f"Kinematyka LinuxCNC: {kin['module']} coordinates={kin['coordinates']} "
              f"kinstype={kin['kinstype']}")
    for letter in model.joints:
        print(f"  {letter}: {', '.join(model.joint_drives[letter])}")
    if model.spindle:
        print(f"  wrzeciono: {model.spindle}")
    pins = sorted(model.inputs.items(), key=lambda item: item[1])
    print("Wejścia: " + ", ".join(f"{name}={pin}" for name, pin in pins))
    if args.run:
        from .core_binding import PlantCoreUnavailable, PlantMachine

        try:
            plant = PlantMachine(model)
        except PlantCoreUnavailable as exc:
            print(f"Rdzeń C niedostępny: {exc}", file=sys.stderr)
            return 1
        except MachineConfigError as exc:
            _print_errors(exc)
            return 1
        tip = ", ".join(f"{v:.3f}" for v in plant.tool_tip(workpiece=True))
        print(f"Rdzeń C: OK; koniec narzędzia w układzie detalu [mm]: ({tip}); "
              f"wejścia 0x{plant.inputs:08x}")
    return 0


def _find_machine_entry(machine: Path, source: str) -> dict:
    try:
        data = yaml.safe_load(machine.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TemplateError(Issue(str(machine), f"nie można wczytać machine.yaml: {exc}")) from exc
    drives = data.get("drives") if isinstance(data, dict) else None
    if not isinstance(drives, list):
        raise TemplateError(Issue(str(machine), "brak listy drives:"))
    for entry in drives:
        if isinstance(entry, dict) and entry.get("id", entry.get("name")) == source:
            entry = dict(entry)
            entry["id"] = entry.pop("name", source) if "id" not in entry else entry["id"]
            return entry
    raise TemplateError(Issue(str(machine), f"brak instancji napędu „{source}”"))


def _run(args: argparse.Namespace) -> int:
    if args.group in ("serve", "panel"):
        return serve_cli.run_serve(args)
    if args.group == "machine":
        return _run_machine(args)
    if args.command == "list":
        for tpl in load_library(args.dir).values():
            print(f"{tpl['id']:28} {tpl['type']:14} v{tpl['version']}  {tpl['name']}")
        return 0
    if args.command == "show":
        tpl = load_library(args.dir).get(args.id)
        if tpl is None:
            print(f"Nieznany szablon „{args.id}”.", file=sys.stderr)
            return 1
        print(yaml.safe_dump(tpl, sort_keys=False, allow_unicode=True, width=100), end="")
        print(f"# J zastępcze na wale: {total_inertia(tpl):.3e} kg·m²")
        return 0
    if args.command == "validate":
        tpl = load_template_file(args.path)
        print(f"OK: {tpl['id']} v{tpl['version']}")
        return 0
    if args.command == "schema":
        print(json.dumps(json_schema(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "instances":
        try:
            _cfg, drives = load_machine_drives(args.machine, args.dir)
        except MachineConfigError as exc:
            print("Błąd:\n" + "\n".join(f"  {e}" for e in exc.errors), file=sys.stderr)
            return 1
        for inst in drives.values():
            changed = ", ".join(f"{k}={v}" for k, v in inst.overrides.items()) or "-"
            print(f"{inst.id:14} {inst.template_id:26} overrides: {changed}")
        return 0
    library = load_library(args.dir)
    if args.machine is not None:
        entry = _find_machine_entry(args.machine, args.source)
        new = clone_instance(resolve_instance(entry, library), args.new_id, name=args.name)
    elif args.source in library:
        new = clone_template(library[args.source], args.new_id, name=args.name)
    else:
        print(f"Nieznany szablon „{args.source}” (dla instancji podaj --machine).",
              file=sys.stderr)
        return 1
    path = save_template(new, args.dir, overwrite=args.force)
    print(f"Zapisano {path} (based_on: {new['based_on']}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return _run(args)
    except TemplateError as exc:
        print(f"Błąd:\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
