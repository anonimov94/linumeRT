"""Offline phase comparison for a passive HAL trace; never runs LinuxCNC.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex. Residuals describe these samples, not a causal delay estimator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .scenario_trace import channels, inspect_trace


def analyze(work: Path, joint: int = 0) -> dict:
    meta_path, data_path = work / "servo_trace.json", work / "servo_trace.txt"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    columns = ["sample", *[c[0] for c in channels()]]
    integrity = inspect_trace(data_path)
    if (meta.get("valid") is not True or meta.get("columns") != columns
            or not integrity["continuous"] or meta.get("samples") != integrity["samples"]):
        raise ValueError("trace metadata/schema/integrity mismatch")
    names = {kind: f"j{joint}.{kind}" for kind in
             ("pos-cmd", "pos-fb", "f-error", "drive-enabled", "drive-ferror")}
    if any(name not in columns for name in names.values()):
        raise ValueError(f"joint {joint} is not recorded")
    raw = data_path.read_bytes()
    rows = [dict(zip(columns, map(float, line.split()), strict=True))
            for line in raw.decode("utf-8").splitlines()]
    # Skip the first two samples so all compared lags use the same population.
    active = [i for i in range(2, len(rows)) if rows[i][names["drive-enabled"]]
              and abs(rows[i][names["pos-cmd"]] - rows[i-1][names["pos-cmd"]]) > 1e-5]
    if not active:
        raise ValueError("no enabled moving samples for this joint")
    residuals = []
    for lag in (0, 1, 2):
        errors = [abs(rows[i][names["f-error"]] -
                      (rows[i-lag][names["pos-cmd"]] - rows[i-lag][names["pos-fb"]]))
                  for i in active]
        residuals.append({"lag_samples": lag, "max_abs_residual_mm": max(errors),
                          "mean_abs_residual_mm": sum(errors) / len(errors)})
    peak = max(active, key=lambda i: abs(rows[i][names["f-error"]]))
    return {"joint": joint, "samples": len(rows), "selected_samples": len(active),
            "selection": "drive-enabled and abs(delta pos-cmd) > 1e-5 mm; index >= 2",
            "trace_sha256": hashlib.sha256(raw).hexdigest(),
            "metadata_sha256": hashlib.sha256(meta_path.read_bytes()).hexdigest(),
            "residuals": residuals, "peak_row": rows[peak], "previous_row": rows[peak-1],
            "drive_ferror_max_abs_mm": max(abs(rows[i][names["drive-ferror"]]) for i in active),
            "limitations": ["residuals do not identify the cause of an unrecorded historical peak",
                            "HAL producer order remains; no Plant/NML clock alignment",
                            "sample numbers are not wall-clock timestamps"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="directory containing servo_trace.json and .txt")
    parser.add_argument("--joint", type=int, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        output = json.dumps(analyze(args.work, args.joint), ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
