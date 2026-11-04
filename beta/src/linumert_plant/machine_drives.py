"""Napędy maszyny: `machine.yaml` (sekcja `drives:`) + biblioteka szablonów (REQ-VD-02).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 013.

Wirtualna obrabiarka powstaje wyłącznie z `machine.yaml`, a każdy napęd jest instancją szablonu
z `plant/library/drives/` (CLAUDE.md §5a). Ten moduł łączy oba źródła:

1. struktura i spójność `machine.yaml` (`linumert.machine`, sesja 010), z listą znanych szablonów;
2. rozwiązanie instancji `{id, template, overrides}` z walidacją nadpisań zakresami szablonu;
3. zgodność rodzaju mechaniki z miejscem użycia: oś liniowa (X/Y/Z/U/V/W) wymaga
   `mechanics.kind: linear`, oś obrotowa (A/B/C) i wrzeciono — `rotary`.

Wszystkie błędy zbierane są naraz i zgłaszane jako `MachineConfigError` (lista komunikatów
po polsku ze ścieżką pola, np. `drives[3].overrides.mechanics.load: ...`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from linumert.machine.schema import MachineConfig, MachineConfigError, load_machine
from linumert.machine.validate import validate_machine

from .drive_library import DriveInstance, load_library, resolve_instances
from .drive_template import TemplateError


def _kind_issues(cfg: MachineConfig, drives: dict[str, DriveInstance]) -> list[str]:
    errors: list[str] = []
    for index, axis in enumerate(cfg.axes):
        wanted = "rotary" if axis.rotary else "linear"
        for name in axis.drives:
            inst = drives.get(name)
            if inst is not None and inst.params["mechanics"]["kind"] != wanted:
                errors.append(f"axes[{index}].drives: napęd {name} (szablon {inst.template_id}) "
                              f"ma mechanikę {inst.params['mechanics']['kind']}, a oś "
                              f"{axis.letter} wymaga {wanted}")
    spindle = drives.get(cfg.spindle.drive)
    if spindle is not None and spindle.params["mechanics"]["kind"] != "rotary":
        errors.append(f"spindle.drive: napęd {cfg.spindle.drive} (szablon {spindle.template_id}) "
                      "musi mieć mechanikę rotary")
    return errors


def resolve_machine_drives(cfg: MachineConfig, library: dict[str, dict[str, Any]]
                           ) -> dict[str, DriveInstance]:
    """Zwraca instancje napędów maszyny (id → instancja); błędy jako `MachineConfigError`."""
    errors = validate_machine(cfg, drive_templates=set(library))
    entries = [{"id": d.name, "template": d.template, "overrides": d.overrides}
               for d in cfg.drives if d.template in library]
    drives: dict[str, DriveInstance] = {}
    try:
        drives = resolve_instances(entries, library)
    except TemplateError as exc:
        # resolve_instances numeruje tylko wpisy ze znanym szablonem — przywróć indeksy z pliku.
        index_of = {f"drives[{n}]": f"drives[{cfg.drives.index(d)}]"
                    for n, d in enumerate(d for d in cfg.drives if d.template in library)}
        for issue in exc.issues:
            head, dot, rest = issue.path.partition(".")
            errors.append(f"{index_of.get(head, head)}{dot}{rest}: {issue.message}")
    errors += _kind_issues(cfg, drives)
    if errors:
        raise MachineConfigError(errors)
    return drives


def load_machine_drives(machine: Path | str, library_dir: Path | None = None
                        ) -> tuple[MachineConfig, dict[str, DriveInstance]]:
    """Wczytuje `machine.yaml` i bibliotekę; zwraca konfigurację i rozwiązane napędy."""
    cfg = load_machine(machine)
    try:
        library = load_library(library_dir)
    except TemplateError as exc:
        raise MachineConfigError([f"biblioteka napędów: {i}" for i in exc.issues]) from exc
    return cfg, resolve_machine_drives(cfg, library)
