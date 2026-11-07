"""Full-precision callbacks and private tooldata, using actual LinuxCNC 2.9.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from job_support import inputs, write_inputs
from linumert.cnc import FakeMachine
from linumert.programs import job, job_check
from linumert.programs.job_trace import capture
from linumert.programs.limits import analyze_canon
from linumert.programs.prepare import JobService
from linumert_webhmi import FakeBackend, Gateway, create_app
from starlette.testclient import TestClient

pytestmark = pytest.mark.linuxcnc
ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"X": (1, 599), "Y": (1, 899), "Z": (-119, -1)}


@pytest.fixture(autouse=True)
def _linuxcnc_cleanup():
    """Only offline child groups exist; never call controller-global cleanup."""
    yield


@pytest.fixture(scope="module")
def runtime(tmp_path_factory):
    rip = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache/linuxcnc-2.9"))
    if not (rip / "src/emc/tooldata/tooldata.hh").is_file():
        pytest.skip("requires LinuxCNC 2.9 RIP source and SDK")
    build = tmp_path_factory.mktemp("job-trace-bridge")
    subprocess.run(["make", "-C", str(ROOT / "core/native"), "linuxcnc-tooldata",
                    f"LINUXCNC_DIR={rip}", f"BUILD={build}"],
                   capture_output=True, text=True, timeout=60, check=True)
    return rip, build / "liblinumert_tooldata.so"


def run(runtime, program, table="T1 P1 Z40 D6\n", **kwargs):
    rip, bridge = runtime
    return capture(program, table, kwargs.pop("origin", (50, 50, -80)), "G54",
                   (50, 50, -5), root=rip, library=bridge, **kwargs)


def test_prepared_job_preserves_tools_motion_lines_and_live_mapping(runtime, tmp_path, monkeypatch):
    program, machine, drives, tools = inputs()
    files = job.render(program, machine, drives, tools, (50, 50, -80))
    live = tmp_path / "live"
    live.mkdir()
    sentinel = live / ".tool.mmap"
    sentinel.write_bytes(b"live mapping must survive")
    monkeypatch.setenv("HOME", str(live))
    trace = run(runtime, files["program.ngc"], files["tool.tbl"])
    assert trace["completed"] and len(trace["motions"]) == 82
    assert trace["motions"][0]["line"] == 0  # initialization, not a job motion
    feeds = [m for m in trace["motions"] if m["name"] == "STRAIGHT_FEED"]
    assert feeds[0]["line"] == 19 and feeds[0]["tool"] == 1
    assert feeds[0]["rpm"] == 6000
    assert feeds[-1]["tool"] == 2 and feeds[-1]["rpm"] == 3000
    offsets = [c["args"][2] for c in trace["calls"] if c["name"] == "USE_TOOL_LENGTH_OFFSET"]
    assert offsets[-2:] == pytest.approx([40, 35], abs=1e-12)
    report = analyze_canon(trace["canonical"], LIMITS, strict=True)
    assert not report.violations and not report.cuts_without_tlo
    assert sentinel.read_bytes() == b"live mapping must survive"


def test_inch_coordinates_and_table_are_not_rounded_or_scaled_twice(runtime):
    program = ("G20 G90 G17 G94\nT7 M6\nG43 H7\nS4000 M3\n"
               "G1 X0.10000003 Y0.2 Z-1 F12.345678\nM2\n")
    trace = run(runtime, program, "T7 P12 Z40.1234 D6.2345\n",
                origin=(50.123456, 50, -80))
    move = trace["motions"][-1]
    assert move["line"] == 5 and move["tool"] == 7
    assert move["args"][:3] == pytest.approx([2.540000762, 5.08, -25.4], abs=1e-10)
    assert move["feed"] == pytest.approx(12.345678 * 25.4, abs=1e-10)
    offset = [c for c in trace["calls"] if c["name"] == "SET_G5X_OFFSET"][-1]
    assert offset["args"][1] == pytest.approx(50.123456, abs=1e-11)
    tlo = [c for c in trace["calls"] if c["name"] == "USE_TOOL_LENGTH_OFFSET"][-1]
    assert tlo["args"][2] == pytest.approx(40.1234, abs=1e-11)
    assert not analyze_canon(trace["canonical"], LIMITS, strict=True).violations


def test_tools_follow_executed_control_flow_and_expressions(runtime):
    program = ("G21 G90 G94\nT1 M6\nG43 H1\n"
               "o<skip> if [0]\nT7 M6\nG43 H7\no<skip> endif\n"
               "G1 X1 F100\n#1=7\nT#1 M6\nG43 H#1\nG1 X2\nM2\n")
    trace = run(runtime, program, "T1 P11 Z40 D6\nT7 P22 Z35 D5\n")
    feeds = [m for m in trace["motions"] if m["name"] == "STRAIGHT_FEED"]
    assert [m["tool"] for m in feeds] == [1, 7]
    assert [m["line"] for m in feeds] == [8, 12]


def test_bad_program_and_quiet_infinite_loop_never_return_a_trace(runtime):
    with pytest.raises(ValueError, match="linia 2"):
        run(runtime, "G21\nG1 X5\nM2\n")
    with pytest.raises(ValueError, match="czas"):
        run(runtime, "o100 while [1]\n#1=1\no100 endwhile\nM2\n", timeout=0.3)
    with pytest.raises(ValueError, match="nie zakończył"):
        run(runtime, "G21\nG1 X5 F100\n")


@pytest.mark.parametrize("existing", [False, True])
def test_bridge_refuses_nonprivate_home_or_an_existing_mapping(runtime, tmp_path, existing):
    rip, bridge = runtime
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    home = private if existing else tmp_path
    sentinel = home / ".tool.mmap"
    sentinel.write_bytes(b"do not truncate")
    config = {"bridge": str(bridge)}
    script = ("import ctypes,json; d=" + repr(config) + "; "
              "lib=ctypes.CDLL(d['bridge']); "
              "lib.lrt_tooldata_open.argtypes=[ctypes.c_char_p]; "
              "lib.lrt_tooldata_open.restype=ctypes.c_int; "
              "print(lib.lrt_tooldata_open(b'missing.tbl'))")
    env = os.environ.copy()
    env["HOME"] = str(home)
    done = subprocess.run([sys.executable, "-c", script], cwd=private, env=env,
                           capture_output=True, text=True, timeout=10, check=True)
    assert int(done.stdout) < 0
    assert sentinel.read_bytes() == b"do not truncate"


@pytest.mark.parametrize("origin,failed", [
    ((50, 50, -80), False), ((539.00004, 50, -80), True),
    ((538.99996, 50, -80), False),
])
def test_preflight_uses_unrounded_limits_including_near_boundary(runtime, tmp_path, origin, failed):
    program, machine, drives, tools = inputs()
    package = tmp_path / "job"
    job.publish(job.render(program, machine, drives, tools, origin), package)
    before = {p.name: p.read_bytes() for p in package.iterdir()}
    rip, bridge = runtime
    result = job_check.check(package, (50, 50, -5), root=rip, trace_library=bridge)
    assert result["checks"]["interpreter"] == "passed", result["messages"]
    assert result["checks"]["motion_limits"] == ("failed" if failed else "passed"), result
    assert result["status"] == ("rejected" if failed else "partial")
    assert result["checks"]["material"] == "pending"
    assert result["coordinate_resolution_mm"] == 1e-6
    assert job_check.ROUNDING_NOTE not in result["limitations"]
    if failed:
        violation = next(v for v in result["violations"] if v["axis"] == "X")
        assert violation["line"] == 20
        assert violation["value"] == pytest.approx(599.00004, abs=1e-9)
    assert {p.name: p.read_bytes() for p in package.iterdir()} == before


def test_arc_interior_is_checked_on_precise_callbacks(runtime):
    text = "G21 G90 G17 G94\nT1 M6\nG43 H1\nG0 X0 Y1 Z0\nG3 X0 Y-1 I0 J-1 F100\nM2\n"
    trace = run(runtime, text, origin=(1.5, 50, -80))
    result = analyze_canon(trace["canonical"], LIMITS, strict=True)
    assert [(v.line, v.axis, v.side) for v in result.violations] == [(5, "X", "min")]
    assert result.violations[0].value == pytest.approx(0.5, abs=1e-9)


def test_g55_preflight_uses_the_same_offset_in_both_interfaces(runtime, tmp_path):
    program, machine, drives, tools = inputs()
    program.steps[0].params["offset"] = "G55"
    package = tmp_path / "job"
    job.publish(job.render(program, machine, drives, tools, (50, 50, -80), "G55"), package)
    rip, bridge = runtime
    result = job_check.check(package, (50, 50, -5), root=rip, trace_library=bridge)
    assert result["checks"]["motion_limits"] == "passed", result["messages"]


def test_api_persists_precise_result_preserving_package_and_cnc(runtime, tmp_path, monkeypatch):
    rip, bridge = runtime
    monkeypatch.setenv("LINUXCNC_DIR", str(rip))
    monkeypatch.setenv("LINUMERT_TOOL_DATA_LIB", str(bridge))
    source, db, machine = write_inputs(tmp_path / "input")
    service = JobService(source.parent, machine, db, tmp_path / "jobs")
    prepared = service.prepare(source.name, "part", (50, 50, -80))
    archive = service.archive("part")
    gateway = Gateway(FakeBackend(FakeMachine()))
    state = gateway.snapshot()
    token = "precise-linuxcnc-api-test"
    client = TestClient(create_app(gateway, token, jobs=service), base_url="http://127.0.0.1")
    response = client.post("/api/jobs/part/preflight", headers={"X-Linumert-Token": token},
        json={"job_id": prepared["manifest"]["job_id"], "start_mm": [50, 50, -5]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "incomplete" and result["checks"]["motion_limits"] == "passed"
    assert result["checks"]["material"] == "incomplete"  # this fixture lacks holder geometry
    assert result["checks"]["execution"] == "not_started"
    assert len(result["precise_trace"]["motions"]) == 82
    saved, = (service.jobs_dir / ".preflight").glob("*.json")
    assert json.loads(saved.read_text()) == result
    assert service.archive("part") == archive and gateway.snapshot() == state
