# SPDX-License-Identifier: GPL-2.0-or-later
"""Deklaracje wdrożenia, bez sterowania HAL. Model-Author: Codex.

Sprawdza kompletność deklaracji, nie okablowanie ani poziom bezpieczeństwa.
Użycie: python -m linumert.machine.deployment machine.ini
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import shlex
from pathlib import Path

PROFILES = ("sim", "plant", "hardware")
PIN = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]*")
REQUIRED = ("ESTOP_MONITOR_PIN", "PC_HEARTBEAT_OUTPUT_PIN", "PC_WATCHDOG_MONITOR_PIN")
SOFTWARE = ("iocontrol.", "halui.", "linumert.hmi", "lrt_hmi", "watchdog.", "lrt-net.")


def check_deployment(cfg: configparser.ConfigParser) -> list[str]:
    """Zwraca błędy deklaracji. Brak profilu nigdy nie oznacza symulacji."""
    profile = cfg.get("LINUMERT", "MACHINE_PROFILE", fallback="").strip()
    if profile not in PROFILES:
        return ["LINUMERT.MACHINE_PROFILE: wymagane sim, plant albo hardware"]
    if profile != "hardware":
        return []
    errors = []
    for flag, expected in (("VIRTUAL_MODE", "0"), ("HMI_ESTOP_BYPASS", "0")):
        if cfg.get("LINUMERT", flag, fallback="0").strip() != expected:
            errors.append(f"hardware: {flag} musi wynosić 0")
    pins = {}
    for key in REQUIRED:
        pin = cfg.get("SAFETY", key, fallback="").strip()
        if not PIN.fullmatch(pin):
            errors.append(f"SAFETY.{key}: wymagany jawny pin fizycznego I/O")
        elif pin.startswith(SOFTWARE):
            errors.append(f"SAFETY.{key}: pin software nie zastępuje fizycznego I/O")
        else:
            pins[key] = pin
    if len(set(pins.values())) != len(pins):
        errors.append("hardware: wejścia monitorujące i wyjście heartbeat muszą być różne")
    if cfg.get("SAFETY", "EXTERNAL_PC_WATCHDOG", fallback="").strip() != "1":
        errors.append("hardware: wymagany EXTERNAL_PC_WATCHDOG=1")
    if cfg.get("SAFETY", "PHYSICAL_RESET", fallback="").strip() != "1":
        errors.append("hardware: wymagany PHYSICAL_RESET=1")
    if cfg.get("SAFETY", "AUTOMATIC_RESTART", fallback="").strip() != "0":
        errors.append("hardware: wymagany AUTOMATIC_RESTART=0")
    return errors


def read_deployment(path: Path) -> configparser.ConfigParser:
    # LinuxCNC dopuszcza powtarzane HALFILE; wartości safety nie mogą być powtarzane.
    cfg = configparser.ConfigParser(strict=False, interpolation=None)
    seen = set()
    section = ""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            text = line.strip()
            if re.match(r"#\s*INCLUDE\b", text, re.IGNORECASE):
                raise ValueError("INI #INCLUDE wymaga osobnej analizy")
            if text.startswith("[") and not text.endswith("]"):
                raise ValueError("niejednoznaczny nagłówek sekcji INI")
            if text.startswith("[") and text.endswith("]"):
                section = text[1:-1].strip()
            elif section in ("SAFETY", "LINUMERT") and text and not text.startswith(("#", ";")):
                if "=" not in text:
                    raise ValueError(f"{section}: wymagane jednoznaczne KEY=VALUE")
                key = (section, text.split("=", 1)[0].strip().upper())
                if key in seen:
                    raise ValueError(f"powtórzona deklaracja {key[0]}.{key[1]}")
                seen.add(key)
        stream.seek(0)
        cfg.read_file(stream)
    if cfg.defaults():
        raise ValueError("INI DEFAULT wymaga osobnej analizy; deklaracje muszą być jawne")
    return cfg


def hal_files_from_ini(path: Path) -> list[Path]:
    """Zachowuje wszystkie HALFILE; ConfigParser przechowuje tylko ostatni."""
    files = []
    section = ""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if text.startswith("[") and text.endswith("]"):
            section = text[1:-1].strip()
        elif section == "HAL" and text and not text.startswith(("#", ";")):
            if "=" not in text:
                raise ValueError(f"{path}:{number}: wymagane KEY=VALUE w HAL")
            key, value = (part.strip() for part in text.split("=", 1))
            if key.upper() in ("HALCMD", "POSTGUI_HALCMD"):
                raise ValueError(f"{path}:{number}: HALCMD wymaga osobnej analizy")
            if key.upper() in ("HALFILE", "POSTGUI_HALFILE"):
                words = shlex.split(value, comments=True)
                if len(words) != 1 or any(c in value for c in ("$", "[", "]")):
                    raise ValueError(f"{path}:{number}: niejednoznaczna ścieżka HALFILE")
                files.append(Path(words[0]))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kontrola profilu, bez uruchamiania CNC")
    parser.add_argument("ini", type=Path)
    parser.add_argument("--hal", type=Path, action="append", default=[],
                        help="plik HAL względem katalogu INI; opcję można powtarzać")
    parser.add_argument("--hal-from-ini", action="store_true",
                        help="sprawdź wszystkie HALFILE i POSTGUI_HALFILE z INI")
    args = parser.parse_args(argv)
    declaration_ok = False
    hal_checked = bool(args.hal or args.hal_from_ini)
    hal_ok = None
    try:
        cfg = read_deployment(args.ini)
        errors = check_deployment(cfg)
        declaration_ok = not errors
        if hal_checked:
            from .hal_audit import audit_hal

            files = args.hal + (hal_files_from_ini(args.ini) if args.hal_from_ini else [])
            hal_errors = audit_hal(files, cfg, args.ini.resolve().parent)
            hal_ok = not hal_errors
            errors += hal_errors
        profile = cfg.get("LINUMERT", "MACHINE_PROFILE", fallback="")
    except (OSError, ValueError, configparser.Error) as exc:
        errors, profile = [str(exc)], ""
    print(json.dumps({"profile": profile, "declaration_complete": declaration_ok,
                      "static_hal_checked": hal_checked, "static_hal_passed": hal_ok,
                      "hardware_verified": False, "errors": errors,
                      "note": "NIEZWERYFIKOWANE NA SPRZĘCIE; bez oceny komponentów"},
                     ensure_ascii=False))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
