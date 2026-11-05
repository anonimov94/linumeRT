"""Offline, partial preflight of an immutable prepared job; never authorizes motion.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

The standalone interpreter's canonical text rounds coordinates to four decimals.
It can expose violations, but cannot establish the complete precision/material
contract. Even a clean run remains partial. No subset-interpreter fallback.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from linumert.machine.lite_config import render_lite
from linumert.machine.schema import MachineConfig
from linumert.tools.db import Tool

from . import job
from ._interpreter_process import InterpreterOutputLimit
from .limits import analyze_canon, number_lines
from .linuxcnc_check import InterpreterUnavailable, interpreter_result, run_interpreter
from .lnx import parse_lnx

FORMAT = "linumert.job.preflight"
CALL = re.compile(r"^\s*\d+ N[.\d]+\s+([A-Z0-9_]+)\(")
# Scope of the compiled 3-axis CAM job, not a general canonical-motion decoder.
KNOWN_CALLS = set("""
USE_LENGTH_UNITS SET_G5X_OFFSET SET_G92_OFFSET SET_XY_ROTATION SET_FEED_REFERENCE
ON_RESET COMMENT SET_FEED_MODE SET_FEED_RATE SELECT_PLANE USE_TOOL_LENGTH_OFFSET
STRAIGHT_TRAVERSE STRAIGHT_FEED ARC_FEED SELECT_TOOL START_CHANGE CHANGE_TOOL
SET_SPINDLE_SPEED SET_SPINDLE_MODE START_SPINDLE_CLOCKWISE START_SPINDLE_COUNTERCLOCKWISE
STOP_SPINDLE_TURNING FLOOD_ON FLOOD_OFF MIST_ON MIST_OFF DWELL PROGRAM_END
SET_MOTION_CONTROL_MODE SET_NAIVECAM_TOLERANCE STOP_CUTTER_RADIUS_COMPENSATION
""".split())


def _snapshot(path: Path, expected_job_id: str | None):
    manifest, files = job.read(path)
    if expected_job_id is not None and manifest["job_id"] != expected_job_id:
        raise ValueError("Identyfikator pakietu zmienił się od przygotowania")
    machine = MachineConfig.model_validate_json(files["machine.yaml"])
    # Recompile the supported prepared format before invoking rs274. Hashes alone
    # do not establish that a hand-crafted manifest contains generated CAM only.
    tools = [Tool(**row) for row in json.loads(files["tools.json"])]
    setup = json.loads(files["setup.json"])
    program = parse_lnx(json.loads(files["program.lnx"]))
    rendered = job.render(program, machine, json.loads(files["drives.json"]),
                          {t.number: t for t in tools}, tuple(setup["origin_mm"]),
                          setup["offset"], source_text=files["program.lnx"])
    if (any(rendered[name] != text for name, text in files.items())
            or json.loads(rendered["manifest.json"]) != manifest):
        raise ValueError("Zasoby nie odpowiadają przygotowaniu z zapisanych wejść")
    if (set(a.letter for a in machine.axes) != set("XYZ")
            or machine.toolchanger.type != "manual"):
        raise ValueError("Ta porcja kontroli wymaga maszyny XYZ z ręczną zmianą narzędzi")
    return manifest, files, machine, setup


def check(path: Path | str, start_mm: tuple[float, float, float], *,
          expected_job_id: str | None = None, root: Path | str | None = None,
          timeout: float = 20.0) -> dict:
    """Same snapshot for syntax, offsets, tools and trace-limit diagnostics.

    start_mm is the assumed machine position of the spindle nose before the
    program, with T0/G49 and G92 cleared. This is not a measurement from CNC.
    The synthetic N0 move initializes the *offline* interpreter, never a machine.
    """
    if (len(start_mm) != 3 or not all(not isinstance(v, bool) and math.isfinite(v)
                                    for v in start_mm)):
        raise ValueError("Pozycja początkowa wymaga trzech skończonych współrzędnych mm")
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError("Limit czasu kontroli musi mieścić się w (0, 60] s")
    path = Path(path)
    started = time.monotonic()
    manifest, files, machine, setup = _snapshot(path, expected_job_id)
    limits = {axis.letter: axis.soft_limits for axis in machine.axes}
    report = {"format": FORMAT, "version": 1, "job_id": manifest["job_id"],
              "status": "partial", "checks": {"integrity": "passed", "interpreter": "pending",
                 "motion_limits": "pending", "material": "pending", "execution": "not_started"},
              "assumptions": {"start_mm": list(start_mm), "tool_in_spindle": 0,
                              "g92_mm": [0, 0, 0], "measured_from_cnc": False,
                              "target": "offline_sim", "offset": setup},
              "messages": [], "violations": [], "canonical_trace": "",
              "limitations": ["Materiał, kolizje i obciążenia nie są jeszcze sprawdzane.",
                 "Ślad rs274 zaokrągla do 4 miejsc w jednostkach programu; "
                 "brak przekroczeń nie potwierdza pełnej kontroli limitów.",
                 "Założona pozycja początkowa i T0 wymagają osobnego powiązania z wykonaniem."]}
    for axis, value in zip("XYZ", start_mm, strict=True):
        lo, hi = limits[axis]
        if not lo <= value <= hi:
            report["messages"].append(f"Pozycja początkowa {axis}={value:g} mm "
                                      f"poza zakresem {lo:g}–{hi:g} mm")
    if report["messages"]:
        report["status"] = "rejected"
        report["checks"]["motion_limits"] = "failed"
    else:
        _interpret(report, files, machine, setup, start_mm, limits, root, timeout)
    # Re-read before publishing a result: a concurrently changed bundle must not
    # acquire a fresh positive integrity check, even if rs274 used private copies.
    current, _ = job.read(path)
    if current["job_id"] != manifest["job_id"]:
        raise ValueError("Pakiet zmienił się podczas kontroli")
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    report["report_id"] = job.digest(job.json_text(report).encode())
    return report


def _interpret(report, files, machine, setup, start, limits, root, timeout):
    try:
        with tempfile.TemporaryDirectory(prefix="linumert-job-check-") as temporary:
            stage = Path(temporary)
            for name, text in render_lite(machine, "sim").items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            (stage / "tool.tbl").write_text(files["tool.tbl"], encoding="utf-8")
            index = job.OFFSETS.index(setup["offset"]) + 1
            values = {5220: index, **{5221 + (index - 1) * 20 + i: v
                                     for i, v in enumerate(setup["origin_mm"])}}
            params = stage / "setup.var"
            params.write_text("".join(f"{k} {v:.17g}\n" for k, v in sorted(values.items())))
            program = stage / "program.ngc"
            seed = "N0 G21 G90 G49 G92.1\nN0 G53 G0 " + " ".join(
                f"{axis}{value:.17g}" for axis, value in zip("XYZ", start, strict=True)) + "\n"
            program.write_text(seed + number_lines(files["program.ngc"]), encoding="utf-8")
            run = run_interpreter(program, root, timeout, parameters_from=params,
                                  linear_units="mm",
                                  machine_ini=stage / f"{machine.machine.name}.ini")
        result = interpreter_result(run)
        report["canonical_trace"] = run.stdout
        report["interpreter"] = {"completed": result.completed, "returncode": run.returncode,
                                 "messages": result.messages}
        if not result.ok:
            report["status"] = "rejected"
            report["checks"]["interpreter"] = "failed"
            report["messages"].extend(result.messages or [
                "Interpreter nie doszedł do końca programu"])
            return
        report["checks"]["interpreter"] = "passed"
        unknown = sorted({m[1] for line in run.stdout.splitlines()
                          if (m := CALL.match(line)) and m[1] not in KNOWN_CALLS})
        if unknown:
            report["messages"].append("Nieobsługiwane wywołania śladu: " + ", ".join(unknown))
            return
        trace = analyze_canon(run.stdout, limits)
        report["violations"] = [asdict(v) for v in trace.violations]
        report["messages"].extend(v.message() for v in trace.violations)
        if trace.cuts_without_tlo:
            report["messages"].append("Ruch roboczy bez korekcji długości narzędzia")
        if trace.violations or trace.cuts_without_tlo:
            report["status"] = "rejected"
            report["checks"]["motion_limits"] = "failed"
        else:
            report["messages"].append("Interpreter zakończył program. W zaokrąglonym śladzie "
                                      "nie wykryto przekroczeń; pełna weryfikacja oczekuje.")
    except InterpreterUnavailable as exc:
        report["status"] = "unavailable"
        report["checks"]["interpreter"] = "unavailable"
        report["messages"].append(str(exc))
    except (subprocess.TimeoutExpired, InterpreterOutputLimit) as exc:
        report["status"] = "incomplete"
        report["checks"]["interpreter"] = "incomplete"
        report["messages"].append("Przekroczono czas interpretera" if isinstance(
            exc, subprocess.TimeoutExpired) else str(exc))


def save(report: dict, path: Path | str) -> None:
    """A separate exclusive report; the prepared bundle/manifest is never rewritten."""
    path = Path(path)
    text = job.json_text(report)
    fd, temporary = tempfile.mkstemp(prefix=".preflight-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as target:
            target.write(text)
            target.flush()
            os.fsync(target.fileno())
        if os.name == "nt":
            os.rename(temporary, path)  # Windows refuses an existing destination.
        else:
            os.link(temporary, path)  # Atomic publication, exclusive even across processes.
    finally:
        Path(temporary).unlink(missing_ok=True)
