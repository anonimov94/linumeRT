#!/usr/bin/env python3
"""Controlled Plant-only X-axis experiment; never sends LinuxCNC commands.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

The analytic reference is a diagnostic stimulus, not a G-code planner or a replay
of the failed LinuxCNC run. Ageing stored feedback changes only the observation,
not the drive controller or transport. Production configurations stay unchanged.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for directory in ("core", "plant/server"):
    sys.path.insert(0, str(ROOT / directory))

from linumert_plant.build_machine import build_machine  # noqa: E402
from linumert_plant.core_binding import PlantMachine  # noqa: E402

DT = 0.001
SUBSTEPS = 4
MACHINE = ROOT / "config/machines/mill_servo_table.yaml"


def reference(t):
    """20 mm out/back, 2000 mm/s², peak 200 mm/s, with stationary intervals."""
    def leg(u):
        if u <= 0:
            return 0.0
        if u < 0.1:
            return 1000.0 * u * u
        if u < 0.2:
            return 20.0 - 1000.0 * (0.2 - u) ** 2
        return 20.0

    return leg(t) - leg(t - 0.3)


def trial(mass, bandwidth=None, acceleration_ff=True, backlash=True):
    model = build_machine(MACHINE, seed=1, start="center")
    settings = dict(model.settings)
    settings["mech.0.load"] = mass
    if not backlash:
        settings["mech.0.backlash"] = 0.0
    inertia = (settings["mech.0.j_motor"] + settings["mech.0.j_screw"]
               + mass * settings["mech.0.ratio"] ** 2)
    if bandwidth is not None:
        # Same formula as lrt_drive_tune_servo(), within its 0.15/dt bound.
        assert bandwidth <= 0.15 / (DT / SUBSTEPS)
        settings.update({"drive.0.kv": inertia * bandwidth,
                         "drive.0.ti": 4.0 / bandwidth,
                         "drive.0.kp_pos": bandwidth / 5.0,
                         "drive.0.inertia_est": inertia})
    if not acceleration_ff:
        settings["drive.0.kff_acc"] = 0.0
    model.settings = list(settings.items())
    machine = PlantMachine(model)
    machine.enable_all(DT)
    origin = machine.drive_position("drv_x")
    encoder_origin = machine.position_actual("drv_x")
    scale = model.counts_per_unit["drv_x"]
    samples = []
    for index in range(1001):
        t = index * DT
        target = reference(t)
        machine.set_joint_target("X", origin + target)
        machine.step_cycle(DT, SUBSTEPS)
        samples.append({"t": t, "target_mm": target,
                        "motor_mm": (machine.position_actual("drv_x") - encoder_origin) / scale,
                        "load_mm": machine.drive_position("drv_x") - origin,
                        "torque_nm": machine.torque_actual("drv_x") * 0.001
                        * settings["drive.0.rated_torque"],
                        "fault": machine.drive_error_code("drv_x")})
        if samples[-1]["fault"]:
            break

    def stats(field):
        values = [s["target_mm"] - s[field] for s in samples]
        peak = max(range(len(values)), key=lambda i: abs(values[i]))
        return {"max_abs_mm": abs(values[peak]), "peak_t_s": samples[peak]["t"],
                "rms_mm": math.sqrt(math.fsum(v*v for v in values) / len(values)),
                "final_mm": values[-1]}

    aged = {}
    for age in (0, 1, 2, 4, 5, 8):
        errors = [s["target_mm"] - samples[max(0, i-age)]["motor_mm"]
                  for i, s in enumerate(samples)]
        aged[str(age)] = max(map(abs, errors))
    return {"mass_kg": mass, "tuned_bandwidth_rad_s": bandwidth,
            "backlash_m": settings["mech.0.backlash"],
            "acceleration_ff": acceleration_ff, "actual_inertia_kg_m2": inertia,
            "controller": {k.removeprefix("drive.0."): v for k, v in settings.items()
                           if k.startswith("drive.0.") and k.split(".")[-1] in
                           ("kp_pos", "kv", "ti", "inertia_est", "kff_vel", "kff_acc")},
            "inertia_torque_at_2000_mm_s2_nm": inertia * 2.0 / settings["mech.0.ratio"],
            "motor_error": stats("motor_mm"), "load_error": stats("load_mm"),
            "peak_torque_nm": max(abs(s["torque_nm"]) for s in samples),
            "fault": samples[-1]["fault"],
            "completed_reference": len(samples) == 1001 and not samples[-1]["fault"],
            "last_reference_t_s": samples[-1]["t"],
            "observation_age_ms_to_max_error_mm": aged, "samples": samples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    paths = [MACHINE, Path(__file__), ROOT / "plant/core/drive.c",
             ROOT / "plant/core/axis.c", ROOT / "plant/core/machine.c",
             ROOT / "core/linumert/machine/drives/templates/servo_400w.yaml"]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    runs = [trial(mass) for mass in (20.0, 80.0, 200.0, 400.0)]
    runs += [trial(mass, 150.0) for mass in (20.0, 80.0, 200.0, 400.0)]
    runs += [trial(80.0, 300.0), trial(80.0, acceleration_ff=False)]
    runs.append(trial(80.0, backlash=False))
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
               for p, h in hashes.items())
    report = {"model_author": "Codex", "runtime_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "method": "Plant C model, analytic X stimulus, no LinuxCNC or UDP; aged observation only",
        "limitations": ["Not a reproduction or explanation of CI X=0.8301 mm",
                        "No PID or configuration changes applied to production",
                        "NIEZWERYFIKOWANE NA SPRZĘCIE"],
        "dt_s": DT, "substeps": SUBSTEPS, "source_sha256": hashes, "trials": runs}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    args.out.write_bytes(gzip.compress(data, mtime=0) if args.out.suffix == ".gz" else data)
    for r in runs:
        print(f"mass={r['mass_kg']:g} bw={r['tuned_bandwidth_rad_s']} "
              f"FFa={r['acceleration_ff']} motor={r['motor_error']['max_abs_mm']:.6f} "
              f"load={r['load_error']['max_abs_mm']:.6f} "
              f"torque={r['peak_torque_nm']:.3f} fault={r['fault']}")


if __name__ == "__main__":
    main()
