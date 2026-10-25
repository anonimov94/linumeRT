# SPDX-License-Identifier: GPL-2.0-or-later
"""Sesja 033: układy G54–G59.3 i sondowanie Z/narożnika na LinuxCNC + Plant (wygenerowany).

Model-Author: Claude · 2026-10-25. Wymaga LinuxCNC RIP (marker `linuxcnc`). Oczekiwane wartości
sondowania pochodzą z geometrii celu sondy w `machine.yaml` (`probe.target`, `probe.tip_length`),
nie z wcześniejszego pomiaru. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

import pytest
import yaml
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
SYSTEMS = ("G54", "G55", "G56", "G57", "G58", "G59", "G59.1", "G59.2", "G59.3")
ROT_SYSTEM = 2                      # P2 = G55 dostaje obrót R90
TOL = 0.01
REPEAT_TOL = 0.002          # [mm] powtarzalność dwóch dokładnych przejazdów
ABS_TOL = 0.02              # [mm] błąd bezwzględny: luz modelu napędu 0,01 + sprężystość

DRIVER = r"""
SYSTEMS = ("G54", "G55", "G56", "G57", "G58", "G59", "G59.1", "G59.2", "G59.3")
out = {"on": on, "homed": homed, "systems": [], "probe": {}}
mdi("G21 G90 G49")
for n, name in enumerate(SYSTEMS, 1):
    off = (100.0 + 10 * n, 100.0 + 5 * n, -10.0 - 2 * n)
    rot = 90.0 if n == @ROT@ else 0.0
    mdi("G10 L2 P%d X%.3f Y%.3f Z%.3f R%.3f" % (n, *off, rot))
    mdi(name)
    s.poll()
    row = {"name": name, "index": s.g5x_index, "offset": list(s.g5x_offset[:3]),
           "rotation": s.rotation_xy}
    mdi("G90 G0 Z-5")                                   # bezpieczna wysokość przed ruchem XY
    mdi("G90 G0 X10 Y0")                                # w układzie detalu
    mdi("G90 G0 Z0")
    s.poll()
    row["actual"] = list(s.actual_position[:3])
    out["systems"].append(row)
mdi("G54 G10 L2 P1 X0 Y0 Z0 R0")
mdi("G54")
# --- sondowanie (układ detalu = maszyny) ---
def probe(axis, sign, dist):
    # dwustopniowo: szybkie F100, odjazd 2 mm, dokładne F10 dwa razy (powtarzalność)
    d = "" if sign > 0 else "-"
    back = "-" if sign > 0 else ""
    mdi("G91 G38.2 %s%s%d F100" % (axis, d, dist))
    mdi("G91 G1 %s%s2 F300" % (axis, back))
    fine, trips = [], []
    for _ in range(2):
        mdi("G91 G38.2 %s%s4 F10" % (axis, d))
        s.poll()
        fine.append(s.probed_position["XYZ".index(axis)]); trips.append(s.probe_tripped)
        mdi("G91 G1 %s%s2 F300" % (axis, back))
    mdi("G90")
    return fine, all(trips)
def at(label):
    s.poll(); out["probe"].setdefault("trace", []).append(
        [label] + [round(v, 3) for v in s.actual_position[:3]])
