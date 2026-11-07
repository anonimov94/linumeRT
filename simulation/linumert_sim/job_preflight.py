"""Composition of core preflight and isolated diagnostic material processing.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from linumert.programs import job, job_check
from linumert.programs._interpreter_process import InterpreterOutputLimit, run_bounded


def check(path, start_mm, *, expected_job_id=None, root=None, timeout=20,
          trace_library=None, material_timeout=60):
    started = time.monotonic()
    report = job_check.check(path, start_mm, expected_job_id=expected_job_id,
                            root=root, timeout=timeout, trace_library=trace_library)
    if report["checks"]["motion_limits"] != "passed":
        return report
    if not 0 < material_timeout <= 60:
        raise ValueError("Limit diagnostyki materiału musi mieścić się w (0, 60] s")
    try:
        manifest, files = job.read(Path(path))
        if manifest["job_id"] != report["job_id"]:
            raise ValueError("Pakiet zmienił się przed diagnostyką materiału")
        with tempfile.TemporaryDirectory(prefix="linumert-job-material-") as temporary:
            source = Path(temporary) / "input.json"
            source.write_text(json.dumps({"files": files, "trace": report["precise_trace"],
                "start_mm": list(start_mm), "timeout": material_timeout}, allow_nan=False),
                encoding="utf-8")
            env = os.environ.copy()
            env.update(HOME=temporary, TMPDIR=temporary)
            run = run_bounded([sys.executable, "-P", "-m", "linumert_sim._job_material_worker",
                               str(source)], cwd=temporary, env=env, timeout=material_timeout)
        if run.returncode:
            raise ValueError("Diagnostyka materiału nieukończona: " + run.stderr[-1500:])
        result = json.loads(run.stdout)
        if result.get("format") != "linumert.job.material" or result.get("version") != 1:
            raise ValueError("Niekompletny wynik diagnostyki materiału")
        report["material_diagnostic"] = result
        failed = set()
        for event in result["events"]:
            if not event["stop"]:
                continue
            failed.add("loads" if event["kind"] == "overload" else
                       "collisions" if event["code"] in ("K-304", "K-305") else "material")
            report["messages"].append(f"linia {event['line']}, T{event['tool']}: {event['text']}")
        for key in ("material", "collisions", "loads"):
            report["checks"][key] = "failed" if key in failed else "passed"
        if failed:
            report["status"] = "rejected"
        else:
            report["messages"].append("Diagnostyka materiału, zadeklarowanych brył i obciążeń "
                                      "nie wykryła problemów w opisanym modelu.")
        pending = "Materiał, kolizje i obciążenia nie są jeszcze sprawdzane."
        report["limitations"] = [v for v in report["limitations"] if v != pending]
        report["limitations"].extend(result["limitations"])
        report["messages"] = [v.replace(" Materiał i kolizje oczekują.", "")
                              for v in report["messages"]]
    except (OSError, ValueError, KeyError, TypeError,
            subprocess.TimeoutExpired, InterpreterOutputLimit) as error:
        report["status"] = "incomplete"
        report["checks"].update(material="incomplete", collisions="incomplete", loads="incomplete")
        report["messages"].append(str(error))
    current, _ = job.read(Path(path))
    if current["job_id"] != report["job_id"]:
        raise ValueError("Pakiet zmienił się podczas diagnostyki materiału")
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    report.pop("report_id")
    report["report_id"] = job.digest(job.json_text(report).encode())
    return report
