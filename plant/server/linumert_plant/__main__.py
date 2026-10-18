"""Wiersz poleceń Plant: `python -m linumert_plant drive <list|show|validate|clone|schema>`.

Model-Author: Claude · sesja 013 (REQ-VD-03). Kody wyjścia: 0 = OK, 1 = błąd danych, 2 = użycie.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="linumert_plant", description="Plant: wirtualna maszyna")
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
    return parser


def _find_machine_entry(machine: Path, source: str) -> dict:
    try:
        data = yaml.safe_load(machine.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TemplateError(Issue(str(machine), f"nie można wczytać machine.yaml: {exc}")) from exc
    drives = data.get("drives") if isinstance(data, dict) else None
    if not isinstance(drives, list):
        raise TemplateError(Issue(str(machine), "brak listy drives:"))
    for entry in drives:
        if isinstance(entry, dict) and entry.get("id") == source:
            return entry
    raise TemplateError(Issue(str(machine), f"brak instancji napędu „{source}”"))


def _run(args: argparse.Namespace) -> int:
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
