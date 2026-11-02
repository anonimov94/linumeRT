"""Plik stanu wirtualnej obrabiarki między uruchomieniami (REQ-VM-07, sesja 015).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 015.

Po wyłączeniu prawdziwa maszyna zostaje tam, gdzie stała (gantry także z rozjazdem stron),
a enkoder absolutny z baterią pamięta pozycję. Plik stanu przenosi to między uruchomieniami
Plant: położenie każdego napędu [jedn. machine.yaml] i stan enkodera absolutnego
(przesunięcie w impulsach, czy ważne). Enkoder bez baterii (`homing.battery_backed: false`)
albo z rozładowaną baterią zapisuje się jako nieważny, więc po następnym włączeniu napęd
zgłasza E-4211 i oś trzeba zbazować ponownie.

Format JSON (wersja 1):
    {"version": 1, "machine": "<nazwa>", "time": <s>,
     "drives": {"<id>": {"position": <mm|°>, "absolute": {"offset": <imp>, "valid": <bool>}}}}
Zapis atomowy (plik tymczasowy + zamiana), żeby przerwany zapis nie zostawił uszkodzonego pliku.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from .core_binding import PlantMachine

STATE_VERSION = 1


class PlantStateError(ValueError):
    """Plik stanu nie pasuje do maszyny albo jest uszkodzony (komunikat po polsku)."""


def _battery_backed(machine: PlantMachine, drive: str) -> bool:
    cfg = machine.model.config
    if cfg is None:
        return True
    for axis in cfg.axes:
        if drive in axis.drives:
            return axis.homing.battery_backed
    return True


def capture_state(machine: PlantMachine) -> dict[str, Any]:
    """Stan do zapisania: położenia napędów osi i enkodery absolutne."""
    drives: dict[str, Any] = {}
    for names in machine.model.joint_drives.values():
        for drive in names:
            entry: dict[str, Any] = {"position": machine.drive_position(drive)}
            absolute = machine.absolute_state(drive)
            if absolute is not None:
                offset, valid = absolute
                entry["absolute"] = {"offset": offset,
                                     "valid": valid and _battery_backed(machine, drive)}
            drives[drive] = entry
    return {"version": STATE_VERSION, "machine": machine.model.name, "time": machine.time,
            "drives": drives}


def save_state(machine: PlantMachine, path: Path | str) -> Path:
    """Zapisuje stan maszyny do pliku JSON (atomowo)."""
    path = Path(path)
    data = capture_state(machine)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def load_state(path: Path | str) -> dict[str, Any]:
    """Wczytuje i sprawdza plik stanu (PlantStateError przy błędzie)."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PlantStateError(f"{path}: brak pliku stanu") from None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlantStateError(f"{path}: uszkodzony plik stanu ({exc})") from None
    if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
        raise PlantStateError(f"{path}: nieobsługiwana wersja pliku stanu "
                              f"(oczekiwano {STATE_VERSION})")
    if not isinstance(data.get("drives"), dict) or not isinstance(data.get("machine"), str):
        raise PlantStateError(f"{path}: brak pól machine/drives")
    return data


def apply_state(machine: PlantMachine, state: dict[str, Any]) -> None:
    """Nakłada stan przed pierwszym krokiem: położenia napędów i enkodery absolutne."""
    errors: list[str] = []
    if state.get("machine") != machine.model.name:
        errors.append(f"plik stanu dotyczy maszyny {state.get('machine')!r}, "
                      f"a uruchomiono {machine.model.name!r}")
    known = {d for names in machine.model.joint_drives.values() for d in names}
    for drive, entry in state.get("drives", {}).items():
        where = f"drives.{drive}"
        if drive not in known:
            errors.append(f"{where}: maszyna nie ma takiego napędu osi")
            continue
        position = entry.get("position") if isinstance(entry, dict) else None
        if not isinstance(position, (int, float)) or not math.isfinite(position):
            errors.append(f"{where}.position: wymagana liczba skończona")
            continue
        absolute = entry.get("absolute")
        if absolute is not None:
            if machine.absolute_state(drive) is None:
                errors.append(f"{where}.absolute: napęd nie ma enkodera absolutnego")
                continue
            if not isinstance(absolute.get("offset"), int) or \
                    not isinstance(absolute.get("valid"), bool):
                errors.append(f"{where}.absolute: wymagane offset (int) i valid (bool)")
                continue
    if errors:
        raise PlantStateError("; ".join(errors))
    for drive, entry in state["drives"].items():
        machine.set_drive_position(drive, float(entry["position"]))
        absolute = entry.get("absolute")
        if absolute is not None:
            machine.restore_absolute(drive, absolute["offset"], absolute["valid"])
