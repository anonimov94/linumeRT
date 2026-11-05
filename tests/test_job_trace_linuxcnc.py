"""Full-precision callbacks and private tooldata, using actual LinuxCNC 2.9.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from job_support import inputs
from linumert.programs import job
from linumert.programs.job_trace import capture
from linumert.programs.limits import analyze_canon

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
