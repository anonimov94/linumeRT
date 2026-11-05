"""Data contract shared by offline verification and simulation execution binding.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import math

from . import job

FORMAT = "linumert.job.verification"
REQUIRED = ("integrity", "interpreter", "motion_limits", "material", "collisions", "loads")


def validate(report: dict, job_id: str, setup: dict) -> None:
    """Accept a complete, unmodified offline verdict for this exact job only.

    This validates a stored result; it cannot authenticate arbitrary local files
    as a safety certificate or authorize execution on an unbound controller.
    """
    identity = dict(report)
    report_id = identity.pop("report_id", None)
    if report_id != job.digest(job.json_text(identity).encode()):
        raise ValueError("Niezgodna suma raportu weryfikacji")
    if (report.get("format") != FORMAT or type(report.get("version")) is not int
            or report.get("version") != 1
            or report.get("status") != "verified" or report.get("job_id") != job_id):
        raise ValueError("Wymagany raport verified dla tego pakietu")
    checks = report.get("checks", {})
    verdict = report.get("verification", {})
    if (any(checks.get(key) != "passed" for key in REQUIRED)
            or checks.get("execution") != "not_started"
            or any(v != "passed" for k, v in checks.items() if k != "execution")
            or verdict.get("kind") != "offline_model"
            or type(verdict.get("model_version")) is not int
            or verdict.get("model_version") != 1
            or verdict.get("complete") is not True
            or verdict.get("execution_authorization") is not False
            or verdict.get("checks_required") != list(REQUIRED)):
        raise ValueError("Niekompletne kontrole raportu verified")
    assumptions = report.get("assumptions", {})
    start = assumptions.get("start_mm", [])
    if (len(start) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float))
                               or not math.isfinite(v) for v in start)
            or assumptions.get("measured_from_cnc") is not False
            or type(assumptions.get("tool_in_spindle")) is not int
            or assumptions.get("tool_in_spindle") != 0
            or assumptions.get("g92_mm") != [0, 0, 0]
            or assumptions.get("target") != "offline_sim" or assumptions.get("offset") != setup):
        raise ValueError("Założenia raportu nie odpowiadają ustawieniu zadania")
