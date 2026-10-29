"""Dobór największego użytecznego przyspieszenia osi na Plant z budżetu uchybu nadążania.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-25 · M1 / decyzja właściciela „Plant — cel strojenia dynamiki”.

Bezwładność układu powoduje uchyb nadążania; to poprawna odpowiedź modelu, a nie błąd. Narzędzie
szuka największego `max_acceleration` osi, przy którym test ruchu (szybki przejazd tam i z
powrotem, bazowanie przed nim) kończy się bez alarmu napędu, bez zgubionych kroków i z uchybem osi
nie większym niż budżet. Wynik dotyczy **modelu Plant**, nie fizycznej maszyny:
NIEZWERYFIKOWANE NA SPRZĘCIE.

Metoda: ocena przy obecnym przyspieszeniu, potem podwajanie (albo połowienie) do znalezienia
przedziału [przechodzi, nie przechodzi], następnie bisekcja z tolerancją względną. Zakłada
monotoniczność (większe przyspieszenie = większy uchyb); zalecana wartość to `margin`
(domyślnie 0,9) największej przechodzącej, sprawdzona jeszcze raz przebiegiem kontrolnym.
LinuxCNC pozostaje jedynym planerem: narzędzie zmienia tylko `max_acceleration` osi
w kopii `machine.yaml`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

ROTARY = "ABC"


class TuningError(ValueError):
    """Niepoprawne dane wejściowe albo brak możliwości wykonania pomiaru."""


@dataclass
class Trial:
    accel: float
    passed: bool
    ferr_mm: float
    reason: str = ""


@dataclass
class AxisTuning:
    axis: str
    budget_mm: float
    configured: float
    best_pass: float = 0.0
    first_fail: float | None = None
    recommended: float = 0.0
    recommended_ferr_mm: float = 0.0
    capped: bool = False                  # górna granica poszukiwań osiągnięta bez porażki
    non_monotonic: bool = False           # porażka poniżej przechodzącego przyspieszenia (rezonans)
    trials: list[Trial] = field(default_factory=list)


Runner = Callable[[dict, str, float], Trial]


def axis_block(data: dict, letter: str) -> dict:
    for axis in data.get("axes", []):
        if axis.get("letter") == letter:
            return axis
    raise TuningError(f"brak osi {letter} w machine.yaml")


def build_program(axis: dict, distance: float | None = None) -> tuple[str, float, float]:
    """Program testowy: dojazd, przejazd tam i z powrotem; zwraca (G-code, odległość, prędkość)."""
    lo, hi = (float(v) for v in axis["soft_limits"])
    span = hi - lo
    dist = min(float(distance) if distance else 150.0, 0.6 * span)
    start = lo + 0.15 * span
    letter = axis["letter"]
    text = (f"G90\nG0 {letter}{start:.3f}\nG0 {letter}{start + dist:.3f}\n"
            f"G0 {letter}{start:.3f}\nM2\n")
    return text, dist, float(axis.get("max_velocity", 100.0))


def run_duration(dist: float, velocity: float, accel: float) -> float:
    move = dist / velocity + velocity / accel
    return 20.0 + 4.0 * move * 1.5 + 5.0


def run_plant(data: dict, letter: str, accel: float, budget: float,
              distance: float | None = None, substeps: int | None = None) -> Trial:
    """Jeden pomiar na atrapie mastera Plant (wymaga rdzenia C)."""
    from .scenario import DEFAULT_SUBSTEPS, Scenario, Step, run_mock

    trial = yaml.safe_load(yaml.safe_dump(data))
    axis = axis_block(trial, letter)
    axis["max_acceleration"] = accel
    program, dist, velocity = build_program(axis, distance)
    with tempfile.TemporaryDirectory(prefix="tune-accel-") as tmp:
        machine = Path(tmp) / "machine.yaml"
        program_path = Path(tmp) / "test.ngc"
        machine.write_text(yaml.safe_dump(trial, allow_unicode=True), encoding="utf-8")
        program_path.write_text(program, encoding="utf-8")
        scen = Scenario("tune_accel", None, machine, duration=run_duration(dist, velocity, accel),
                        substeps=substeps or DEFAULT_SUBSTEPS, program=program_path,
                        steps=[Step("enable", at=0), Step("home", at=0.01),
                               Step("program", at=0.1)])
        scen.expect = ([{"completed": True}, {"no_alarm": True}] +
                       [{"lost_steps": {"axis": a, "max": 0}} for a in "XYZ"])
        result = run_mock(scen)
    ferr = float(result.ferr_max.get(letter, 0.0))
    problems = [f"{c.name}: {c.detail}" for c in result.criteria if not c.passed]
    if ferr > budget:
        problems.append(f"uchyb {ferr:.4f} mm > budżet {budget} mm")
    return Trial(accel, not problems, ferr, "; ".join(problems))


def tune_axis(data: dict, letter: str, budget_mm: float, runner: Runner, *,
              max_factor: float = 32.0, margin: float = 0.9, tolerance: float = 0.05,
              max_trials: int = 24) -> AxisTuning:
    """Szuka największego przechodzącego przyspieszenia osi (pomiar: `runner`)."""
    if not (0.0 < budget_mm < 100.0):
        raise TuningError("budżet uchybu musi być w zakresie (0, 100) mm")
    if not (0.0 < margin <= 1.0) or tolerance <= 0.0 or max_factor <= 1.0:
        raise TuningError("margin w (0, 1], tolerancja > 0, max_factor > 1")
    configured = float(axis_block(data, letter).get("max_acceleration", 0.0))
    if configured <= 0.0:
        raise TuningError(f"oś {letter}: brak dodatniego max_acceleration")
    out = AxisTuning(letter, budget_mm, configured)

    def measure(accel: float) -> Trial:
        if len(out.trials) >= max_trials:
            raise TuningError(f"oś {letter}: przekroczono limit {max_trials} pomiarów")
        trial = runner(data, letter, accel)
        out.trials.append(trial)
        return trial

    passing = failing = None
    base = measure(configured)
    if base.passed:
        passing = configured
        accel = configured
        while accel < configured * max_factor:
            accel = min(accel * 2.0, configured * max_factor)
            if measure(accel).passed:
                passing = accel
            else:
                failing = accel
                break
        else:
            out.capped = failing is None
    else:
        failing = configured
        accel = configured
        for _ in range(8):
            accel /= 2.0
            if measure(accel).passed:
                passing = accel
                break
            failing = accel
    if passing is None:
        raise TuningError(f"oś {letter}: nawet {accel:.1f} mm/s² nie spełnia kryteriów "
                          f"({out.trials[-1].reason or 'brak powodu'})")
    while failing is not None and (failing - passing) / passing > tolerance:
        mid = 0.5 * (passing + failing)
        if measure(mid).passed:
            passing = mid
        else:
            failing = mid
    out.best_pass, out.first_fail = passing, failing
    target = max(round(passing * margin, -1), 10.0)
    holes = [t.accel for t in out.trials if not t.passed and t.accel < passing]
    if holes:                                    # krokowce: pasma rezonansu poniżej „najlepszego”
        target = min(target, max(round(0.9 * min(holes), -1), 10.0))
    floor = max(configured * 0.05, 10.0)
    while True:                          # zalecana i jej niższy sąsiad (−10 %) muszą przejść
        check = measure(target)
        neighbour = max(round(target * 0.9, -1), 10.0)
        if check.passed and measure(neighbour).passed:
            break
        if target <= floor:
            raise TuningError(f"oś {letter}: brak stabilnego przyspieszenia > {floor:.0f} mm/s²")
        target = neighbour
    out.recommended, out.recommended_ferr_mm = target, check.ferr_mm
    best_trial = max(t.accel for t in out.trials if t.passed)
    out.non_monotonic = any(not t.passed and t.accel < best_trial for t in out.trials)
    return out


def write_acceleration(path: Path, letter: str, value: float) -> bool:
    """Zmienia `max_acceleration` osi w pliku (zapis atomowy, komentarze zostają)."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines)
                  if re.match(rf"\s*-\s*letter:\s*{letter}\b", ln)), None)
    if start is None:
        raise TuningError(f"brak osi {letter} w {path}")
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"\s*-\s*letter:", lines[i]) or re.match(r"\S", lines[i])), len(lines))
    for i in range(start, end):
        match = re.match(r"(\s*max_acceleration:\s*)([0-9.]+)(.*)", lines[i], flags=re.S)
        if match:
            new = f"{value:g}"
            if match.group(2) == new:
                return False
            lines[i] = f"{match.group(1)}{new}{match.group(3)}"
            break
    else:
        raise TuningError(f"oś {letter}: brak linii max_acceleration")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.writelines(lines)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return True


