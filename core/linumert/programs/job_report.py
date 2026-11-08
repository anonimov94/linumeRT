"""Offline assessment of sampled job telemetry; never imports or commands a controller.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import hashlib
import json
import math
from collections import deque
from pathlib import Path

from linumert.machine.configgen import joint_drives
from linumert.machine.schema import MachineConfig

from . import job, job_binding, job_execution

FORMAT = "linumert.job.run_report"
MAX_BYTES = 512 * 1024 * 1024
MAX_LINE = 1024 * 1024
MAX_GAP_S = .1
MAX_REPORT_BYTES = 32 * 1024 * 1024
JOINT_ERROR_SOURCE = "linuxcnc.stat.joint.ferror_current"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _accumulate(stat, value, row):
    if stat[2] is None or abs(value) > stat[0]:
        stat[2] = {"t": row["t"], "line": row.get("line"),
                   "motion_line": row.get("motion_line"), "value_mm": value}
    stat[0], stat[1] = max(stat[0], abs(value)), stat[1] + value * value


def _metrics(stat, samples):
    maximum, squares, peak = stat
    return {"max_abs_mm": maximum if samples else None,
            "rms_mm": math.sqrt(squares / samples) if samples else None, "peak": peak}


def _json(data):
    def invalid(value):
        raise ValueError("Nieskończona wartość w zapisie przebiegu: " + value)
    return json.loads(data, parse_constant=invalid)


def _read(path, limit):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Plik raportu lub metadanych przekracza limit danych")
    return data


def _ending_ready(tail, axes):
    return len(tail) == 3 and all(
        r.get("task") == "on" and r.get("interp") == "idle"
        and r.get("inpos") is True and r.get("task_done") is True
        and _number(r.get("current_vel")) and abs(r["current_vel"]) < 1e-4
        and job_binding.same_context({a: r["axes"][a]["commanded"] for a in axes},
            {a: tail[0]["axes"][a]["commanded"] for a in axes}) for r in tail)


def _positions(values, axes):
    return (isinstance(values, dict) and set(values) == set(axes)
        and all(isinstance(v, dict)
            and all(_number(v.get(k)) for k in ("commanded", "actual", "following_error"))
            and abs(v["following_error"] - v["commanded"] + v["actual"]) <= 1e-6
            for v in values.values()))


def load(source):
    """Reopen a self-contained report, checking its checksum, shape and PASS evidence.

    No raw files are opened. Source hashes identify the earlier observations;
    this checksum verifies file consistency, not provenance or a digital signature.
    """
    data = source if isinstance(source, bytes) else _read(Path(source), MAX_REPORT_BYTES)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("Raport przekracza limit32MiB")
    report = _json(data)
    if not isinstance(report, dict):
        raise ValueError("Nieprawidłowy raport przebiegu")
    identity = {k: v for k, v in report.items() if k != "report_id"}
    if report.get("report_id") != job.digest(job.json_text(identity).encode()):
        raise ValueError("Niezgodna suma kontrolna raportu")

    def need(condition):
        if not condition:
            raise ValueError("Niepełny lub niespójny raport przebiegu")

    try:
        need(report["format"] == FORMAT and type(report["version"]) is int)
        need(report["version"] == 1 and report["source"] == "linuxcnc.stat")
        need(report["units"] == {"position": "mm", "time": "s"})
        for key, size in (("job_id", 64), ("execution_id", 64), ("verification_id", 64),
                          ("run_id", 32)):
            need(isinstance(report[key], str) and len(report[key]) == size)
            need(all(c in "0123456789abcdef" for c in report[key]))
        need(report["status"] in ("observational", "incomplete"))
        need(report["target"] in ("sim", "plant"))
        verification, timing = report["verification"], report["time"]
        need(verification["status"] == "verified" and isinstance(verification["checks"], dict))
        need(isinstance(verification["assumptions"], dict))
        for key in ("elapsed_s", "paused_observed_s", "unpaused_elapsed_s",
                    "predicted_lower_bound_s",
                    "excess_over_lower_bound_s", "excess_over_lower_bound_percent"):
            need(timing[key] is None or _number(timing[key]))
        need(type(timing["comparison_available"]) is bool)
        quality, axes = report["quality"], report["axes"]
        need(isinstance(quality["issues"], list) and all(
            isinstance(s, str) for s in quality["issues"]))
        need(quality["servo_trace"] is False and report["hardware_qualification"] is False)
        need(type(quality["samples"]) is int and quality["samples"] >= 0)
        need(_number(quality["max_gap_s"]) and quality["max_gap_s"] >= 0)
        need(set(axes) == set("XYZ"))
        for stats in axes.values():
            for key in ("following_error", "actual_minus_commanded"):
                for value in (stats[key]["max_abs_mm"], stats[key]["rms_mm"]):
                    need(value is None if not quality["samples"] else
                         _number(value) and value >= 0)
        need(isinstance(report["trajectory"], list) and len(report["trajectory"]) <= 2001)
        need(isinstance(report["ending_samples"], list) and len(report["ending_samples"]) <= 3)
        for row in report["trajectory"] + report["ending_samples"]:
            need(isinstance(row, dict) and _number(row["t"]) and row["t"] >= 0)
            need(_positions(row["axes"], axes))
        need(all(isinstance(report[key], list) for key in
                   ("events", "alarms", "controller_errors")))
        for alarm in report["alarms"] + report["controller_errors"]:
            need(isinstance(alarm, dict) and isinstance(alarm["text"], str))
            need(alarm.get("observed_at_s") is None or _number(alarm["observed_at_s"]))
        for event in report["events"]:
            need(isinstance(event, dict) and isinstance(event["event"], str)
                 and _number(event["t"]))
        need(report["positioning"]["status"] in ("passed", "failed", "unavailable"))
        if report["positioning"]["status"] == "passed":
            need(not quality["issues"] and report["status"] == "observational")
            need(quality["samples"] >= 3 and report["execution_status"] in (
                "completed_observed", "aborted"))
            need(_ending_ready(report["ending_samples"], axes))
            need(all(abs(v["actual"] - v["commanded"]) < .001
                       and abs(v["following_error"]) < .001
                       for row in report["ending_samples"] for v in row["axes"].values()))
            need(_number(report["time"]["elapsed_s"]))
        need(report["positioning"]["tolerance_mm"] == .001)
        joints = report.get("joint_following_error")
        if joints is not None:
            need(joints["source"] == JOINT_ERROR_SOURCE and joints["units"] == "mm")
            need(joints["status"] in ("available", "incomplete", "unavailable"))
            need(type(joints["samples"]) is int and 0 <= joints["samples"] <= quality["samples"])
            if joints["status"] == "available":
                need(0 < joints["samples"] == quality["samples"] and bool(joints["joints"]))
            for stat in joints["joints"].values():
                need(_number(stat["max_abs_mm"]) and _number(stat["rms_mm"]))
                need(0 <= stat["rms_mm"] <= stat["max_abs_mm"] + 1e-12)
            if "joint_axes" in joints:
                mapping = joints["joint_axes"]
                need(isinstance(mapping, dict) and bool(mapping))
                need(set(mapping) == {str(i) for i in range(len(mapping))})
                need(all(axis in axes for axis in mapping.values()))
                need(set(joints["joints"]) <= set(mapping))
                if joints["status"] == "available":
                    need(set(joints["joints"]) == set(mapping))
        last3 = report["positioning"]["last3_max_abs_mm"]
        need(isinstance(last3, dict))
        if len(report["ending_samples"]) == 3:
            need(set(last3) == set(axes))
            need(all(_number(last3[a]) and abs(last3[a] - max(abs(r["axes"][a]["actual"]
                - r["axes"][a]["commanded"]) for r in report["ending_samples"])) < 1e-6
                for a in axes))
    except (KeyError, TypeError, AttributeError):
        raise ValueError("Niepełny lub niespójny raport przebiegu") from None
    return report


def build(run: Path, execution: Path) -> dict:
    """Bind immutable inputs and the exact consumed bytes; report gaps without inventing data."""
    run, execution = Path(run), Path(execution)
    frozen, files = job_execution.read_evidence(execution)
    manifest_bytes = _read(run / "manifest.json", MAX_LINE)
    manifest = _json(manifest_bytes)
    if (not isinstance(manifest, dict) or manifest.get("format") != "linumert.job.run"
            or manifest.get("version") != 1
            or manifest.get("source") != "linuxcnc.stat"):
        raise ValueError("Nieobsługiwane źródło przebiegu")
    if (not isinstance(manifest.get("run_id"), str) or len(manifest["run_id"]) != 32
            or any(c not in "0123456789abcdef" for c in manifest["run_id"])):
        raise ValueError("Nieprawidłowy identyfikator przebiegu")
    keys = ("job_id", "execution_id", "verification_id", "target")
    if any(manifest.get(k) != frozen[k] for k in keys):
        raise ValueError("Przebieg nie odpowiada zamrożonemu zadaniu")
    issues = []
    result_bytes = _read(run / "result.json", MAX_LINE) if (run / "result.json").exists() else b""
    result = _json(result_bytes) if result_bytes else {}
    if not isinstance(result, dict):
        raise ValueError("Nieprawidłowy wynik przebiegu")
    if not isinstance(result.get("alarms", []), list) or any(
            not isinstance(a, dict) or type(a.get("id")) is not int
            for a in result.get("alarms", [])):
        raise ValueError("Nieprawidłowe alarmy wyniku")
    if result and (result.get("format") != manifest["format"]
                   or result.get("version") != 1 or result.get("source") != manifest["source"]):
        raise ValueError("Nieobsługiwany wynik przebiegu")
    if result and any(result.get(k) != manifest[k] for k in (*keys, "run_id")):
        raise ValueError("Wynik pochodzi z innego przebiegu")
    if not result:
        issues.append("Brak końcowego result.json")
    elif result.get("status") not in {"completed_observed", "aborted", "estop", "fault",
            "start_timeout", "resume_timeout", "settle_timeout", "unavailable", "client_lost"}:
        issues.append("Nieznany wynik zakończenia")
    path = run / "samples.jsonl"
    before = path.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError("Zapis przebiegu przekracza limit512MiB")
    machine = MachineConfig.model_validate(_json(files["machine.yaml"]))
    axes = [a.letter for a in machine.axes]
    joint_axes = {str(i): axis.letter for i, (axis, _) in enumerate(joint_drives(machine))}
    stats = {a: {k: [0.0, 0.0, None] for k in ("actual_minus_commanded", "following_error")}
             for a in axes}
    digest = hashlib.sha256()
    samples, last_t, gap, paused_s, stride = 0, None, 0.0, 0.0, 1
    trajectory, events, tail = [], [], deque(maxlen=3)
    previous = None
    last, first_t = None, None
    alarms, controller_errors = {}, {}
    joint_stats, joint_samples, joint_bad = {}, 0, 0
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
                    if not isinstance(row["event"], str):
                        raise ValueError("Nieprawidłowe zdarzenie")
                    if len(events) < 10000:
                        events.append(row)
                    else:
                        raise ValueError("Zbyt wiele zdarzeń")
                    continue
                if set(row["axes"]) != set(axes):
                    raise ValueError("Niepełne osie")
                values = {a: row["axes"][a] for a in axes}
                if any(not isinstance(v, dict) for v in values.values()) or any(
                       not _number(v.get(k)) for v in values.values()
                       for k in ("commanded", "actual", "following_error")):
                    raise ValueError("Niepełna pozycja")
                if any(abs(v["following_error"] - v["commanded"] + v["actual"]) > 1e-6
                       for v in values.values()):
                    raise ValueError("Błąd osi nie odpowiada współrzędnym NML")
                if row.get("interp") not in ("idle", "reading", "waiting", "paused"):
                    raise ValueError("Brak stanu interpretera")
                if (not isinstance(row.get("alarms", []), list)
                        or any(not isinstance(a, dict) or type(a.get("id")) is not int
                               for a in row.get("alarms", []))
                        or not isinstance(row.get("errors", []), list)
                        or any(not isinstance(e, str) for e in row.get("errors", []))):
                    raise ValueError("Nieprawidłowe alarmy")
                if last_t is not None:
                    dt = row["t"] - last_t
                    if dt <= 0:
                        raise ValueError("Czas nie rośnie")
                    gap = max(gap, dt)
                    if previous["interp"] == "paused":
                        paused_s += dt
                last_t, previous, last = row["t"], row, row
                if first_t is None:
                    first_t = last_t
                samples += 1
                joints = row.get("joint_following_errors")
                if joints is not None:
                    valid = (isinstance(joints, dict) and joints.get("units") == "mm"
                             and isinstance(joints.get("values"), list)
                             and len(joints["values"]) == len(joint_axes)
                             and all(_number(v) for v in joints["values"]))
                    if valid and (not joint_stats or len(joints["values"]) == len(joint_stats)):
                        if not joint_stats:
                            joint_stats = {str(i): [0.0, 0.0, None]
                                           for i in range(len(joints["values"]))}
                        joint_samples += 1
                        for i, value in enumerate(joints["values"]):
                            _accumulate(joint_stats[str(i)], value, row)
                    else:
                        joint_bad += 1
                for alarm in row.get("alarms", []):
                    alarms.setdefault(alarm["id"], {**alarm, "observed_at_s": row["t"],
                        "line": row.get("line"), "motion_line": row.get("motion_line")})
                for error in row.get("errors", []):
                    controller_errors.setdefault(error, {"text": error, "observed_at_s": row["t"],
                        "line": row.get("line"), "motion_line": row.get("motion_line")})
                if len(alarms) + len(controller_errors) > 10000:
                    raise ValueError("Zbyt wiele alarmów")
                for a, v in values.items():
                    for key, value in (("actual_minus_commanded", v["actual"] - v["commanded"]),
                                       ("following_error", v["following_error"])):
                        _accumulate(stats[a][key], value, row)
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
    joint_status = ("incomplete" if joint_bad or joint_samples and joint_samples != samples else
                    "available" if joint_samples else "unavailable")
    if (joint_status == "incomplete" or joint_status == "unavailable"
            and manifest.get("joint_error_source") == JOINT_ERROR_SOURCE):
        issues.append("Brak kompletnego zapisu surowego błędu nadążania przegubów")
    if type(result.get("samples")) is not int or result["samples"] != samples:
        issues.append("Liczba próbek nie odpowiada wynikowi")
    for alarm in result.get("alarms", []):
        if alarm["id"] not in alarms:
            issues.append("Alarm wyniku bez odpowiadającej próbki")
            alarms[alarm["id"]] = {**alarm, "line": None, "motion_line": None}
    if gap > MAX_GAP_S:
        issues.append("Przerwa pomiędzy próbkami przekracza0,1s")
    if first_t is not None and first_t > MAX_GAP_S:
        issues.append("Brak początkowych próbek przebiegu")
    if (run / "manifest.json").read_bytes() != manifest_bytes or (
            result_bytes and (run / "result.json").read_bytes() != result_bytes) or (
            path.stat().st_size != before.st_size or path.stat().st_mtime_ns != before.st_mtime_ns):
        raise ValueError("Przebieg zmienił się podczas odczytu")
    for values in stats.values():
        for key, stat in values.copy().items():
            values[key] = _metrics(stat, samples)
    ending_ready = _ending_ready(tail, axes)
    settled = (not issues and ending_ready and result.get("settled_position_observed") is True
        and result.get("status") in ("completed_observed", "aborted")
        and all(abs(v["actual"] - v["commanded"]) < .001 and abs(v["following_error"]) < .001
                for r in tail for v in r["axes"].values()))
    verification = _json(files["verification.json"])
    predicted = verification.get("material_diagnostic", {}).get("time_lower_bound_s")
    elapsed = result.get("elapsed_s")
    if not _number(elapsed) or last_t is None or elapsed < last_t:
        issues.append("Brak zgodnego końcowego czasu")
        elapsed = None
        settled = False
    elif elapsed - last_t > MAX_GAP_S:
        issues.append("Brak końcowych próbek przebiegu")
        settled = False
    unpaused = max(0, elapsed - paused_s) if elapsed is not None else None
    comparable = (not issues and result.get("status") == "completed_observed"
                  and _number(predicted) and predicted > 0 and unpaused is not None)
    excess = unpaused - predicted if comparable else None
    if last and (not trajectory or trajectory[-1]["t"] != last["t"]):
        trajectory.append({"t": last["t"], "motion_line": last.get("motion_line"),
                           "axes": last["axes"]})
    positioning = ("passed" if settled else "failed" if not issues and ending_ready
                   and result.get("settled_position_observed") is True else "unavailable")
    report = {"format": FORMAT, "version": 1, **{k: manifest[k] for k in (*keys, "run_id")},
        "status": "incomplete" if issues else "observational", "execution_status": result.get(
            "status", "unavailable"), "source": manifest["source"],
        "quality": {"issues": issues, "samples": samples, "max_gap_s": gap, "servo_trace": False,
                    "first_sample_s": first_t, "last_sample_s": last_t},
        "verification": {"status": verification["status"], "checks": verification["checks"],
                         "assumptions": verification["assumptions"]},
        "execution_resources": frozen["resources"],
        "units": {"position": "mm", "time": "s"},
        "coordinates": "NML machine coordinates in mm; no alignment or interpolation",
        "time": {"basis": "monotonic elapsed seconds", "elapsed_s": elapsed,
                 "paused_observed_s": paused_s, "predicted_lower_bound_s": predicted,
                 "unpaused_elapsed_s": unpaused, "comparison_available": comparable,
                 "excess_over_lower_bound_s": excess,
                 "excess_over_lower_bound_percent":
                     excess / predicted * 100 if comparable else None,
                 "prediction_kind": "offline model lower bound, not a completion deadline"},
        "axes": stats, "weighting": "sample weighted; observed maxima only",
        "joint_following_error": {"status": joint_status, "source": JOINT_ERROR_SOURCE,
            "units": "mm", "samples": joint_samples, "joint_axes": joint_axes,
            "joints": {i: _metrics(s, joint_samples) for i, s in joint_stats.items()},
            "last3_max_abs_mm": {i: max(abs(r["joint_following_errors"]["values"][int(i)])
                for r in tail) for i in joint_stats} if joint_status == "available"
                and len(tail) == 3 else {}},
        "axis_error_definition": "following_error = commanded minus actual Cartesian position; "
                                 "raw joint ferror_current is reported separately in "
                                 "joint_following_error when available",
        "positioning": {"status": positioning,
                        "scope": "last3 settled NML observations only", "tolerance_mm": .001,
                        "last3_max_abs_mm": {a: max(abs(r["axes"][a]["actual"]
                            - r["axes"][a]["commanded"]) for r in tail) for a in axes}
                            if len(tail) == 3 else {}},
        "ending_samples": list(tail),
        "trajectory": trajectory, "trajectory_stride": stride, "events": events,
        "alarms": list(alarms.values()), "controller_errors": list(controller_errors.values()),
        "hardware_qualification": False,
        "hashes": {"manifest.json": job.digest(manifest_bytes), "result.json": job.digest(
            result_bytes) if result_bytes else None, "samples.jsonl": digest.hexdigest()}}
    report["report_id"] = job.digest(job.json_text(report).encode())
    return report
