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
    live["joint_following_errors"] = {"units": "mm", "values": [.00005, -.00008, .00009, .00011]}
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


def test_offline_report_reopens_after_original_data_are_unavailable(recorded, tmp_path):
    from linumert.programs.job import json_text

    run, execution = recorded
    report = job_report.build(run, execution)
    path = tmp_path / "portable.json"
    path.write_text(json_text(report))
    shutil.rmtree(run)
    shutil.rmtree(execution)
    assert job_report.load(path) == report


def test_historical_report_does_not_recompile_but_runtime_still_does(recorded, monkeypatch):
    def changed_generator(*args, **kwargs):
        raise ValueError("generator changed since recording")

    monkeypatch.setattr(job_execution, "render", changed_generator)
    report = job_report.build(*recorded)
    assert report["status"] == "observational"
    with pytest.raises(ValueError, match="generator changed"):
        job_execution.read(recorded[1])


def test_historical_report_still_rejects_changed_execution_bytes(recorded):
    run, execution = recorded
    (execution / "nc_files/program.ngc").write_text("G0 X999\nM2\n")
    with pytest.raises(ValueError, match="Zmieniony zasób"):
        job_report.build(run, execution)


@pytest.mark.parametrize("damage", ["checksum", "units", "ending", "missing", "nan"])
def test_saved_report_rejects_damage_and_unsubstantiated_pass(recorded, damage):
    from linumert.programs.job import digest, json_text

    run, execution = recorded
    report = job_report.build(run, execution)
    if damage == "units":
        report["units"]["position"] = "inch"
    elif damage == "ending":
        report["ending_samples"] = []
    elif damage == "missing":
        del report["trajectory"]
    elif damage == "nan":
        with pytest.raises(ValueError):
            job_report.load(b'{"bad": NaN}')
        return
    else:
        report["time"]["elapsed_s"] += 1
    if damage != "checksum":
        report["report_id"] = digest(json_text({k: v for k, v in report.items()
                                              if k != "report_id"}).encode())
    with pytest.raises(ValueError):
        job_report.load(json_text(report).encode())


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


@pytest.mark.parametrize("damage", ["negative", "rms", "missing_joint", "wrong_axis"])
def test_portable_joint_statistics_and_mapping_remain_consistent(recorded, damage):
    from linumert.programs.job import digest, json_text

    report = job_report.build(*recorded)
    raw = report["joint_following_error"]
    if damage == "negative":
        raw["joints"]["0"]["rms_mm"] = -.001
    elif damage == "rms":
        raw["joints"]["0"]["rms_mm"] = 1
    elif damage == "missing_joint":
        del raw["joints"]["2"]
    else:
        raw["joint_axes"]["2"] = "A"
    report["report_id"] = digest(json_text({k: v for k, v in report.items()
                                          if k != "report_id"}).encode())
    with pytest.raises(ValueError, match="niespójny"):
        job_report.load(json_text(report).encode())


