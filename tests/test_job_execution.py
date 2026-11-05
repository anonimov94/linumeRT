"""Frozen execution inputs; no controller or implicit authorization.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import copy
import io
import json
import zipfile

import pytest
from job_support import write_inputs
from linumert.cnc import FakeMachine
from linumert.programs import job, job_execution, job_verification
from linumert.programs.job_check import save
from linumert.programs.prepare import JobService
from linumert_plant.build_machine import build_model
from linumert_webhmi import FakeBackend, Gateway, create_app
from starlette.testclient import TestClient
from test_job_material import complete_inputs


def report_fixture(manifest, setup):
    """Constructed contract fixture; actual interpreter acceptance is separate."""
    report = {"format": job_verification.FORMAT, "version": 1,
        "job_id": manifest["job_id"], "status": "verified",
        "checks": {**dict.fromkeys(job_verification.REQUIRED, "passed"),
                   "execution": "not_started"},
        "verification": {"kind": "offline_model", "model_version": 1, "complete": True,
            "execution_authorization": False, "checks_required": list(job_verification.REQUIRED)},
        "assumptions": {"start_mm": [200, 200, -5], "measured_from_cnc": False,
            "tool_in_spindle": 0, "g92_mm": [0, 0, 0], "offset": setup, "target": "offline_sim"}}
    return resign_report(report)


def resign_report(report):
    report = copy.deepcopy(report)
    report.pop("report_id", None)
    report["report_id"] = job.digest(job.json_text(report).encode())
    return report


@pytest.fixture
def package(tmp_path):
    files = job.render(*complete_inputs(), (200, 200, -80))
    path = job.publish(files, tmp_path / "job")
    manifest, data = job.read(path)
    return path, report_fixture(manifest, json.loads(data["setup.json"]))


@pytest.mark.parametrize("target", ["sim", "plant"])
def test_export_uses_frozen_drives_tools_offsets_and_program(
        package, tmp_path, monkeypatch, target):
    source, report = package
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    monkeypatch.setattr("linumert.machine.drives.machine_drives.load_library",
                        lambda *a, **k: pytest.fail("mutable drive library lookup"))
    files = job_execution.render(source, report, target)
    out = job_execution.publish(files, tmp_path / "execution")
    manifest, data = job_execution.read(out)
    assert manifest["status"] == "configured" and not manifest["execution_authorization"]
    assert manifest["verification_id"] == report["report_id"] and manifest["target"] == target
    assert "HMI_ESTOP_BYPASS = 0" in data[manifest["ini"]]
    assert data["nc_files/program.ngc"] == (source / "program.ngc").read_text()
    assert data["tool.tbl"] == (source / "tool.tbl").read_text()
    assert "5221 200\n" in data["linumert.var"] and "5223 -80\n" in data["linumert.var"]
    assert "job/program.lnx" in data and "verification.json" in data
    config = job_execution.MachineConfig.model_validate_json(data["machine.yaml"])
    library = {json.loads(text)["id"]: json.loads(text) for name, text in data.items()
               if name.startswith("drive_library/")}
    instances = job_execution.resolve_machine_drives(config, library)
    original = json.loads((source / "drives.json").read_text())
    for name, instance in instances.items():
        parameters = copy.deepcopy(instance.params)
        parameters["id"] = original[name]["parameters"]["id"]
        assert parameters == original[name]["parameters"]
    model = build_model(config, instances)
    assert manifest["joint_scales"] == model.counts_per_unit
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    with pytest.raises(FileExistsError):
        job_execution.publish(files, out)


@pytest.mark.parametrize("problem", ["partial", "missing_check", "different_job", "wrong_setup",
                                      "changed_hash", "authorized", "unmeasured_start"])
def test_execution_configuration_rejects_missing_or_wrong_verification(package, problem):
    source, report = package
    report = copy.deepcopy(report)
    if problem == "partial":
        report["status"] = "partial"
    elif problem == "missing_check":
        del report["checks"]["collisions"]
    elif problem == "different_job":
        report["job_id"] = "0" * 64
    elif problem == "wrong_setup":
        report["assumptions"]["offset"]["origin_mm"][0] = 500
    elif problem == "authorized":
        report["verification"]["execution_authorization"] = True
    elif problem == "unmeasured_start":
        report["assumptions"]["start_mm"] = [True, 200, -5]
    if problem != "changed_hash":
        report = resign_report(report)
    else:
        report["status"] = "partial"
    with pytest.raises(ValueError):
        job_execution.render(source, report, "plant")


def test_hardware_refused_bypass_explicit_and_port_bound(package):
    source, report = package
    with pytest.raises(ValueError, match="sim i plant"):
        job_execution.render(source, report, "hardware", test_mode=True)
    files = job_execution.render(source, report, "plant", test_mode=True, port=47883)
    metadata = json.loads(files["execution.json"])
    assert "HMI_ESTOP_BYPASS = 1" in files[metadata["ini"]]
    assert "PORT = 47883\n" in files[metadata["ini"]]
    assert metadata["launch"]["plant"][-1] == "47883"
    assert "127.0.0.1" in metadata["launch"]["plant"]


def test_resigned_foreign_hal_is_not_a_generated_configuration(package, tmp_path):
    source, report = package
    files = job_execution.render(source, report, "sim")
    out = job_execution.publish(files, tmp_path / "execution")
    resource = out / "linumert_sim.hal"
    resource.write_text(resource.read_text() + "# altered locally\n")
    metadata = json.loads((out / "execution.json").read_text())
    data = resource.read_bytes()
    metadata["resources"][resource.name] = {"sha256": job.digest(data), "bytes": len(data)}
    metadata.pop("execution_id")
    metadata["execution_id"] = job.digest(job.json_text(metadata).encode())
    (out / "execution.json").write_text(job.json_text(metadata))
    with pytest.raises(ValueError, match="nie odpowiada"):
        job_execution.read(out)


@pytest.mark.parametrize("name", ["../escape", "/tmp/escape", "a/../escape", "a\\escape"])
def test_no_resource_can_escape_publication(name, tmp_path):
    with pytest.raises(ValueError, match="ścieżka"):
        job_execution.publish({name: "bad"}, tmp_path / "execution")
    assert not (tmp_path / "execution").exists()


def test_api_export_is_bound_to_stored_verdict_and_never_changes_cnc(tmp_path):
    source, db, machine = write_inputs(tmp_path / "input")
    service = JobService(source.parent, machine, db, tmp_path / "jobs")
    prepared = service.prepare(source.name, "part", (200, 200, -80))
    report = report_fixture(prepared["manifest"], prepared["setup"])
    reports = service.jobs_dir / ".preflight"
    reports.mkdir()
    save(report, reports / f"{report['job_id']}-{report['report_id']}.json")
    token = "execution-config-api-test"
    headers = {"X-Linumert-Token": token}
    gateway = Gateway(FakeBackend(FakeMachine()))
    state, before = gateway.snapshot(), service.archive("part")
    client = TestClient(create_app(gateway, token, jobs=service), base_url="http://127.0.0.1")
    endpoint = "/api/jobs/part/execution-config"
    body = {"job_id": report["job_id"], "verification_id": report["report_id"], "target": "plant"}
    assert client.post(endpoint, json=body).status_code == 401
    assert client.post(endpoint, json=body, headers={**headers, "Host": "evil.test"}
                       ).status_code == 403
    for change in ({"target": "hardware"}, {"test_mode": True}, {"root": "/elsewhere"},
                   {"verification_id": "../other"}):
        assert client.post(endpoint, json={**body, **change}, headers=headers).status_code == 422
    response = client.post(endpoint, json=body, headers=headers)
    assert response.status_code == 200, response.text
    expected = job_execution.render(service.jobs_dir / "part", report, "plant")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert {name.removeprefix("part-plant/"): archive.read(name).decode()
                for name in archive.namelist()} == expected
    assert "HMI_ESTOP_BYPASS = 0" in next(
        text for name, text in expected.items() if name.endswith(".ini"))
    partial = copy.deepcopy(report)
    partial["status"] = "partial"
    partial = resign_report(partial)
    save(partial, reports / f"{partial['job_id']}-{partial['report_id']}.json")
    assert client.post(endpoint, json={**body, "verification_id": partial["report_id"]},
                       headers=headers).status_code == 409
    assert service.archive("part") == before and gateway.snapshot() == state