mdi("G53 G0 Z-5")
mdi("G53 G0 X300 Y400"); at("start-z")
out["probe"]["z"], out["probe"]["z_tripped"] = probe("Z", -1, 100)
mdi("G53 G0 Z-5"); mdi("G53 G0 X200 Y400")                # nad przygotówką, potem w dół obok niej
mdi("G53 G0 Z-40"); at("x-start")
out["probe"]["x"], out["probe"]["x_tripped"] = probe("X", +1, 100)
at("after-x")
mdi("G53 G0 Z-5"); mdi("G53 G0 X300 Y300")
mdi("G53 G0 Z-40"); at("y-start")
out["probe"]["y"], out["probe"]["y_tripped"] = probe("Y", +1, 100)
mdi("G53 G0 Z-5")
# sonda w powietrzu: G38.2 kończy się błędem, G38.3 (bez błędu) nie ustawia sygnału zadziałania
mdi("G53 G0 X100 Y100")
mdi("G38.3 X150 F100")
s.poll()
out["probe"]["air_tripped"] = s.probe_tripped
out["estop"] = s.estop
print("RESULT " + json.dumps(out))
"""


def _rot(x: float, y: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


# REQ-QA-02
@pytest.mark.linuxcnc
def test_work_offsets_g54_to_g593_and_probing_on_plant(tmp_path):
    driver = DRIVER.replace("@ROT@", str(ROT_SYSTEM))
    result, _, out_dir = run_generated_plant(tmp_path, MILL, driver,
                                             port=47852)
    assert result["on"] and result["homed"] and not result["estop"], result
    assert [r["name"] for r in result["systems"]] == list(SYSTEMS)
    for n, row in enumerate(result["systems"], 1):
        off = (100.0 + 10 * n, 100.0 + 5 * n, -10.0 - 2 * n)
        assert row["index"] == n, row
        assert row["offset"] == pytest.approx(off, abs=1e-6), row
        rot = 90.0 if n == ROT_SYSTEM else 0.0
        assert row["rotation"] == pytest.approx(rot), row
        dx, dy = _rot(10.0, 0.0, rot)            # ruch do X10 Y0 w układzie detalu, Z = zero detalu
        want = (off[0] + dx, off[1] + dy, off[2])
        assert row["actual"] == pytest.approx(want, abs=TOL), (row, want)

    # Geometria celu sondy z machine.yaml: górna ściana, ściana X min, ściana Y min.
    machine = yaml.safe_load(MILL.read_text(encoding="utf-8"))["probe"]
    lo, hi = machine["target"]["min"], machine["target"]["max"]
    tip = machine["tip_length"]
    probe = result["probe"]
    assert probe["z_tripped"] and probe["x_tripped"] and probe["y_tripped"], probe
    assert not probe["air_tripped"], probe
    expected = {"z": hi[2] + tip, "x": lo[0], "y": lo[1]}     # górna ściana, ściany X min, Y min
    errors = {k: [v - expected[k] for v in probe[k]] for k in expected}
    if os.environ.get("LINUMERT_PROBE_REPORT"):
        Path(os.environ["LINUMERT_PROBE_REPORT"]).write_text(
            json.dumps({"expected": expected, "probe": probe, "errors": errors}, indent=1))
    for axis, errs in errors.items():
        # Powtarzalność dokładnego przejazdu F10: kryterium ≤ 0,01 mm z zapasem.
        assert abs(probe[axis][0] - probe[axis][1]) <= REPEAT_TOL, (axis, probe)
        # Błąd bezwzględny: model napędu ma luz 10 µm (servo_*.yaml, mechanics.backlash) — odczyt
        # z enkodera silnika wyprzedza czubek sondy o luz i sprężystość (docs/user/SONDOWANIE.md).
        assert all(abs(e) <= ABS_TOL for e in errs), (axis, errs)

    # Parametry układów w pliku zmiennych (PARAMETER_FILE): odczyt po zamknięciu LinuxCNC.
    var = (out_dir / "linumert.var").read_text(encoding="utf-8")
    values = {int(k): float(v) for k, v in re.findall(r"^(\d+)\s+(\S+)$", var, flags=re.M)}
    for n in range(1, len(SYSTEMS) + 1):
        base = 5201 + 20 * n
        if base not in values:
            pytest.fail(f"brak parametru {base} (układ {SYSTEMS[n - 1]}) w pliku zmiennych")
        if n == 1:
            continue                         # G54 wrócił do zera na końcu testu
        assert values[base] == pytest.approx(100.0 + 10 * n, abs=1e-4), (n, values[base])
