"""Offline assessment of sampled job telemetry; never imports or commands a controller.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import hashlib
import json
import math
from collections import deque
from pathlib import Path

from . import job, job_binding, job_execution

FORMAT = "linumert.job.run_report"
MAX_BYTES = 512 * 1024 * 1024
MAX_LINE = 1024 * 1024


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _json(data):
    def invalid(value):
        raise ValueError("Nieskończona wartość w zapisie przebiegu: " + value)
    return json.loads(data, parse_constant=invalid)


def build(run: Path, execution: Path) -> dict:
    """Bind immutable inputs and the exact consumed bytes; report gaps without inventing data."""
    run, execution = Path(run), Path(execution)
    frozen, files = job_execution.read(execution)
    manifest_bytes = (run / "manifest.json").read_bytes()
    manifest = _json(manifest_bytes)
    if (manifest.get("format") != "linumert.job.run" or manifest.get("version") != 1
            or manifest.get("source") != "linuxcnc.stat"):
        raise ValueError("Nieobsługiwane źródło przebiegu")
    keys = ("job_id", "execution_id", "verification_id", "target")
    if any(manifest.get(k) != frozen[k] for k in keys):
        raise ValueError("Przebieg nie odpowiada zamrożonemu zadaniu")
    issues = []
    result_bytes = (run / "result.json").read_bytes() if (run / "result.json").exists() else b""
    result = _json(result_bytes) if result_bytes else {}
    if result and (result.get("format") != manifest["format"]
                   or result.get("version") != 1 or result.get("source") != manifest["source"]):
        raise ValueError("Nieobsługiwany wynik przebiegu")
    if result and any(result.get(k) != manifest[k] for k in (*keys, "run_id")):
        raise ValueError("Wynik pochodzi z innego przebiegu")
    if not result:
        issues.append("Brak końcowego result.json")
    path = run / "samples.jsonl"
    before = path.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError("Zapis przebiegu przekracza limit512MiB")
    axes = [a["letter"] for a in _json(files["machine.yaml"])["axes"]]
    stats = {a: {k: [0.0, 0.0] for k in ("actual_minus_commanded", "following_error")}
             for a in axes}
    digest = hashlib.sha256()
    samples, last_t, gap, paused_s, stride = 0, None, 0.0, 0.0, 1
    trajectory, events, tail = [], [], deque(maxlen=3)
    previous = None
    last = None
    with path.open("rb") as stream:
        for line_number, raw in enumerate(iter(lambda: stream.readline(MAX_LINE + 1), b""), 1):
            digest.update(raw)
            if len(raw) > MAX_LINE:
                raise ValueError("Zbyt długa linia telemetrii")
            try:
                row = _json(raw)
                if not isinstance(row, dict) or not _number(row.get("t")) or row["t"] < 0:
                    raise ValueError("Nieprawidłowy czas")
                if "event" in row:
                    if len(events) < 10000:
                        events.append(row)
                    else:
                        raise ValueError("Zbyt wiele zdarzeń")
                    continue
                if set(row["axes"]) != set(axes):
                    raise ValueError("Niepełne osie")
                values = {a: row["axes"][a] for a in axes}
                if any(not _number(v.get(k)) for v in values.values()
                       for k in ("commanded", "actual", "following_error")):
                    raise ValueError("Niepełna pozycja")
                if last_t is not None:
                    dt = row["t"] - last_t
                    if dt <= 0:
                        raise ValueError("Czas nie rośnie")
                    gap = max(gap, dt)
                    if previous["interp"] == "paused":
                        paused_s += dt
                last_t, previous, last = row["t"], row, row
                samples += 1
                for a, v in values.items():
                    for key, value in (("actual_minus_commanded", v["actual"] - v["commanded"]),
                                       ("following_error", v["following_error"])):
                        stat = stats[a][key]
                        stat[0], stat[1] = max(stat[0], abs(value)), stat[1] + value * value
                tail.append(row)
                if (samples - 1) % stride == 0:
                    trajectory.append({"t": row["t"], "motion_line": row.get("motion_line"),
                                       "axes": values})
                    if len(trajectory) > 2000:
                        trajectory, stride = trajectory[::2], stride * 2
            except (ValueError, KeyError, TypeError) as error:
                issues.append(f"Linia{line_number}: {error}")
                if len(issues) > 100:
                    raise ValueError("Zbyt wiele uszkodzonych próbek") from None
    if not samples:
        issues.append("Brak poprawnych próbek pozycji")
    if result.get("samples") != samples:
        issues.append("Liczba próbek nie odpowiada wynikowi")
    if gap > .1:
        issues.append("Przerwa pomiędzy próbkami przekracza0,1s")
    if (run / "manifest.json").read_bytes() != manifest_bytes or (
            result_bytes and (run / "result.json").read_bytes() != result_bytes) or (
            path.stat().st_size != before.st_size or path.stat().st_mtime_ns != before.st_mtime_ns):
        raise ValueError("Przebieg zmienił się podczas odczytu")
    for values in stats.values():
        for key, (maximum, squares) in values.copy().items():
            values[key] = {"max_abs_mm": maximum if samples else None,
                           "rms_mm": math.sqrt(squares / samples) if samples else None}
    settled = (not issues and result.get("settled_position_observed") is True
        and result.get("status") in ("completed_observed", "aborted") and len(tail) == 3
        and all(r.get("task") == "on" and r.get("interp") == "idle"
                and r.get("inpos") is True and r.get("task_done") is True
                and _number(r.get("current_vel")) and abs(r["current_vel"]) < 1e-4
                and all(abs(v["actual"] - v["commanded"]) < .001
                        and abs(v["following_error"]) < .001 for v in r["axes"].values())
                and job_binding.same_context({a: r["axes"][a]["commanded"] for a in axes},
                    {a: tail[0]["axes"][a]["commanded"] for a in axes}) for r in tail))
    verification = _json(files["verification.json"])
    predicted = verification.get("material_diagnostic", {}).get("time_lower_bound_s")
    elapsed = result.get("elapsed_s")
    if not _number(elapsed) or last_t is None or elapsed < last_t:
        issues.append("Brak zgodnego końcowego czasu")
        elapsed = None
        settled = False
    if last and (not trajectory or trajectory[-1]["t"] != last["t"]):
        trajectory.append({"t": last["t"], "motion_line": last.get("motion_line"),
                           "axes": last["axes"]})
    report = {"format": FORMAT, "version": 1, **{k: manifest[k] for k in (*keys, "run_id")},
        "status": "incomplete" if issues else "observational", "execution_status": result.get(
            "status", "unavailable"), "source": manifest["source"],
        "quality": {"issues": issues, "samples": samples, "max_gap_s": gap, "servo_trace": False},
        "coordinates": "NML machine coordinates in mm; no alignment or interpolation",
        "time": {"basis": "monotonic elapsed seconds", "elapsed_s": elapsed,
                 "paused_observed_s": paused_s, "predicted_lower_bound_s": predicted,
                 "prediction_kind": "offline model lower bound, not a completion deadline"},
        "axes": stats, "weighting": "sample weighted; observed maxima only",
        "axis_error_definition": "following_error = commanded minus actual Cartesian position; "
                                 "raw joint ferror_current is not recorded",
        "positioning": {"status": "passed" if settled else "unavailable",
                        "scope": "last3 settled NML observations only", "tolerance_mm": .001},
        "trajectory": trajectory, "trajectory_stride": stride, "events": events,
        "alarms": result.get("alarms", []), "hardware_qualification": False,
        "hashes": {"manifest.json": job.digest(manifest_bytes), "result.json": job.digest(
            result_bytes) if result_bytes else None, "samples.jsonl": digest.hexdigest()}}
    report["report_id"] = job.digest(job.json_text(report).encode())
    return report
