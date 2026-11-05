"""Actual rs274 + private SDK trace + separate diagnostic worker, without CNC.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import subprocess
from pathlib import Path

import pytest
from job_support import inputs
from linumert.programs import job
from linumert_sim.job_preflight import check
from test_job_material import complete_inputs
from test_job_trace_linuxcnc import runtime as runtime

pytestmark = pytest.mark.linuxcnc


@pytest.fixture(autouse=True)
def _linuxcnc_cleanup():
    """Only owned offline child groups; never run controller-global cleanup."""
    yield


def test_complete_job_uses_private_worker_and_frozen_resources(runtime, tmp_path, monkeypatch):
    rip, bridge = runtime
    package = tmp_path / "job"
    job.publish(job.render(*complete_inputs(), (200, 200, -80)), package)
    before = {p.name: p.read_bytes() for p in package.iterdir()}
    build = tmp_path / "native"
    subprocess.run(["make", "-C", str(Path(__file__).resolve().parents[1] / "core/native"),
                    "shared", f"BUILD={build}"], capture_output=True, timeout=60, check=True)
    monkeypatch.setenv("LINUMERT_NATIVE_LIB", str(build / "liblinumert_native.so"))
    results = []
    for backend in ("0", "1"):
        monkeypatch.setenv("LINUMERT_NATIVE", backend)
        result = check(package, (200, 200, -5), root=rip, trace_library=bridge)
        assert result["checks"]["interpreter"] == "passed", result["messages"]
        assert result["checks"]["motion_limits"] == "passed", result["messages"]
        assert "material_diagnostic" in result, result["messages"]
        assert result["checks"]["execution"] == "not_started"
        results.append(result)
    a, b = (r["material_diagnostic"] for r in results)
    assert a["backend"] == "Python"
    assert b["backend"] == "C" and a["worker_nice"] >= 10 and b["worker_nice"] >= 10
    assert a["motions"] == b["motions"] == 81
    assert a["removed_mm3"] > 100
    assert a["removed_mm3"] == b["removed_mm3"]
    assert a["events"] == b["events"]
    assert a["time_lower_bound_s"] == b["time_lower_bound_s"]
    assert {p.name: p.read_bytes() for p in package.iterdir()} == before
    # Keep negative diagnostics visible in assertion output until the complete
    # prepared CAM fixture itself has been accepted through this same path.
    assert results[0]["status"] == "partial", results[0]["messages"]
    assert all(results[0]["checks"][k] == "passed" for k in ("material", "collisions", "loads"))


def test_missing_holder_data_is_incomplete_after_successful_interpreter(runtime, tmp_path):
    rip, bridge = runtime
    package = tmp_path / "job"
    job.publish(job.render(*inputs(), (200, 200, -80)), package)
    result = check(package, (200, 200, -5), root=rip, trace_library=bridge)
    assert result["checks"]["interpreter"] == result["checks"]["motion_limits"] == "passed"
    assert result["status"] == "incomplete" and result["checks"]["material"] == "incomplete"
    assert any("T1" in text and "oprawki" in text for text in result["messages"])
    assert "material_diagnostic" not in result
    manifest, _ = job.read(package)
    assert result["job_id"] == manifest["job_id"]
    assert result["report_id"] == job.digest(job.json_text({
        k: v for k, v in result.items() if k != "report_id"}).encode())


def test_declared_fixture_collision_reports_executed_source_line(runtime, tmp_path):
    rip, bridge = runtime
    program, config, drives, tools = complete_inputs()
    raw = config.model_dump(mode="json")
    raw["collision_bodies"].append({"name": "imadlo", "shape": "box", "attached_to": "vise",
        "size": [1, 40, 20], "position": [230, 220, -80]})
    config = type(config).model_validate(raw)
    package = tmp_path / "job"
    job.publish(job.render(program, config, drives, tools, (200, 200, -80)), package)
    result = check(package, (200, 200, -5), root=rip, trace_library=bridge)
    assert result["status"] == "rejected", result["messages"]
    assert result["checks"]["collisions"] == "failed"
    hits = [e for e in result["material_diagnostic"]["events"] if "imadlo" in e["pair"]]
    assert hits and all(e["line"] > 0 for e in hits)
    assert any(e["code"] == "K-304" and e["stop"] for e in hits)
    assert json.loads((package / "machine.yaml").read_text())["collision_bodies"][-1][
        "name"] == "imadlo"
