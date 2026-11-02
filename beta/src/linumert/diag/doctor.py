# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only environment inventory, without importing CNC or starting HAL. Model-Author: Codex."""

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path


def _module_present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def inspect_environment():
    """Presence is an observation, not evidence that a component works."""
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    version = platform.python_version()
    add("Python", "ok" if sys.version_info >= (3, 11) else "error",
        f"{version}; wymagany Python >= 3.11, docelowy Debian 12 / Python 3.11")
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        release = {}
    target = release.get("ID") == "debian" and release.get("VERSION_ID") == "12"
    add("System", "ok" if target else "info",
        f"{release.get('PRETTY_NAME', platform.system())}; cel: Debian 12")
    for module in ("yaml", "numpy", "linuxcnc", "hal"):
        present = _module_present(module)
        add(module, "ok" if present else "missing",
            "moduł znaleziony; nie został zaimportowany" if present else "modułu nie znaleziono")
    for command in ("linuxcnc", "rs274", "halcmd", "lcec_conf"):
        path = shutil.which(command)
        add(f"PATH:{command}", "ok" if path else "missing",
            f"znaleziono {path}; nie uruchomiono" if path else "brak w PATH")
    try:
        realtime = Path("/sys/kernel/realtime").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        realtime = "unknown"
    add("Jądro", "info", platform.release())
    add("PREEMPT_RT", "info",
        {"1": "jądro zgłasza realtime=1; latencja niezmierzona",
         "0": "jądro zgłasza realtime=0"}.get(realtime, "brak odczytu /sys/kernel/realtime"))
    return {
        "schema_version": 1,
        "checks": checks,
        "hardware_verified": False,
        "scope": "Inwentaryzacja bieżącego procesu. Nie jest kwalifikacją maszyny.",
        "not_checked": ["wersja i działanie LinuxCNC", "latencja RT", "załadowane komponenty HAL",
                        "uprawnienia urządzeń", "EtherCAT i Plant", "safety/STO"],
    }


def format_report(report):
    rows = [report["scope"], ""]
    labels = {"ok": "obecne", "info": "informacja", "missing": "brak", "error": "błąd"}
    rows.extend(f"[{labels[c['status']]}] {c['name']}: {c['detail']}" for c in report["checks"])
    rows.extend(["", "Nie sprawdzono: " + ", ".join(report["not_checked"]),
                 "NIEZWERYFIKOWANE NA SPRZĘCIE"])
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Odczyt środowiska bez uruchamiania CNC/HAL")
    parser.add_argument("--json", action="store_true", help="raport w formacie JSON")
    args = parser.parse_args(argv)
    report = inspect_environment()
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
    # Missing CNC is expected in an offline editor/cloud. The output lists each missing item.
    return int(any(c["status"] == "error" for c in report["checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
