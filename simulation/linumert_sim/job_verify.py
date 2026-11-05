"""Complete offline job verdict, separate from authorization to execute.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from linumert.programs import job

from .job_preflight import check

FORMAT = "linumert.job.verification"
REQUIRED = ("integrity", "interpreter", "motion_limits", "material", "collisions", "loads")


def verify(path, start_mm, **options):
    """Verify the supported offline model under the recorded start assumptions.

    Re-run the authoritative pipeline rather than promoting a client-supplied or
    old saved report. Execution must independently bind the live machine state,
    tools, configuration and immutable job; this function never commands CNC.
    """
    report = check(path, start_mm, **options)
    checks = report["checks"]
    complete = (report["status"] == "partial"
                and all(checks.get(key) == "passed" for key in REQUIRED)
                and checks.get("execution") == "not_started"
                and all(value == "passed" for key, value in checks.items() if key != "execution")
                and report.get("material_diagnostic", {}).get("source") == "linuxcnc.gcode")
    if complete:
        report["status"] = "verified"
        report["messages"].append("Zadanie zweryfikowane offline w opisanym modelu. "
            "Przed startem wymagane powiązanie pakietu, konfiguracji, narzędzi i początku "
            "z rzeczywistą instancją LinuxCNC sim/Plant.")
    elif report["status"] == "partial":
        report["status"] = "incomplete"
        report["messages"].append("Brak kompletu dodatnich kontroli; "
                                  "zadanie nie jest zweryfikowane.")
    report["format"] = FORMAT
    report["verification"] = {"kind": "offline_model", "model_version": 1,
        "checks_required": list(REQUIRED), "complete": complete,
        "execution_authorization": False}
    report.pop("report_id")
    report["report_id"] = job.digest(job.json_text(report).encode())
    return report
