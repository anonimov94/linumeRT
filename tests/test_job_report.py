"""Offline report validation against constructed telemetry, separate from CNC acceptance.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import shutil
from dataclasses import replace
from types import SimpleNamespace

import pytest
from linumert.cnc import AxisSnapshot, InterpState, MachineSnapshot, Mode, TaskState
from linumert.programs import job_execution, job_report
from linumert_webhmi import FakeBackend, Gateway, create_app
from linumert_webhmi.job_run import RunLog
from starlette.testclient import TestClient
from test_job_instance import configuration as configuration
from test_job_instance import package as package


@pytest.fixture
def recorded(configuration, tmp_path):
    identity, _ = job_execution.read(configuration)
    now = [0.0]
    log = RunLog(tmp_path / "instance", identity, clock=lambda: now[0])
    axes = tuple(AxisSnapshot(a, commanded=v, position=v + .0002)
                 for a, v in zip("XYZ", (200, 200, -5), strict=True))
    snap = MachineSnapshot(timestamp=0, axes=axes, task_state=TaskState.ON, mode=Mode.AUTO,
                           interp_state=InterpState.READING)
    live = dict(inpos=True, current_vel=0, task_done=True, motion_line=105)
    for i in range(4):
        now[0] = (i + 1) * .02
        log.sample(snap if i == 0 else replace(snap, interp_state=InterpState.IDLE), live, [])
    assert log.phase == "completed_observed"
    return log.path, configuration


def test_report_uses_raw_machine_values_and_exact_source_hashes(recorded):
    run, execution = recorded
    before = {p.name: p.read_bytes() for p in run.iterdir()}
    report = job_report.build(run, execution)
    assert report["status"] == "observational" and report["positioning"]["status"] == "passed"
    assert report["quality"]["samples"] == 4 and not report["quality"]["servo_trace"]
    assert report["axes"]["X"]["actual_minus_commanded"]["max_abs_mm"] == pytest.approx(.0002)
    assert report["axes"]["Z"]["following_error"]["rms_mm"] == pytest.approx(.0002)
    assert report["trajectory"][0]["axes"]["X"]["commanded"] == 200
    assert report["time"]["predicted_lower_bound_s"] is None
    assert report["time"]["elapsed_s"] == .08 and not report["hardware_qualification"]
    assert {p.name: p.read_bytes() for p in run.iterdir()} == before
    assert set(report["hashes"]) == {"manifest.json", "result.json", "samples.jsonl"}


@pytest.mark.parametrize("damage", ["truncated", "missing_result", "wrong_count", "gap",
                                    "old_completion", "unsettled"])
def test_incomplete_or_legacy_recording_cannot_pass_positioning(recorded, damage):
    run, execution = recorded
    result_path = run / "result.json"
    result = json.loads(result_path.read_text())
    path = run / "samples.jsonl"
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    if damage == "truncated":
        path.write_text(path.read_text() + '{"t":0.1,')
    elif damage == "missing_result":
        result_path.unlink()
    elif damage == "wrong_count":
        result["samples"] += 1
    elif damage == "old_completion":
        del result["settled_position_observed"]
    elif damage == "gap":
        rows[-2]["t"] = .3
        result["elapsed_s"] = .31
    else:
        rows[-2]["axes"]["Z"]["actual"] += .03
    if damage not in ("truncated", "missing_result"):
        result_path.write_text(json.dumps(result))
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    report = job_report.build(run, execution)
    assert report["positioning"]["status"] == "unavailable"
    if damage not in ("old_completion", "unsettled"):
        assert report["status"] == "incomplete"


def test_wrong_execution_identity_is_rejected(recorded):
    run, execution = recorded
    path = run / "manifest.json"
    data = json.loads(path.read_text())
    data["job_id"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="zadaniu"):
        job_report.build(run, execution)


def test_cli_and_authenticated_api_share_the_offline_report_without_commands(recorded, tmp_path):
    from linumert.cli import main

    run, execution = recorded
    target = tmp_path / "report.json"
    args = ["run-report", str(run), "--execution", str(execution), "--out", str(target)]
    assert main(args) == 0
    expected = json.loads(target.read_text())
    original = target.read_bytes()
    assert main(args) == 2 and target.read_bytes() == original
    gateway = Gateway(FakeBackend())
    before = gateway.backend.snapshot()
    shutil.copytree(execution, execution.parent / "evidence")
    gateway._instance = SimpleNamespace(root=execution.parent,
        run=SimpleNamespace(active=False, path=run))
    token = "report-test-token-123456"
    with TestClient(create_app(gateway, token), base_url="http://127.0.0.1:8765") as client:
        assert client.get("/api/execution/report").status_code == 401
        result = client.get("/api/execution/report", headers={"X-Linumert-Token": token})
        assert result.status_code == 200 and result.json() == expected
        gateway._instance.run.active = True
        assert client.get("/api/execution/report", headers={"X-Linumert-Token": token}
                          ).status_code == 409
    assert gateway.backend.snapshot() == before
