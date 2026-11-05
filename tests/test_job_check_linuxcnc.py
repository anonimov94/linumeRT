"""Prepared snapshots in actual isolated LinuxCNC, without starting a controller.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import os
from pathlib import Path

import pytest
from job_support import inputs
from linumert.programs import job, job_check

pytestmark = pytest.mark.linuxcnc


@pytest.fixture(autouse=True)
def _linuxcnc_cleanup():
    """Override controller-global cleanup: these tests own private rs274 processes only.

    run_interpreter/run_bounded reap their own process groups. The conftest cleanup
    belongs to tests which start a controller and must never run for this module.
    """
    yield


@pytest.mark.parametrize("offset,origin,zlength,rejected", [
    ("G54", (50, 50, -80), 40, False), ("G55", (50, 50, -80), 40, False),
    ("G54", (590, 50, -80), 40, True), ("G54", (50, 50, -80), 100, True),
])
def test_real_interpreter_uses_selected_offset_tool_table_and_source_lines(
        tmp_path, monkeypatch, offset, origin, zlength, rejected):
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache/linuxcnc-2.9"))
    if not (root / "bin/rs274").exists():
        pytest.skip("requires LinuxCNC RIP")
    program, machine, drives, tools = inputs()
    program.steps[0].params["offset"] = offset
    tools[1].offsets["Z"] = zlength
    package = tmp_path / "job"
    job.publish(job.render(program, machine, drives, tools, origin, offset), package)
    before = {p.name: p.read_bytes() for p in package.iterdir()}
    live = tmp_path / "live-home"
    live.mkdir()
    sentinel = live / ".tool.mmap"
    sentinel.write_bytes(b"live controller mapping must remain unchanged")
    monkeypatch.setenv("HOME", str(live))
    report = job_check.check(package, (50, 50, -5), root=root)
    assert report["checks"]["interpreter"] == "passed", report["messages"]
    assert report["interpreter"]["completed"]
    assert report["status"] == ("rejected" if rejected else "partial")
    assert bool(report["violations"]) == rejected
    assert report["checks"]["motion_limits"] == ("failed" if rejected else "pending")
    assert report["checks"]["material"] == "pending"
    assert f"{zlength:.4f}" in report["canonical_trace"]
    assert all(v["line"] > 0 for v in report["violations"])
    assert {p.name: p.read_bytes() for p in package.iterdir()} == before
    assert sentinel.read_bytes() == b"live controller mapping must remain unchanged"