def report_markdown(machine: Path, results: list[AxisTuning]) -> str:
    out = [f"# Dobór przyspieszeń — {machine.name}", "",
           "Model-Author: Claude. Wynik dla **modelu Plant** (atrapa mastera, lockstep); uchyb to",
           "odpowiedź bezwładności modelu, nie błąd. NIEZWERYFIKOWANE NA SPRZĘCIE.", "",
           "| Oś | Budżet uchybu [mm] | Obecne [mm/s²] | Największe przechodzące "
           "| Pierwsze niespełniające | Zalecane (zapas) | Uchyb przy zalecanym [mm] | Uwagi |",
           "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in results:
        fail = f"{r.first_fail:.0f}" if r.first_fail else ("brak do limitu" if r.capped else "—")
        note = ("niemonotoniczne: porażki poniżej przechodzącego (rezonans, utrata kroków) — "
                "zalecane poniżej najniższej porażki" if r.non_monotonic else "—")
        out.append(f"| {r.axis} | {r.budget_mm} | {r.configured:.0f} | {r.best_pass:.0f} | {fail} "
                   f"| **{r.recommended:.0f}** | {r.recommended_ferr_mm:.4f} | {note} |")
    out += ["", "## Pomiary", "", "| Oś | Przyspieszenie | Wynik | Uchyb [mm] | Powód |",
            "|---|---:|---|---:|---|"]
    for r in results:
        for t in r.trials:
            out.append(f"| {r.axis} | {t.accel:.0f} | {'PASS' if t.passed else 'FAIL'} "
                       f"| {t.ferr_mm:.4f} | {t.reason or '—'} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("machine", type=Path, help="machine.yaml (z czujnikami bazy do bazowania)")
    parser.add_argument("--axis", action="append", help="litera osi (domyślnie wszystkie liniowe)")
    parser.add_argument("--budget", type=float, default=0.2, help="budżet uchybu osi [mm]")
    parser.add_argument("--lag-factor", type=float, default=1.0,
                        help="o ile LinuxCNC zwiększa uchyb względem atrapy mastera (pomiar "
                             "docelowy: ok. 1,5); budżet pomiaru = budżet / współczynnik")
    parser.add_argument("--margin", type=float, default=0.9)
    parser.add_argument("--max-factor", type=float, default=32.0)
    parser.add_argument("--distance", type=float, help="odległość testowa [mm] (domyślnie 150)")
    parser.add_argument("--write", action="store_true", help="wpisz zalecane do machine.yaml")
    parser.add_argument("--out", type=Path, help="raport Markdown")
    parser.add_argument("--json", type=Path, help="wynik JSON")
    args = parser.parse_args(argv)
    if args.lag_factor < 1.0:
        print("błąd: --lag-factor musi być ≥ 1", file=sys.stderr)
        return 2
    try:
        data = yaml.safe_load(args.machine.read_text(encoding="utf-8"))
        letters = args.axis or [a["letter"] for a in data["axes"] if a["letter"] not in ROTARY]

        def runner(d: dict, letter: str, accel: float) -> Trial:
            trial = run_plant(d, letter, accel, args.budget / args.lag_factor, args.distance)
            print(f"  {letter} {accel:9.1f} mm/s²  {'PASS' if trial.passed else 'FAIL'}  "
                  f"uchyb {trial.ferr_mm:.4f} mm  {trial.reason}", flush=True)
            return trial

        results = []
        for letter in letters:
            print(f"oś {letter}:", flush=True)
            results.append(tune_axis(data, letter, args.budget, runner, margin=args.margin,
                                     max_factor=args.max_factor))
    except (OSError, KeyError, yaml.YAMLError, TuningError) as exc:
        print(f"błąd: {exc}", file=sys.stderr)
        return 2
    text = report_markdown(args.machine, results)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in results], indent=1), encoding="utf-8")
    if args.write:
        for r in results:
            changed = write_acceleration(args.machine, r.axis, r.recommended)
            state = "zapisano" if changed else "bez zmian"
            print(f"{r.axis}: max_acceleration = {r.recommended:g} ({state})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
