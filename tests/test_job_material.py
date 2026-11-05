"""Frozen job models, frame continuity and diagnostic failure cases.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import copy
import json
import subprocess
from dataclasses import asdict

import pytest
from job_support import inputs
from linumert.programs import job
from linumert_sim import job_preflight
from linumert_sim.job_collisions import sweep
from linumert_sim.job_material import diagnose
from linumert_sim.job_model import frozen_cutters, frozen_machine
from linumert_sim.job_path import Frame, segments
from linumert_sim.machine import Body, Machine


def complete_inputs():
    program, machine, drives, tools = inputs()
    program.stock.material = "aluminium"
    for tool in tools.values():
        tool.params.update(holder_d=32, holder_l=10, flutes=2, hand=1)
    return program, machine, drives, tools


def trace_fixture():
    calls, motions = [], []
    def add(name, args, line=0, tool=0, rpm=0, feed=100):
        call = {"name": name, "args": args, "line": line}
        calls.append(call)
        if name in ("STRAIGHT_TRAVERSE", "STRAIGHT_FEED", "ARC_FEED"):
            motions.append({**call, "tool": tool, "rpm": rpm, "feed": feed})
    add("USE_LENGTH_UNITS", ["CANON_UNITS_MM"])
    add("SET_G5X_OFFSET", [1, 200, 200, -80, 0, 0, 0, 0, 0, 0])
    add("STRAIGHT_TRAVERSE", [0, 0, 75, 0, 0, 0, 0, 0, 0])
    add("CHANGE_TOOL", [1], 1)
    add("USE_TOOL_LENGTH_OFFSET", [0, 0, 40, 0, 0, 0, 0, 0, 0], 1)
    add("STRAIGHT_TRAVERSE", [10, 10, 5, 0, 0, 0, 0, 0, 0], 2, 1, 6000)
    add("STRAIGHT_FEED", [10, 10, -1, 0, 0, 0, 0, 0, 0], 3, 1, 6000)
    add("STRAIGHT_FEED", [20, 10, -1, 0, 0, 0, 0, 0, 0], 4, 1, 6000)
    return {"format": "linumert.job.trace", "version": 1, "completed": True,
            "source": "linuxcnc.gcode", "calls": calls, "motions": motions}


def data_fixture():
    files = job.render(*complete_inputs(), (200, 200, -80), "G54")
    return {"files": files, "trace": trace_fixture(), "start_mm": [200, 200, -5]}


def test_frozen_models_never_read_current_library(monkeypatch):
    _, config, drives, tools = complete_inputs()
    monkeypatch.setattr("linumert_sim.machine._template", lambda _: pytest.fail("mutable lookup"))
    original = frozen_machine(config, drives)
    modified = copy.deepcopy(drives)
    modified["drv_x"]["parameters"]["motor"]["peak_torque"] *= 0.5
    changed = frozen_machine(config, modified)
    assert changed.axis_force["X"] < original.axis_force["X"]
    assert any(b.name == "magazyn_narzedzi" for b in original.bodies)
    cutters = frozen_cutters([asdict(t) for t in tools.values()])
    assert cutters[1].gauge == 40 and cutters[1].holder_r == 16
    assert not cutters[1].substitute


@pytest.mark.parametrize("missing", ["holder_d", "holder_l", "flute_length", "hand", "max_rpm"])
def test_incomplete_geometry_never_becomes_generic_cylinder(missing):
    *_, tools = complete_inputs()
    del tools[1].params[missing]
    with pytest.raises(ValueError, match="T1"):
        frozen_cutters([asdict(t) for t in tools.values()])


def test_no_default_motor_force_or_spindle_power():
    _, config, drives, _ = complete_inputs()
    drives["drv_y1"]["parameters"]["motor"].pop("peak_torque")
    drives["drv_y1"]["parameters"]["motor"].pop("rated_torque")
    with pytest.raises(ValueError, match="Oś Y"):
        frozen_machine(config, drives)
    _, config, drives, _ = complete_inputs()
    drives["drv_spindle"]["parameters"]["motor"].pop("torque_curve")
    with pytest.raises(ValueError, match="krzywej"):
        frozen_machine(config, drives)


def test_frames_tlo_and_initialization_are_not_physical_sweeps():
    path = list(segments(trace_fixture(), (200, 200, -5)))
    assert len(path) == 3 and path[0].line == 2
    assert path[0].start == pytest.approx((200, 200, -5), abs=1e-10)
    assert path[0].end == pytest.approx((210, 210, -35), abs=1e-10)
    assert path[1].end == pytest.approx((210, 210, -41), abs=1e-10)
    assert path[1].tool == 1 and path[1].rpm == 6000
    frame = Frame((50.123456, 80.654321, -80), (2.123456, -3.765432, 5.1), (0, 0, 40.1234), 31)
    p = (12.345678, 9.876543, -1.0000007)
    assert frame.program(frame.machine(p)) == pytest.approx(p, abs=1e-10)


@pytest.mark.parametrize("plane,end,center", [
    ("CANON_PLANE_XY", (20, 20, -1), (10, 20)),
    ("CANON_PLANE_XZ", (20, 10, -11), (-11, 10)),
    ("CANON_PLANE_YZ", (10, 20, -11), (10, -11)),
])
def test_arcs_keep_source_plane_and_double_precision(plane, end, center):
    trace = trace_fixture()
    trace["calls"].insert(-1, {"name": "SELECT_PLANE", "args": [plane], "line": 4})
    axes = {"CANON_PLANE_XY": (0, 1, 2), "CANON_PLANE_XZ": (2, 0, 1),
            "CANON_PLANE_YZ": (1, 2, 0)}[plane]
    args = [end[axes[0]], end[axes[1]], *center, 1, end[axes[2]], 0, 0, 0, 0, 0, 0]
    trace["calls"][-1].update(name="ARC_FEED", args=args)
    trace["motions"][-1].update(name="ARC_FEED", args=args)
    arc = list(segments(trace, (200, 200, -5)))[-1]
    assert arc.center is not None and arc.length > 10
    assert arc.point(1) == pytest.approx(arc.frame.machine(end), abs=1e-10)
    assert arc.sample_count(1) >= 40


def test_trace_mismatch_and_unknown_events_fail_closed():
    trace = trace_fixture()
    trace["motions"][-1]["line"] = 999
    with pytest.raises(ValueError, match="metadane"):
        list(segments(trace, (200, 200, -5)))
    trace = trace_fixture()
    trace["calls"].append({"name": "UNKNOWN", "args": [], "line": 5})
    with pytest.raises(ValueError, match="UNKNOWN"):
        list(segments(trace, (200, 200, -5)))
    with pytest.raises(ValueError, match="Początek"):
        list(segments(trace_fixture(), (50, 50, -5)))


def test_continuous_sweep_catches_thin_body_between_endpoints():
    body = Body("thin", "box", "table", (0.0001, 1, 1), (10.12345, 0, 0))
    moving = Body("head", "cylinder", "spindle", (1, 1), (0, 0, 0))
    machine = Machine(bodies=[body, moving])
    hits = sweep(machine, None, (0, 0, 0), (20, 0, 0), line=27, tool=0)
    assert hits and hits[0]["line"] == 27 and hits[0]["conservative"]
    assert not sweep(machine, None, (0, 5, 0), (20, 5, 0), line=28, tool=0)


def test_complete_cut_and_explicit_missing_material():
    data = data_fixture()
    result = diagnose(data)
    assert not result["events"]
    assert result["removed_mm3"] > 50 and result["time_lower_bound_s"] > 9
    assert result["motions"] == 3 and result["peak_load"]["power_w"] > 0
    raw = json.loads(data["files"]["program.lnx"])
    raw["stock"]["material"] = None
    data["files"]["program.lnx"] = json.dumps(raw)
    with pytest.raises(ValueError, match="materiał"):
        diagnose(data)


@pytest.mark.parametrize("mode,code", [("rapid", "K-302"), ("stopped", "K-301"),
                                       ("reverse", "K-308"), ("overspeed", "K-309")])
def test_material_events_use_incoming_state_and_original_line(mode, code):
    data = data_fixture()
    if mode == "rapid":
        data["trace"]["calls"][-2]["name"] = "STRAIGHT_TRAVERSE"
        data["trace"]["motions"][-2]["name"] = "STRAIGHT_TRAVERSE"
    else:
        data["trace"]["motions"][-1]["rpm"] = {
            "stopped": 0, "reverse": -6000, "overspeed": 8001}[mode]
        if mode == "overspeed":
            raw = json.loads(data["files"]["tools.json"])
            raw[0]["params"]["max_rpm"] = 6500
            data["files"]["tools.json"] = json.dumps(raw)
            data["trace"]["motions"][-1]["rpm"] = 7000
    result = diagnose(data)
    assert any(e["code"] == code and e["line"] in (3, 4) and e["tool"] == 1
               for e in result["events"])


def test_holder_contact_and_frozen_spindle_overload_are_reported():
    data = data_fixture()
    tools = json.loads(data["files"]["tools.json"])
    tools[0]["params"].update(l=0.5, flute_length=0.5, holder_l=39.5)
    data["files"]["tools.json"] = json.dumps(tools)
    result = diagnose(data)
    assert any(e["code"] == "K-303" and "oprawka" in e["pair"] for e in result["events"])
    data = data_fixture()
    drives = json.loads(data["files"]["drives.json"])
    curve = drives["drv_spindle"]["parameters"]["motor"]["torque_curve"]
    drives["drv_spindle"]["parameters"]["motor"]["torque_curve"] = [[w, 0.00001] for w, _ in curve]
    data["files"]["drives.json"] = json.dumps(drives)
    result = diagnose(data)
    assert any(e["code"] == "K-306" for e in result["events"])
    assert result["peak_load"]["spindle_ratio"] > 1


@pytest.mark.parametrize("failure", ["timeout", "exit", "truncated"])
def test_worker_failure_never_publishes_positive_diagnostics(tmp_path, monkeypatch, failure):
    data = data_fixture()
    package = job.publish(data["files"], tmp_path / "job")
    manifest, _ = job.read(package)
    base = {"job_id": manifest["job_id"], "report_id": "previous", "status": "partial",
            "checks": {"integrity": "passed", "interpreter": "passed", "motion_limits": "passed",
                       "material": "pending", "execution": "not_started"},
            "messages": [], "limitations": [], "precise_trace": data["trace"]}
    monkeypatch.setattr(job_preflight.job_check, "check", lambda *a, **k: copy.deepcopy(base))
    def fail(*a, **k):
        if failure == "timeout":
            raise subprocess.TimeoutExpired("private-worker", 0.01)
        return subprocess.CompletedProcess(a, 3 if failure == "exit" else 0,
                                           "{" if failure == "truncated" else "", "failed")
    monkeypatch.setattr(job_preflight, "run_bounded", fail)
    result = job_preflight.check(package, data["start_mm"])
    assert result["status"] == "incomplete" and "material_diagnostic" not in result
    assert all(result["checks"][k] == "incomplete" for k in ("material", "collisions", "loads"))
    assert result["checks"]["interpreter"] == "passed" and result["report_id"] != "previous"
