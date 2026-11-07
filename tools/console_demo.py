"""Replay actual Plant C telemetry in a terminal; no connection to hardware.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in ("core", "plant/server"):
    sys.path.insert(0, str(ROOT / directory))


def frame(result, index: int, *, width: int = 100, height: int = 32,
          scene=None, camera=None, mode: str = "braille", color: bool = False) -> str:
    """Compose telemetry, a real XYZ projection and optional orthogonal tiles."""
    from terminal3d import Camera, Scene

    if width < 70 or height < 20:
        return "Powieksz terminal do minimum 70 kolumn x 20 wierszy.\nQ: koniec"
    now = result.telemetry["t"][index]
    model_end = result.stats["frames"] * result.scenario.cycle_ns / 1e9
    startup = max(0, model_end - result.stats["time_s"])
    scenario_time = max(0, now - startup)
    camera = camera or Camera()
    rows = [f"linumeRT | ODTWARZANIE Plant C 3D | kamera {camera.yaw % 360:.0f}/"
            f"{camera.pitch:.0f} | zoom {camera.zoom:.1f}",
            f"{result.scenario.name} | model {now:.3f}s | scenariusz {scenario_time:.3f}s",
            "NAPED        ZADANA      RZECZYW.      BLAD     PREDKOSC   MOMENT  ZGUBIONE",
            "                mm           mm         mm         mm/s       %"]
    for name, data in result.telemetry["drives"].items():
        rows.append(f"{name:12.12} {data['cmd'][index]:10.4f} {data['act'][index]:12.4f} "
                    f"{data['ferr'][index]:10.5f} {data['vel'][index]:11.3f} "
                    f"{data['torque'][index] / 10:8.1f} {int(data['lost'][index]):8}")
    scene = scene or Scene(result)
    alarms = [code for code, stamp in result.alarms.items() if stamp <= scenario_time]
    footer = ["ALARMY: " + (", ".join(alarms) or "brak"),
              "@ narzedzie | cyjan: tor rzeczywisty | niebieski: zadany | siatka: obwiednia toru",
              "A/D obrot W/S nachylenie +/- zoom O orbit R reset SPACJA pauza Q koniec",
              "Symulacja, bez sprzetu. Koniec ruchu zatrzymuje odtwarzanie; kamera dziala dalej."]
    plot_rows = height - len(rows) - len(footer)
    picture = scene.render(index, width, plot_rows, camera, mode, color)
    return "\n".join([*(line[:width].ljust(width) for line in rows), *picture,
                       *(line[:width].ljust(width) for line in footer)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("first_motion", "estop_mid_program"),
                        default="first_motion")
    parser.add_argument("--speed", type=float, default=1.0, help="tempo odtwarzania, > 0")
    parser.add_argument("--plain", action="store_true", help="bez animacji i kodow ANSI")
    parser.add_argument("--raster", choices=("auto", "braille", "block", "ascii"), default="auto")
    parser.add_argument("--width", type=int, help="szerokosc w komorkach terminala")
    parser.add_argument("--height", type=int, help="wysokosc w wierszach terminala")
    parser.add_argument("--once", action="store_true", help="zakoncz po jednym odtworzeniu")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)
    if any(v is not None and v <= 0 for v in (args.width, args.height)):
        parser.error("--width i --height musza byc dodatnie")
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
        from bisect import bisect_right

        from terminal3d import Camera, Scene
        from terminal_keys import keyboard

        animated = sys.stdout.isatty() and not args.plain
        interactive = animated and sys.stdin.isatty()
        scene, camera = Scene(result), Camera()
        mode = args.raster
        if mode == "auto":
            try:
                "⣿".encode(sys.stdout.encoding or "utf-8")
                mode = "braille"
            except UnicodeEncodeError:
                mode = "ascii"

        def draw(index):
            try:
                size = os.get_terminal_size(sys.stdout.fileno())
            except (OSError, ValueError):
                size = shutil.get_terminal_size((110, 36))
            width = max(1, min(440, args.width or size.columns - 1))
            height = max(1, min(150, args.height or size.lines - 1))
            return frame(result, index, width=width, height=height, scene=scene,
                         camera=camera, mode=mode, color=animated and not args.no_color)

        try:
            if animated:
                print("\033[?1049h\033[?25l", end="", flush=True)
                position, paused, previous = times[0], False, time.monotonic()
                with keyboard(interactive) as read_key:
                    while True:
                        now = time.monotonic()
                        dt, previous = min(now - previous, 0.25), now
                        key = read_key()
                        if key == "q":
                            break
                        if key in (" ", "p"):
                            paused = not paused
                        camera.key(key)
                        if camera.orbit:
                            camera.yaw += dt * 14
                        if not paused:
                            position = min(times[-1], position + dt * args.speed)
                        index = min(len(times) - 1, max(0, bisect_right(times, position) - 1))
                        print("\033[H" + draw(index) + "\033[J", end="", flush=True)
                        if position >= times[-1] and (args.once or not interactive):
                            break
                        time.sleep(0.1)
            else:
                for index in sorted({0, len(times) // 2, len(times) - 1}):
                    print(draw(index), flush=True)
        finally:
            if animated:
                print("\033[?25h\033[?1049l", end="", flush=True)
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
