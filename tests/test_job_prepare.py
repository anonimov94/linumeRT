"""CLI and WebHMI share preparation without changing inputs or machine state.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import io
import json
import zipfile

import pytest
from job_support import write_inputs
from linumert.cnc import FakeMachine
from linumert.programs.prepare import JobService, main
from linumert.tools.db import ToolDB
from linumert_webhmi import FakeBackend, Gateway, create_app
from starlette.testclient import TestClient

TOKEN = "job-preparation-test-token"
HEADERS = {"X-Linumert-Token": TOKEN}
PAYLOAD = {"program": "detal.lnx", "name": "detal-001",
           "origin": [50, 50, -80], "offset": "G54"}


@pytest.fixture
def setup(tmp_path):
    source, db, machine = write_inputs(tmp_path / "inputs")
    service = JobService(source.parent, machine, db, tmp_path / "jobs")
    gateway = Gateway(FakeBackend(FakeMachine()))
    client = TestClient(create_app(gateway, TOKEN, jobs=service), base_url="http://127.0.0.1")
    return service, client, source, db, machine, gateway


def test_cli_and_webhmi_produce_identical_bundles_preserving_inputs(setup, tmp_path, capsys):
    service, client, source, db, machine, gateway = setup
    # Preserve the original byte representation, including CRLF and noncanonical indentation.
    source.write_bytes(json.dumps(json.loads(source.read_text()), ensure_ascii=False,
                                 indent=4).replace("\n", "\r\n").encode())
    before = {p: p.read_bytes() for p in (source, db, machine)}
    state = gateway.snapshot()
    with ToolDB(db, readonly=True) as database:
        history = database.history()
    context = client.get("/api/jobs/context", headers=HEADERS).json()
    assert context["available"] and context["programs"] == [source.name]
    response = client.post("/api/jobs/prepare", headers=HEADERS, json=PAYLOAD)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["report"]["status"] == "prepared"
    assert result["report"]["checks"]["interpreter"] == "pending"
    assert result["setup"]["origin_mm"] == [50, 50, -80]
    assert gateway.snapshot() == state  # No reset, enable, mode or motion side effects.
    assert main([str(source), "--machine", str(machine), "--tools", str(db),
                 "--out", str(tmp_path / "cli"), "--origin", "50", "50", "-80"]) == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli["job_id"] == result["manifest"]["job_id"]
    assert (tmp_path / "cli/program.lnx").read_bytes() == before[source]
    assert {p: p.read_bytes() for p in before} == before
    with ToolDB(db, readonly=True) as database:
        assert database.history() == history
    archive = client.get("/api/jobs/detal-001/archive", headers=HEADERS)
    assert archive.status_code == 200 and archive.headers["content-type"] == "application/zip"
    assert archive.content == service.archive("detal-001")
    with zipfile.ZipFile(io.BytesIO(archive.content)) as contents:
        assert len(contents.namelist()) == 9
        assert contents.read("detal-001/program.lnx") == before[source]
    assert client.post("/api/jobs/prepare", headers=HEADERS, json=PAYLOAD).status_code == 409
    assert service.describe("detal-001")["manifest"] == result["manifest"]


@pytest.mark.parametrize("change", [
    {"program": "../detal.lnx"}, {"program": "detal.ngc"}, {"name": "../outside"},
    {"origin": [0, 1]}, {"origin": [True, 0, 0]}, {"origin": ["NaN", 0, 0]},
    {"offset": "G92"}, {"machine": "/tmp/arbitrary.yaml"},
])
def test_invalid_api_inputs_publish_nothing(setup, change):
    service, client, *_ = setup
    response = client.post("/api/jobs/prepare", headers=HEADERS, json={**PAYLOAD, **change})
    assert response.status_code in (409, 422), response.text
    assert not service.jobs_dir.exists()


def test_authentication_host_missing_config_and_changed_export(setup):
    service, client, *_ = setup
    for method, path, kwargs in (("GET", "/api/jobs/context", {}),
                                 ("POST", "/api/jobs/prepare", {"json": PAYLOAD}),
                                 ("GET", "/api/jobs/detal-001/archive", {})):
        assert client.request(method, path, **kwargs).status_code == 401
        assert client.request(method, path, headers={**HEADERS, "Host": "evil.example"},
                              **kwargs).status_code == 403
    assert client.post("/api/jobs/prepare", headers=HEADERS, json=PAYLOAD).status_code == 200
    (service.jobs_dir / "detal-001/program.ngc").write_text("G0 X99999")
    response = client.get("/api/jobs/detal-001/archive", headers=HEADERS)
    assert response.status_code == 409 and "Zmieniony zasób" in response.json()["detail"]
    off = TestClient(create_app(Gateway(FakeBackend(FakeMachine())), TOKEN),
                     base_url="http://localhost")
    assert off.get("/api/jobs/context", headers=HEADERS).json()["available"] is False
    assert off.post("/api/jobs/prepare", headers=HEADERS, json=PAYLOAD).status_code == 409


def test_broken_machine_and_missing_database_never_create_output(setup, tmp_path):
    service, client, source, db, machine, _ = setup
    bad = tmp_path / "bad-machine.yaml"
    bad.write_text(machine.read_text().replace("servo", "nonexistent-template"))
    service.machine = bad
    assert client.post("/api/jobs/prepare", headers=HEADERS, json=PAYLOAD).status_code == 409
    assert not service.jobs_dir.exists()
    assert main([str(source), "--machine", str(machine), "--tools", str(tmp_path / "missing.db"),
                 "--out", str(tmp_path / "bad"), "--origin", "0", "0", "0"]) == 2
    assert not (tmp_path / "missing.db").exists() and db.exists()


def test_symlink_source_and_existing_target_are_rejected(setup):
    service, client, source, *_ = setup
    link = source.with_name("link.lnx")
    link.symlink_to(source)
    assert "link.lnx" not in service.context()["programs"]
    response = client.post("/api/jobs/prepare", headers=HEADERS,
                           json={**PAYLOAD, "program": "link.lnx"})
    assert response.status_code == 409
    assert not service.jobs_dir.exists()
