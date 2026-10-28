"""CLI generatora konfiguracji: `linumert-config build` (sesja 062).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

    linumert-config build config/machines/mill_servo_table.yaml --target plant --out DIR
    linumert-config build MACHINE.yaml --target sim --out DIR --write

Bez `--write` tylko pokazuje diff (nic nie zapisuje). Z `--write`: walidacja machine.yaml
(struktura, spójność, biblioteka napędów), kopia zapasowa całego istniejącego katalogu
(`config_files.backup_configuration`, nigdy nie nadpisuje poprzednich kopii), zapis wyłącznie
plików generatora; pliki operatora (tool.tbl, linumert.var, makra, ekran) zostają bez zmian.
Kody wyjścia: 0 = bez zmian albo zapisano, 1 = są zmiany (podgląd), 2 = błąd.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config_files import _relative, backup_configuration, configuration_diff
from .configgen import TARGETS, Options, render
from .schema import MachineConfigError, load_machine
from .validate import validate_machine


def build(machine: Path, target: str, out: Path, *, write: bool = False,
          options: Options | None = None) -> tuple[str, Path | None]:
    """Zwraca (diff, katalog kopii zapasowej albo None). Błędy: MachineConfigError/ValueError."""
    cfg = load_machine(machine)
    errors = validate_machine(cfg)
    if errors:
        raise MachineConfigError(errors)
    files = render(cfg, target, options)
    diff = configuration_diff(out, files)
    backup = None
    if write and diff:
        backup = backup_configuration(out)
        out.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            path = out / _relative(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(path)
    return diff, backup


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="linumert-config",
                                 description="Konfiguracja LinuxCNC z machine.yaml (linumeRT)")
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="generuj INI/HAL (domyślnie tylko diff)")
    b.add_argument("machine", type=Path, help="machine.yaml")
    b.add_argument("--target", choices=TARGETS, required=True)
    b.add_argument("--out", type=Path, required=True, help="katalog konfiguracji")
    b.add_argument("--write", action="store_true", help="zapisz (z kopią zapasową)")
    b.add_argument("--ip", default=Options.ip, help="adres serwera Plant")
    b.add_argument("--port", type=int, default=Options.port, help="port LRT-NET")
    args = ap.parse_args(argv)
    try:
        diff, backup = build(args.machine, args.target, args.out, write=args.write,
                             options=Options(ip=args.ip, port=args.port))
    except MachineConfigError as exc:
        for line in exc.errors:
            print(f"błąd: {line}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"błąd: {exc}", file=sys.stderr)
        return 2
    if not diff:
        print("Bez zmian.")
        return 0
    sys.stdout.write(diff)
    if not args.write:
        print("\nPodgląd — nic nie zapisano. Zapis: --write (z kopią zapasową).", file=sys.stderr)
        return 1
    print(f"\nZapisano {args.out}" + (f"; kopia zapasowa: {backup}" if backup else ""),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
