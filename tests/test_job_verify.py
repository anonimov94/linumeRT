"""A verified offline verdict requires every diagnostic, never enables motion.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import copy

import pytest
from linumert.programs import job
from linumert_sim import job_verify


def base_report():
    return {"format": "linumert.job.preflight", "version": 1, "status": "partial",
        "job_id": "a" * 64, "report_id": "previous", "checks": {
            **dict.fromkeys(job_verify.REQUIRED, "passed"), "execution": "not_started"},
        "material_diagnostic": {"source": "linuxcnc.gcode"},
        "messages": [], "assumptions": {"measured_from_cnc": False},
        "limitations": ["Diagnostic model only"]}


def test_verification_is_fresh_and_distinct_from_execution(monkeypatch):
    report = base_report()
    seen = []
    def check(*args, **options):
        seen.append((args, options))
        return copy.deepcopy(report)
    monkeypatch.setattr(job_verify, "check", check)
    result = job_verify.verify("package", (20, 30, -5), expected_job_id="a" * 64)
    assert result["status"] == "verified" and result["format"] == job_verify.FORMAT
    assert result["verification"]["complete"] is True
    assert result["verification"]["execution_authorization"] is False
    assert result["checks"]["execution"] == "not_started"
    assert result["assumptions"] == report["assumptions"]
    assert result["limitations"] == report["limitations"]
    assert seen == [(("package", (20, 30, -5)), {"expected_job_id": "a" * 64})]
    assert result["report_id"] == job.digest(job.json_text({
        k: v for k, v in result.items() if k != "report_id"}).encode())


@pytest.mark.parametrize("key", job_verify.REQUIRED + ("execution", "new_check"))
def test_no_missing_pending_or_failed_check_can_be_promoted(monkeypatch, key):
    report = base_report()
    report["checks"][key] = "pending"
    monkeypatch.setattr(job_verify, "check", lambda *a, **k: copy.deepcopy(report))
    result = job_verify.verify("package", (20, 30, -5))
    assert result["status"] == "incomplete"
    assert not result["verification"]["complete"]
    assert not result["verification"]["execution_authorization"]


@pytest.mark.parametrize("status", ["rejected", "unavailable", "incomplete"])
def test_negative_interpreter_or_material_status_is_preserved(monkeypatch, status):
    report = base_report()
    report["status"] = status
    monkeypatch.setattr(job_verify, "check", lambda *a, **k: report)
    result = job_verify.verify("package", (20, 30, -5))
    assert result["status"] == status and not result["verification"]["complete"]
