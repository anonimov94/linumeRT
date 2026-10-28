# SPDX-License-Identifier: GPL-2.0-or-later
"""Bramka przed uruchomieniem LinuxCNC. Model-Author: Codex.

Kontrola konfiguracji nie potwierdza bezpieczeństwa fizycznej maszyny.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import sys
import sysconfig
from pathlib import Path

from .deployment import PROFILES, check_deployment, hal_files_from_ini, read_deployment
from .hal_audit import audit_hal


def preflight(path: Path, expected_profile: str | None = None) -> dict:
    """Odmowa przy nieznanym profilu; audyt HAL obowiązkowy tylko dla hardware."""
    report = {"profile": "", "declaration_complete": False, "static_hal_checked": False,
              "static_hal_passed": None, "hardware_verified": False, "errors": [],
              "note": "NIEZWERYFIKOWANE NA SPRZĘCIE; kontrola konfiguracji, bez zgody na ruch"}
    try:
        path = path.resolve()
        cfg = read_deployment(path)
        profile = cfg.get("LINUMERT", "MACHINE_PROFILE", fallback="").strip()
        report["profile"] = profile
        errors = check_deployment(cfg)
        report["declaration_complete"] = not errors
        if expected_profile is not None and profile != expected_profile:
            errors.append(f"oczekiwany profil {expected_profile}, odczytano {profile!r}")
        if profile == "hardware" and not errors:
            report["static_hal_checked"] = True
            errors += audit_hal(hal_files_from_ini(path), cfg, path.resolve().parent)
            report["static_hal_passed"] = not errors
        report["errors"] = errors
    except (OSError, UnicodeError, ValueError, RuntimeError, configparser.Error) as exc:
        report["errors"] = [str(exc)]
        if report["static_hal_checked"]:
            report["static_hal_passed"] = False
    return report


def cnc_environment() -> dict[str, str]:
    """Keep venv packages visible to QtVCP's absolute /usr/bin/python3 shebang.

    LinuxCNC/QtVCP still use Debian's Python. The starter's venv has matching
    Python 3.11 and --system-site-packages; forward its dependency directories
    without replacing the caller's core/module paths or changing the parent env.
    """
    env = dict(os.environ)
    if sys.prefix != sys.base_prefix:
        paths = env["PYTHONPATH"].split(os.pathsep) if env.get("PYTHONPATH") else []
        for key in ("purelib", "platlib"):
            path = sysconfig.get_path(key)
            if path not in paths:
                paths.append(path)
        env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ini", type=Path)
    parser.add_argument("--expect-profile", choices=PROFILES)
    parser.add_argument("--check-only", action="store_true", help="bez uruchomienia LinuxCNC")
    args = parser.parse_args(argv)
    path = args.ini.absolute()
    report = preflight(path, args.expect_profile)
    print(json.dumps(report, ensure_ascii=False), file=sys.stderr, flush=True)
    if report["errors"]:
        return 2
    if args.check_only:
        return 0
    try:
        os.execvpe("linuxcnc", ["linuxcnc", str(path.resolve())], cnc_environment())
    except (OSError, RuntimeError) as exc:
        print(f"Nie uruchomiono LinuxCNC: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
