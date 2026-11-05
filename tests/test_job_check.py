"""Preflight remains partial, preserves packages, and fails closed on lost evidence.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import subprocess

import pytest
from job_support import inputs, write_inputs
from linumert.cli import main
from linumert.cnc import FakeMachine
from linumert.programs import job, job_check
from linumert.programs._interpreter_process import InterpreterOutputLimit
from linumert.programs.linuxcnc_check import InterpreterUnavailable
from linumert.programs.prepare import JobService
from linumert_webhmi import FakeBackend, Gateway, create_app
from starlette.testclient import TestClient

START = (50, 50, -5)
TOKEN = "job-preflight-test-token"
HEADERS = {"X-Linumert-Token": TOKEN}


@pytest.fixture(autouse=True)
def standalone_only(monkeypatch, tmp_path):
    """This module exercises the partial fallback independently of local builds."""
    monkeypatch.setenv("LINUMERT_TOOL_DATA_LIB", str(tmp_path / "not-built.so"))


def canon(*calls):
    return "\n".join(f"{i+1} N{i} {call}" for i, call in enumerate(calls)) + "\n"


GOOD = canon("USE_LENGTH_UNITS(CANON_UNITS_MM)",
             "STRAIGHT_TRAVERSE(50, 50, -5, 0, 0, 0)",
             "SET_G5X_OFFSET(1, 50, 50, -80, 0, 0, 0)",
             "USE_TOOL_LENGTH_OFFSET(0, 0, 40, 0, 0, 0)",
             "STRAIGHT_FEED(10, 10, -2, 0, 0, 0)", "PROGRAM_END()")


@pytest.fixture
def package(tmp_path):
    program, machine, drives, tools = inputs()
    path = tmp_path / "part"
    job.publish(job.render(program, machine, drives, tools, (50, 50, -80)), path)
    return path


def fake(monkeypatch, stdout=GOOD, stderr="", code=0):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, code, stdout, stderr)
    monkeypatch.setattr(job_check, "run_interpreter", run)


def test_same_snapshot_start_and_numbering_reach_isolated_interpreter(package, monkeypatch):
    before = {p.name: p.read_bytes() for p in package.iterdir()}
    seen = []

    def run(program, root, timeout, *, parameters_from, linear_units, machine_ini):
        assert program.read_text().startswith("N0 G21 G90 G49 G92.1\nN0 G53 G0 X50 Y50 Z-5\nN1 ")
        assert linear_units == "mm"
        assert "5221 50\n" in parameters_from.read_text()
        assert "5223 -80\n" in parameters_from.read_text()
        assert (machine_ini.parent / "tool.tbl").read_bytes() == before["tool.tbl"]
        assert "HMI_ESTOP_BYPASS = 0" in machine_ini.read_text()
        seen.append(machine_ini.parent)
        return subprocess.CompletedProcess([], 0, GOOD, "")

    monkeypatch.setattr(job_check, "run_interpreter", run)
    report = job_check.check(package, START)
    assert report["status"] == "partial"
    assert report["checks"] == {"integrity": "passed", "interpreter": "passed",
        "motion_limits": "pending", "material": "pending", "execution": "not_started"}
    assert report["assumptions"]["measured_from_cnc"] is False
    assert report["assumptions"]["tool_in_spindle"] == 0
    assert {p.name: p.read_bytes() for p in package.iterdir()} == before
    assert not seen[0].exists()
    identity = dict(report)
    assert identity.pop("report_id") == job.digest(job.json_text(identity).encode())


@pytest.mark.parametrize("stdout,stderr,code", [
    (GOOD, "bad semantic diagnostic\n", 0), (GOOD, "", 7),
    (GOOD.replace("PROGRAM_END()", "COMMENT(\"not finished\")"), "", 0),
    (GOOD.replace("PROGRAM_END()", "COMMENT(\"PROGRAM_END()\")"), "", 0),
])
def test_any_error_or_missing_end_rejects_even_an_otherwise_complete_trace(
        package, monkeypatch, stdout, stderr, code):
    fake(monkeypatch, stdout, stderr, code)
    report = job_check.check(package, START)
    assert report["status"] == "rejected" and report["checks"]["interpreter"] == "failed"
    assert report["checks"]["material"] == "pending"


@pytest.mark.parametrize("error,status", [(InterpreterUnavailable("no rs274"), "unavailable"),
    (subprocess.TimeoutExpired([], 1), "incomplete"),
    (InterpreterOutputLimit("limit danych"), "incomplete")])
def test_unavailable_timeout_and_output_limit_are_not_positive(package, monkeypatch, error, status):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(job_check, "run_interpreter", fail)
    report = job_check.check(package, START)
    assert report["status"] == status and report["checks"]["interpreter"] == status
    assert report["messages"] and report["checks"]["motion_limits"] == "pending"


def test_trace_violations_retain_source_line_and_unknown_calls_remain_partial(package, monkeypatch):
    fake(monkeypatch, GOOD.replace("STRAIGHT_FEED(10, 10, -2", "STRAIGHT_FEED(1000, 10, -2"))
    report = job_check.check(package, START)
    assert report["status"] == "rejected"
    assert [(v["line"], v["axis"], v["value"]) for v in report["violations"]] == [(4, "X", 1050)]
    fake(monkeypatch, GOOD + canon("RIGID_TAP(1, 2, 3)"))
    report = job_check.check(package, START)
    assert report["status"] == "partial" and report["checks"]["motion_limits"] == "pending"
    assert "RIGID_TAP" in report["messages"][0]


def test_resigned_gcode_is_rejected_before_interpreter(package, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("changed inputs reached interpreter")
    monkeypatch.setattr(job_check, "run_interpreter", forbidden)
    path = package / "program.ngc"
    path.write_text("M100\nM2\n")
    with pytest.raises(ValueError, match="Zmieniony zasób"):
        job_check.check(package, START)
    manifest = json.loads((package / "manifest.json").read_text())
    manifest["resources"][path.name] = {"sha256": job.digest(path.read_bytes()),
                                       "bytes": path.stat().st_size}
    manifest.pop("job_id")
    manifest["job_id"] = job.digest(job.json_text(manifest).encode())
    (package / "manifest.json").write_text(job.json_text(manifest))
    with pytest.raises(ValueError, match="zapisanych wejść"):
        job_check.check(package, START)


def test_changed_during_check_stale_identity_and_bad_start_do_not_pass(package, monkeypatch):
    fake(monkeypatch)
    with pytest.raises(ValueError, match="Identyfikator"):
        job_check.check(package, START, expected_job_id="0" * 64)
    for start in ((float("nan"), 50, -5), (True, 50, -5)):
        with pytest.raises(ValueError, match="skończonych"):
            job_check.check(package, start)
    assert job_check.check(package, (0, 50, -5))["status"] == "rejected"

    def mutate(*args, **kwargs):
        (package / "program.ngc").write_text("changed during check")
        return subprocess.CompletedProcess([], 0, GOOD, "")
    monkeypatch.setattr(job_check, "run_interpreter", mutate)
    with pytest.raises(ValueError, match="Zmieniony zasób"):
        job_check.check(package, START)


def test_cli_preserves_bundle_and_existing_report(package, monkeypatch, tmp_path, capsys):
    fake(monkeypatch)
    target = tmp_path / "preflight.json"
    args = ["preflight", str(package), "--start", "50", "50", "-5", "--out", str(target)]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "partial"
    before = target.read_bytes()
    assert main(args) == 2 and target.read_bytes() == before
    args[-1] = str(package / "extra.json")
    assert main(args) == 2 and not (package / "extra.json").exists()


def test_disagreement_between_interfaces_cannot_pass_limits(package, monkeypatch):
    fake(monkeypatch)
    monkeypatch.setattr(job_check.job_trace, "capture", lambda *a, **k: {
        "canonical": GOOD.replace("STRAIGHT_FEED(10, 10", "STRAIGHT_FEED(11, 10")})
    result = job_check.check(package, START)
    assert result["status"] == "incomplete"
    assert result["checks"]["interpreter"] == "passed"
    assert result["checks"]["motion_limits"] == "incomplete"
    assert "coordinate_resolution_mm" not in result


def test_api_auth_snapshot_report_storage_and_no_cnc_effect(tmp_path, monkeypatch):
    source, db, machine = write_inputs(tmp_path / "input")
    service = JobService(source.parent, machine, db, tmp_path / "jobs")
    prepared = service.prepare(source.name, "part", (50, 50, -80))
    gateway = Gateway(FakeBackend(FakeMachine()))
    client = TestClient(create_app(gateway, TOKEN, jobs=service), base_url="http://127.0.0.1")
    payload = {"job_id": prepared["manifest"]["job_id"], "start_mm": list(START)}
    endpoint = "/api/jobs/part/preflight"
    fake(monkeypatch)
    before = service.archive("part")
    state = gateway.snapshot()
    assert client.post(endpoint, json=payload).status_code == 401
    assert client.post(endpoint, json=payload, headers={**HEADERS, "Host": "evil.test"}
                       ).status_code == 403
    for change in ({"start_mm": [True, 50, -5]}, {"start_mm": ["NaN", 50, -5]},
                   {"start_mm": [50, 50]}, {"root": "/arbitrary"}, {"job_id": "../x"}):
        assert client.post(endpoint, json={**payload, **change}, headers=HEADERS).status_code == 422
    result = client.post(endpoint, json=payload, headers=HEADERS)
    assert result.status_code == 200, result.text
    report = result.json()
    assert report["status"] == "partial" and report["job_id"] == payload["job_id"]
    saved, = (service.jobs_dir / ".preflight").glob("*.json")
    assert json.loads(saved.read_text()) == report
    assert service.archive("part") == before and gateway.snapshot() == state
    assert client.post(endpoint, json={**payload, "job_id": "0" * 64}, headers=HEADERS
                       ).status_code == 409
    service._checking.acquire()
    try:
        assert client.post(endpoint, json=payload, headers=HEADERS).status_code == 409
    finally:
        service._checking.release()
