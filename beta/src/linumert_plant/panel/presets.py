"""Presety parametrów live napędów: wbudowane (mnożniki) i zapisane (wartości) — sesja 022.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 022.

Preset to mapa `{napęd: {ścieżka: wartość}}`. Presety wbudowane mnożą wartości startowe
z szablonu (`machine.yaml` + overrides), więc pasują do każdej maszyny; dotyczą tylko ścieżek
oznaczonych `live` w szablonie danego napędu. Presety użytkownika to pliki JSON w katalogu
presetów (domyślnie `state/presets/`), zapisywane z bieżących wartości.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

# nazwa → (opis, {ścieżka: mnożnik wartości startowej})
BUILTIN: dict[str, tuple[str, dict[str, float]]] = {
    "startowy": ("wartości z machine.yaml", {}),
    "lekki": ("masa obciążenia × 0,5", {"mechanics.load": 0.5}),
    "ciezki_stol": ("masa obciążenia × 2", {"mechanics.load": 2.0}),
    "zuzyty_silnik": ("tarcie × 2, limit momentu × 0,8",
                      {"mechanics.friction_coulomb": 2.0, "mechanics.friction_static": 2.0,
                       "mechanics.friction_viscous": 2.0, "limits.torque_limit_permille": 0.8}),
}


class PresetError(ValueError):
    pass


def _get(params: dict[str, Any], path: str) -> Any:
    section, key = path.split(".", 1)
    return params[section][key]


def check_name(name: str) -> str:
    if not NAME_RE.match(name or ""):
        raise PresetError(f"nazwa presetu „{name}”: dozwolone litery, cyfry, _ i - (1–40 znaków)")
    return name


def builtin_values(name: str, base: dict[str, dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Wartości presetu wbudowanego dla napędów o parametrach startowych `base`."""
    _desc, factors = BUILTIN[name]
    out: dict[str, dict[str, float]] = {}
    for drive, params in base.items():
        values = {}
        for path in params["live"]:
            factor = factors.get(path, 1.0)
            value = _get(params, path) * factor
            values[path] = round(value) if path == "limits.torque_limit_permille" else value
        out[drive] = values
    return out


def list_presets(store: Path | None) -> list[dict[str, str]]:
    items = [{"name": n, "kind": "wbudowany", "desc": d} for n, (d, _f) in BUILTIN.items()]
    if store is not None and store.is_dir():
        for path in sorted(store.glob("*.json")):
            if NAME_RE.match(path.stem) and path.stem not in BUILTIN:
                items.append({"name": path.stem, "kind": "zapisany", "desc": path.name})
    return items


def load_preset(name: str, base: dict[str, dict[str, Any]],
                store: Path | None) -> dict[str, dict[str, float]]:
    check_name(name)
    if name in BUILTIN:
        return builtin_values(name, base)
    if store is None:
        raise PresetError("brak katalogu presetów")
    path = store / f"{name}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PresetError(f"brak presetu „{name}”") from None
    except (OSError, json.JSONDecodeError) as exc:
        raise PresetError(f"{path}: nie można odczytać ({exc})") from None
    values = data.get("values") if isinstance(data, dict) else None
    if not isinstance(values, dict) or not all(isinstance(v, dict) for v in values.values()):
        raise PresetError(f"{path}: oczekiwano {{\"values\": {{napęd: {{ścieżka: wartość}}}}}}")
    return values


def save_preset(name: str, values: dict[str, dict[str, float]], store: Path | None) -> Path:
    check_name(name)
    if name in BUILTIN:
        raise PresetError(f"„{name}” to preset wbudowany; wybierz inną nazwę")
    if store is None:
        raise PresetError("brak katalogu presetów")
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{name}.json"
    path.write_text(json.dumps({"name": name, "values": values}, ensure_ascii=False, indent=2)
                    + "\n", encoding="utf-8")
    return path
