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

from pathlib import Path

from .config_files import _relative, backup_configuration, configuration_diff
from .configgen import Options, render
from .schema import MachineConfigError, load_machine
from .validate import validate_machine


def build(machine: Path, target: str, out: Path, *, write: bool = False,
          options: Options | None = None, renderer=render) -> tuple[str, Path | None]:
    """Zwraca (diff, katalog kopii zapasowej albo None). Błędy: MachineConfigError/ValueError."""
    cfg = load_machine(machine)
    errors = validate_machine(cfg)
    if errors:
        raise MachineConfigError(errors)
    files = renderer(cfg, target, options)
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
