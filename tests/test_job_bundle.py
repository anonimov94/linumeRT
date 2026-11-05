"""Preparation must preserve operator inputs and publish a complete, identifiable job.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from job_support import inputs
from linumert.programs import job


def bundle():
    return job.render(*inputs(), origin=(50., 50., -80.))


def test_complete_job_is_deterministic_and_does_not_claim_verification(tmp_path):
    files = bundle()
    assert files == bundle()
    path = job.publish(files, tmp_path / "job")
    manifest, contents = job.read(path)
    assert manifest["name"] == "Detal pionowy" and len(manifest["job_id"]) == 64
    assert set(contents) == job.RESOURCES
    assert "G53 G0 Z-1" in contents["program.ngc"]
    assert "G53 G0 Z0\n" not in contents["program.ngc"]
    assert "G81" in contents["program.ngc"] and "T2 M6" in contents["program.ngc"]
    assert "T1 P1 Z40 D6" in contents["tool.tbl"]
    report = json.loads(contents["prepare.json"])
    assert report["status"] == "prepared" and report["checks"]["motion_limits"] == "pending"


@pytest.mark.parametrize("problem", ["missing", "diameter", "units", "origin", "order", "budget"])
def test_invalid_job_is_rejected_before_publication(tmp_path, problem):
    program, machine, drives, tools = inputs()
    origin = (50., 50., -80.)
    if problem == "missing":
        del tools[1]
    elif problem == "diameter":
        program.steps[2].params["tool_d"] = 8
    elif problem == "units":
        program.units = "inch"
    elif problem == "origin":
        origin = (0., float("nan"), 0.)
    elif problem == "order":
        del program.steps[1]
    elif problem == "budget":
        program.steps[2].params["step_down"] = 1e-15
    with pytest.raises(ValueError):
        job.publish(job.render(program, machine, drives, tools, origin), tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_existing_output_and_temporary_files_are_preserved_on_failure(tmp_path, monkeypatch):
    existing = tmp_path / "job"
    existing.mkdir()
    (existing / "operator.ngc").write_bytes(b"operator data\n")
    with pytest.raises(FileExistsError):
        job.publish(bundle(), existing)
    assert (existing / "operator.ngc").read_bytes() == b"operator data\n"

    def fail(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(job.os, "replace", fail)
    if job.os.name == "nt":
        monkeypatch.setattr(job.os, "rename", fail)
    with pytest.raises(OSError, match="publication failed"):
        job.publish(bundle(), tmp_path / "new")
    assert list(tmp_path.iterdir()) == [existing]


@pytest.mark.parametrize("name", ["program.ngc", "machine.yaml", "tools.json", "setup.json"])
def test_modified_job_is_rejected(tmp_path, name):
    path = job.publish(bundle(), tmp_path / "job")
    (path / name).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Zmieniony zasób"):
        job.read(path)


def test_publish_validates_contents_before_exposing_target(tmp_path):
    files = bundle()
    files["program.ngc"] += "G0 X99999\n"
    with pytest.raises(ValueError, match="Zmieniony zasób"):
        job.publish(files, tmp_path / "job")
    assert list(tmp_path.iterdir()) == []


def test_concurrent_publishers_cannot_overwrite_a_package(tmp_path):
    files = bundle()

    def publish():
        try:
            job.publish(files, tmp_path / "job")
            return "published"
        except FileExistsError:
            return "exists"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: publish(), range(2))) == ["exists", "published"]
    assert job.read(tmp_path / "job")[1]["program.ngc"] == files["program.ngc"]
    assert [p.name for p in tmp_path.iterdir()] == ["job"]
