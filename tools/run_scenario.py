#!/usr/bin/env python3
"""Runner scenariuszy Plant z raportem HTML (sesja 024, REQ-QA-01…04).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 024.

Przykłady (z katalogu repozytorium):
    python tools/run_scenario.py                         # wszystkie plant/scenarios/*.yaml, atrapa
    python tools/run_scenario.py plant/scenarios/first_motion.yaml --master linuxcnc
    python tools/run_scenario.py --matrix                # matrix_smoke na config/machines/*.yaml
    python tools/run_scenario.py --ssh lrt@10.77.0.10 --remote-dir ~/linumeRT first_motion
Master `mock` (domyślny, CI): atrapa mastera LRT-NET w tym samym procesie, lockstep.
Master `linuxcnc`: LinuxCNC RIP (LINUXCNC_DIR) + Plant na localhost, sterowanie przez
`linuxcnc.command` (moduł `linumert_plant.scenario_linuxcnc`). `--ssh` uruchamia to samo
polecenie na VM przez ssh (wynik i raport zostają na VM). Raport: `docs/raporty/prototypy/`.
Kod wyjścia: 0 = wszystkie PASS, 1 = któryś FAIL, 2 = błąd scenariusza lub użycia.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("core", "simulation", "plant/server"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

SCENARIOS = ROOT / "plant" / "scenarios"
MACHINES = ROOT / "config" / "machines"
REPORTS = ROOT / "docs" / "raporty" / "prototypy"


def resolve(name: str) -> Path:
    path = Path(name)
    if path.is_file():
        return path
    candidate = SCENARIOS / (name if name.endswith(".yaml") else f"{name}.yaml")
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"brak scenariusza {name}")


def ssh_command(args: argparse.Namespace, argv: list[str]) -> list[str]:
    """Polecenie ssh uruchamiające runner na VM (te same argumenty bez --ssh)."""
    rest = []
    skip = False
    for item in argv:
        if skip:
            skip = False
            continue
        if item in ("--ssh", "--remote-dir"):
            skip = True
            continue
        if item.startswith(("--ssh=", "--remote-dir=")):
            continue
        rest.append(item)
    remote = f"cd {args.remote_dir} && python3 tools/run_scenario.py " + \
        " ".join(shlex.quote(x) for x in rest)
    return ["ssh", "-o", "BatchMode=yes", args.ssh, remote]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(description="Scenariusze Plant (raport HTML)")
    p.add_argument("scenarios", nargs="*", help="pliki albo nazwy z plant/scenarios")
    p.add_argument("--master", choices=("mock", "linuxcnc"), default=None,
                   help="domyślnie: mock (atrapa), a dla master: linuxcnc w scenariuszu — LinuxCNC")
    p.add_argument("--machine", type=Path, default=None, help="inna maszyna niż w scenariuszu")
    p.add_argument("--matrix", action="store_true",
                   help="matrix_smoke na każdej config/machines/*.yaml (REQ-QA-02)")
    p.add_argument("--out", type=Path, default=REPORTS, help="katalog raportów HTML")
    p.add_argument("--no-report", action="store_true", help="bez plików HTML")
    p.add_argument("--ssh", default=None, help="user@host VM: uruchom runner zdalnie")
    p.add_argument("--remote-dir", default="~/linumeRT", help="repozytorium na VM")
    p.add_argument("--print-ssh", action="store_true", help="tylko wypisz polecenie ssh")
    args = p.parse_args(argv)

    if args.ssh:
        cmd = ssh_command(args, argv)
        if args.print_ssh:
            print(" ".join(shlex.quote(c) for c in cmd))
            return 0
        return subprocess.run(cmd, check=False).returncode

    from linumert_plant import report
    from linumert_plant.scenario import ScenarioError, load_scenario, run_mock

    try:
        if args.matrix:
            base = SCENARIOS / "matrix_smoke.yaml"
            scenarios = [load_scenario(base, machine=m) for m in sorted(MACHINES.glob("*.yaml"))]
            for scen, m in zip(scenarios, sorted(MACHINES.glob("*.yaml")), strict=True):
                scen.name = f"matrix_smoke_{m.stem}"
        else:
            paths = [resolve(s) for s in args.scenarios] or sorted(SCENARIOS.glob("*.yaml"))
            paths = [x for x in paths if args.scenarios or x.stem != "matrix_smoke"]
            scenarios = [load_scenario(x, machine=args.machine) for x in paths]
            if not args.scenarios and args.master != "linuxcnc":
                # „Wszystkie” bez RIP: scenariusze `master: linuxcnc` (np. sondowanie G38) pomijamy
                only = [s.name for s in scenarios if s.master == "linuxcnc"]
                if only:
                    print(f"Pominięto scenariusze tylko-LinuxCNC (--master linuxcnc): "
                          f"{', '.join(only)}")
                    scenarios = [s for s in scenarios if s.master != "linuxcnc"]
    except (ScenarioError, FileNotFoundError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 2

    results = []
    for scen in scenarios:
        master = args.master or ("linuxcnc" if scen.master == "linuxcnc" else "mock")
        try:
            if master == "linuxcnc":
                from linumert_plant.scenario_linuxcnc import run_linuxcnc

                res = run_linuxcnc(scen)
            else:
                res = run_mock(scen)
        except ScenarioError as exc:
            print(f"{scen.name}: błąd scenariusza: {exc}", file=sys.stderr)
            return 2
        results.append(res)
        print(f"{'PASS' if res.passed else 'FAIL'}  {scen.name:32} {master:8} "
              f"{sum(c.passed for c in res.criteria)}/{len(res.criteria)} kryteriów")
        for c in res.criteria:
            if not c.passed:
                print(f"      ✗ {c.name}: {c.detail}")
    if not args.no_report and results:
        index = report.write(results, args.out)
        print(f"Raport: {index}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