def test_peak_and_alarm_keep_the_original_run_time_and_program_line(recorded):
    run, execution = recorded
    path = run / "samples.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    sample = next(r for r in rows if "axes" in r)
    sample.update(line=44, motion_line=17, errors=["test controller fault"])
    sample["axes"]["X"].update(actual=200.025, following_error=-.025)
    sample["alarms"] = [{"id": 7, "code": "E-1000", "text": "test alarm", "count": 1}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    report = job_report.build(run, execution)
    assert report["run_id"] == run.name
    peak = report["axes"]["X"]["following_error"]["peak"]
    assert peak == {"t": .02, "line": 44, "motion_line": 17, "value_mm": -.025}
    assert report["alarms"][0]["observed_at_s"] == .02
    assert report["alarms"][0]["motion_line"] == 17
    assert report["controller_errors"][0]["line"] == 44
    assert report["units"] == {"position": "mm", "time": "s"}
    assert report["verification"]["status"] == "verified"


@pytest.mark.parametrize("bad", [None, "value", "count"])
def test_raw_joint_following_error_is_independent_of_cartesian_poll_difference(recorded, bad):
    run, execution = recorded
    path = run / "samples.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    first = next(row for row in rows if "axes" in row)
    first["joint_following_errors"]["values"][1] = None if bad == "value" else .025
    if bad == "count":
        first["joint_following_errors"]["values"].pop()
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    report = job_report.build(run, execution)
    raw = report["joint_following_error"]
    if bad:
        assert raw["status"] == "incomplete" and report["status"] == "incomplete"
        assert report["positioning"]["status"] == "unavailable"
    else:
        assert raw["status"] == "available" and raw["samples"] == 4
        assert raw["joint_axes"] == {"0": "X", "1": "Y", "2": "Y", "3": "Z"}
        assert raw["joints"]["1"]["max_abs_mm"] == .025
        assert report["axes"]["Y"]["following_error"]["max_abs_mm"] < .001


def test_verified_terminal_claim_cannot_hide_an_observed_positioning_failure(recorded):
    run, execution = recorded
    path = run / "samples.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        if "axes" in row:
            row["axes"]["Z"].update(actual=-4.999, following_error=-.001)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    report = job_report.build(run, execution)
    assert report["positioning"]["status"] == "failed"


@pytest.mark.parametrize("damage", ["axis_type", "error_mismatch", "missing_start", "missing_end"])
def test_invalid_coordinates_and_missing_recording_edges_never_pass(recorded, damage):
    run, execution = recorded
    path = run / "samples.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    result_path = run / "result.json"
    result = json.loads(result_path.read_text())
    if damage == "missing_end":
        result["elapsed_s"] += .2
    else:
        for row in rows:
            if "axes" not in row:
                continue
            if damage == "axis_type":
                row["axes"]["X"] = []
            elif damage == "error_mismatch":
                row["axes"]["X"]["following_error"] = 0
            else:
                row["t"] += .2
        if damage == "missing_start":
            result["elapsed_s"] += .2
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    result_path.write_text(json.dumps(result))
    report = job_report.build(run, execution)
    assert report["status"] == "incomplete"
    assert report["positioning"]["status"] == "unavailable"


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


def test_report_only_gateway_preserves_raw_json_and_refuses_every_control_command(recorded):
    from linumert_webhmi.backend import ReportBackend

    run, execution = recorded
    report = job_report.build(run, execution)
    gateway = Gateway(ReportBackend(report))
    headers = {"X-Linumert-Token": "offline-report-test-token"}
    with TestClient(create_app(gateway, headers["X-Linumert-Token"]),
                    base_url="http://127.0.0.1:8765") as client:
        state = client.get("/api/state", headers=headers).json()["state"]
        assert state["read_only"] and not state["axes"] and not state["alarms"]
        assert "task_state" not in state and "mode" not in state
        for command in ("run", "resume", "home", "reset", "estop", "stop", "power_on", "mdi"):
            denied = client.post("/api/command", headers=headers, json={"cmd": command})
            assert denied.status_code == 409 and "offline" in denied.json()["detail"]
        raw = client.get("/api/execution/report", headers=headers)
        assert job_report.load(raw.content) == report
        assert client.post("/api/reports/open", content=raw.content).status_code == 401
        reopened = client.post("/api/reports/open", content=raw.content, headers=headers)
        assert reopened.status_code == 200 and job_report.load(reopened.content) == report
        assert client.post("/api/reports/open", content=b"{}", headers=headers).status_code == 422


def test_report_viewer_cli_never_constructs_a_controller(recorded, tmp_path, monkeypatch):
    import uvicorn
    from linumert.programs.job import json_text
    from linumert_webhmi import __main__ as entry

    run, execution = recorded
    path = tmp_path / "report.json"
    path.write_text(json_text(job_report.build(run, execution)))
    def refused(*args, **kwargs):
        pytest.fail("offline viewer constructed a controller")
    seen = []
    monkeypatch.setattr(entry, "LinuxCNCBackend", refused)
    monkeypatch.setattr(entry, "_demo_machine", refused)
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs:
                        seen.append(app.state.gateway.snapshot()[1]["read_only"]))
    assert entry.main(["--report", str(path)]) == 0 and seen == [True]
    assert entry.main(["--report", str(path), "--hal"]) == 2
