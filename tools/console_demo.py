"""Replay actual Plant C telemetry in a terminal; no connection to hardware.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in ("core", "plant/server"):
    sys.path.insert(0, str(ROOT / directory))


def frame(result, index: int, *, width: int = 48, height: int = 6) -> str:
    """Render measured values; XY shows displacement from the first recorded sample."""
    telemetry = result.telemetry
    times, drives = telemetry["t"], telemetry["drives"]
    now = times[index]
    # Both supported scenarios enable the drives at t=0. Enable advances Plant time
    # during boot, while the scenario clock stays at zero. Alarm stamps use that clock.
    model_end = result.stats["frames"] * result.scenario.cycle_ns / 1e9
    startup = max(0, model_end - result.stats["time_s"])
    scenario_time = max(0, now - startup)
    rows = ["linumeRT lite | Plant C + master testowy | ODTWARZANIE",
            f"{result.scenario.name} | model: {now:.3f} s | scenariusz: {scenario_time:.3f} s",
            "", "NAPED        ZADANA      RZECZYW.      BLAD     PREDKOSC   MOMENT  ZGUBIONE",
            "                mm           mm         mm         mm/s       %"]
    rotary = {a["letter"] for a in result.machine_data.get("axes", [])
              if a.get("rotary", a.get("letter") in ("A", "B", "C"))}
    for name, data in drives.items():
        rows.append(f"{name:12.12} {data['cmd'][index]:10.4f} {data['act'][index]:12.4f} "
                    f"{data['ferr'][index]:10.5f} {data['vel'][index]:11.3f} "
                    f"{data['torque'][index] / 10:8.1f} {int(data['lost'][index]):8}")
    if rotary:
        rows.append("Osie obrotowe: pozycja/blad w stopniach, predkosc w stopniach/s.")
    xy = [result.axis_drives.get(axis, []) for axis in ("X", "Y")]
    if all(xy):
        x, y = [drives[names[0]]["act"] for names in xy]
        xmin, xmax, ymin, ymax = min(x), max(x), min(y), max(y)
        canvas = [[" " for _ in range(width)] for _ in range(height)]

        def point(i):
            col = round((x[i] - xmin) / max(xmax - xmin, 0.001) * (width - 1))
            row = height - 1 - round((y[i] - ymin) / max(ymax - ymin, 0.001) * (height - 1))
            return row, col

        for i in range(index + 1):
            row, col = point(i)
            canvas[row][col] = "."
        row, col = point(index)
        canvas[row][col] = "@"
        rows += ["", "SLAD XY: @ aktualna pozycja, . przebieg; osie skalowane osobno",
                 f"Zakres ruchu: X {xmax - xmin:.3f} mm | Y {ymax - ymin:.3f} mm",
                 "+" + "-" * width + "+"]
        rows += ["|" + "".join(row) + "|" for row in canvas]
        rows.append("+" + "-" * width + "+")
    alarms = [code for code, stamp in result.alarms.items() if stamp <= scenario_time]
    rows += ["", "ALARMY: " + (", ".join(alarms) or "brak"),
             "Dane symulowane; to nie jest odczyt rzeczywistej maszyny. Ctrl+C: koniec."]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("first_motion", "estop_mid_program"),
                        default="first_motion")
    parser.add_argument("--speed", type=float, default=1.0, help="tempo odtwarzania, > 0")
    parser.add_argument("--plain", action="store_true", help="bez animacji i kodow ANSI")
    args = parser.parse_args(argv)
    if not math.isfinite(args.speed) or args.speed <= 0:
        parser.error("--speed musi byc dodatnia, skonczona liczba")
    from linumert.machine.schema import MachineConfigError
    from linumert_plant.core_binding import PlantCoreUnavailable
    from linumert_plant.scenario import ScenarioError, load_scenario, run_mock

    try:
        print("Obliczanie scenariusza na rdzeniu Plant C...", flush=True)
        result = run_mock(load_scenario(ROOT / f"plant/scenarios/{args.scenario}.yaml"))
        times = result.telemetry["t"]
        if not times:
            raise ValueError("scenariusz nie zwrocil telemetrii")
        animated = sys.stdout.isatty() and not args.plain
        stride = max(1, round(0.1 * args.speed / max(times[1] - times[0], 0.001))) \
            if len(times) > 1 else 1
        indices = sorted({0, len(times) - 1, *range(0, len(times), stride)}) if animated else \
            sorted({0, len(times) // 2, len(times) - 1})
        previous = times[0]
        try:
            if animated:
                print("\033[?25l", end="", flush=True)
            for index in indices:
                if animated:
                    time.sleep(max(0, times[index] - previous) / args.speed)
                    print("\033[2J\033[H", end="")
                print(frame(result, index), flush=True)
                previous = times[index]
        finally:
            if animated:
                print("\033[?25h", end="", flush=True)
        print("\nWYNIK SCENARIUSZA: " + ("PASS" if result.passed else "FAIL"))
        for criterion in result.criteria:
            status = "PASS" if criterion.passed else "FAIL"
            print(f"  {status} {criterion.name}: {criterion.detail}")
        print("Maks. blad nadazania [mm]: " + str(result.ferr_max))
        return 0 if result.passed else 1
    except KeyboardInterrupt:
        return 130
    except (PlantCoreUnavailable, MachineConfigError, ScenarioError, OSError, ValueError) as exc:
        print(f"Blad: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
