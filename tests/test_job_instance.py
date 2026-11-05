"""Private runtime copies and a closed Start gate, without controller commands.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import os
from pathlib import Path

import pytest
from linumert.programs import job, job_execution
from linumert_webhmi import Command, FakeBackend, Gateway, create_app
from linumert_webhmi.backend import CommandError
from linumert_webhmi.job_instance import Instance, prepare
from starlette.testclient import TestClient
from test_job_execution import package as package


@pytest.fixture
def configuration(package, tmp_path):
    source, report = package
    return job_execution.publish(job_execution.render(source, report, "plant"), tmp_path / "export")


def test_private_copy_preserves_evidence_tools_and_closed_safety(configuration, tmp_path):
    original = {p.relative_to(configuration): p.read_bytes()
                for p in configuration.rglob("*") if p.is_file()}
    out = tmp_path / "instance"
    record = prepare(configuration, out, port=8792)
    ini = out / "config" / record["ini"]
    bound = Instance(out / "instance.json", ini)
    assert not bound.status()["can_start"]
    assert not bound.status()["execution_authorization"]
    assert "HMI_ESTOP_BYPASS = 0" in ini.read_text()
    assert "--hal --postgui instance_postgui.hal --instance ../instance.json" in ini.read_text()
    for name, data in original.items():
        assert (out / "evidence" / name).read_bytes() == data
        assert (configuration / name).read_bytes() == data
    assert (out / "config/tool.tbl").read_bytes() == original[Path("tool.tbl")]
    if os.name != "nt":
        assert out.stat().st_mode & 0o777 == 0o700
    with pytest.raises(FileExistsError):
        prepare(configuration, out)
    with pytest.raises(ValueError, match="poza"):
        prepare(configuration, configuration / "runtime")


def test_resigned_foreign_runtime_hal_is_refused(configuration, tmp_path):
    out = tmp_path / "instance"
    record = prepare(configuration, out)
    path = out / "config/linumert_plant.hal"
    path.write_text(path.read_text() + "\nsetp lrt_hmi_bypass.in1 true\n")
    record["config_hashes"]["linumert_plant.hal"] = job.digest(path.read_bytes())
    (out / "instance.json").write_text(job.json_text(record))
    with pytest.raises(ValueError, match="nie odpowiada"):
        Instance(out / "instance.json", out / "config" / record["ini"])


def test_instance_rejects_test_bypass(package, tmp_path):
    source, report = package
    config = job_execution.publish(job_execution.render(source, report, "sim", test_mode=True),
                                   tmp_path / "export")
    with pytest.raises(ValueError, match="bypass"):
        prepare(config, tmp_path / "runtime")
    assert not (tmp_path / "runtime").exists()


def test_instance_rejects_other_ini(configuration, tmp_path):
    out = tmp_path / "instance"
    prepare(configuration, out)
    with pytest.raises(ValueError, match="Obca konfiguracja"):
        Instance(out / "instance.json", configuration / "mill_servo_table.ini")


def test_bound_gateway_api_and_websocket_refuse_start_without_machine_side_effects(
        configuration, tmp_path):
    out = tmp_path / "instance"
    record = prepare(configuration, out)
    instance = Instance(out / "instance.json", out / "config" / record["ini"])
    backend = FakeBackend()
    gateway = Gateway(backend, instance=instance)
    before = backend.machine.snapshot()
    token = "instance-test-token-123456"
    with TestClient(create_app(gateway, token), base_url="http://127.0.0.1:8765") as client:
        state = client.get("/api/state", headers={"X-Linumert-Token": token}).json()["state"]
        assert state["execution"]["job_id"] == record["job_id"]
        assert "token" not in json.dumps(state["execution"])
        assert client.post("/api/command", json={"cmd": "run"},
                           headers={"X-Linumert-Token": token}).status_code == 409
        with client.websocket_connect("/ws", headers={"host": "127.0.0.1:8765"}) as ws:
            ws.send_json({"auth": token})
            assert ws.receive_json()["type"] == "state"
            ws.send_json({"id": 1, "cmd": "run"})
            reply = ws.receive_json()
            while reply.get("id") != 1:
                reply = ws.receive_json()
            assert reply["type"] == "error" and "zablokowany" in reply["message"]
    with pytest.raises(CommandError, match="zablokowany"):
        gateway.execute(Command(cmd="resume"))
    after = backend.machine.snapshot()
    assert after.task_state == before.task_state and after.positions == before.positions
