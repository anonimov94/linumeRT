"""Actual interpreter consumes the derived frozen execution configuration.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json

import pytest
from linumert.cli import main
from linumert.programs import job, job_execution
from linumert.programs.job_check import save
from linumert.programs.job_trace import compare_motion
from linumert.programs.limits import number_lines
from linumert.programs.linuxcnc_check import interpreter_result, run_interpreter
from linumert_sim.job_verify import verify
from test_job_material import complete_inputs
from test_job_trace_linuxcnc import runtime as runtime

pytestmark = pytest.mark.linuxcnc


@pytest.fixture(autouse=True)
def _linuxcnc_cleanup():
    """Offline processes only; never clean up a live controller belonging to others."""
    yield


@pytest.mark.parametrize("target,offset", [("sim", "G54"), ("plant", "G54"), ("plant", "G55")])
def test_actual_rs274_consumes_same_verified_tools_frames_and_motion(
        runtime, tmp_path, monkeypatch, target, offset):
    rip, bridge = runtime
    program, config, drives, tools = complete_inputs()
    program.steps[0].params["offset"] = offset
    package = job.publish(job.render(program, config, drives, tools, (200, 200, -80), offset),
                          tmp_path / "job")
    report = verify(package, (200, 200, -5), root=rip, trace_library=bridge)
    assert report["status"] == "verified", report["messages"]
    verification = tmp_path / "verification.json"
    save(report, verification)
    monkeypatch.setattr("linumert.machine.drives.machine_drives.load_library",
                        lambda *a, **k: pytest.fail("current drive-library lookup"))
    out = tmp_path / "execution"
    assert main(["run-config", str(package), "--verification", str(verification),
                 "--target", target, "--out", str(out), "--plant-port", "47883"]) == 0
    manifest, files = job_execution.read(out)
    copy = tmp_path / "analysis.ngc"
    seed = "N0 G21 G90 G49 G92.1\nN0 G53 G0 X200 Y200 Z-5\n"
    copy.write_text(seed + number_lines(files["nc_files/program.ngc"]))
    run = run_interpreter(copy, root=rip, parameters_from=out / "linumert.var",
                          machine_ini=out / manifest["ini"], linear_units="mm")
    result = interpreter_result(run)
    assert result.ok, result.messages
    compare_motion(report["canonical_trace"], run.stdout)
    assert manifest["job_id"] == report["job_id"]
    assert not manifest["execution_authorization"] and manifest["status"] == "configured"
    assert json.loads((out / "verification.json").read_text())["report_id"] == report["report_id"]
