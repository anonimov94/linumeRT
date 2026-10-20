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
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kontrola profilu, bez uruchamiania CNC")
    parser.add_argument("ini", type=Path)
    args = parser.parse_args(argv)
    try:
        cfg = read_deployment(args.ini)
        errors = check_deployment(cfg)
        profile = cfg.get("LINUMERT", "MACHINE_PROFILE", fallback="")
    except (OSError, ValueError, configparser.Error) as exc:
        errors, profile = [str(exc)], ""
    print(json.dumps({"profile": profile, "declaration_complete": not errors,
                      "hardware_verified": False, "errors": errors,
                      "note": "NIEZWERYFIKOWANE NA SPRZĘCIE; bez analizy połączeń HAL"},
                     ensure_ascii=False))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
