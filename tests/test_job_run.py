"""Persistent real-state lifecycle; constructed observations, not a CNC acceptance.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import json
from dataclasses import replace

import pytest
from linumert.cnc import AxisSnapshot, InterpState, MachineSnapshot, Mode, TaskState
from linumert_webhmi.job_run import RunLog


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def run(tmp_path):
    clock = Clock()
    identity = dict(job_id="a" * 64, execution_id="b" * 64, verification_id="c" * 64,
                    target="plant")
    log = RunLog(tmp_path, identity, clock=clock)
    yield log, clock
    if log.active:
        log.finish("unavailable")


def sample(log, interp=InterpState.READING, **overrides):
    snap = MachineSnapshot(timestamp=1, task_state=TaskState.ON, mode=Mode.AUTO,
        interp_state=interp, axes=(AxisSnapshot("X", position=1.0003, commanded=1),))
    live = {"inpos": True, "current_vel": 0, "task_done": True, "motion_line": 15}
    live.update(overrides)
    log.sample(snap, live, [])
    return snap, live


def test_idle_read_ahead_cannot_finish_queued_motion_and_stop_is_distinct(run):
    log, clock = run
    sample(log)
    clock.t = 1
    for _ in range(5):
        sample(log, InterpState.IDLE, task_done=False, inpos=False, current_vel=2)
    assert log.active
    log.command("stop")
    for _ in range(3):
        sample(log, InterpState.IDLE)
    assert log.phase == "aborted"
    result = json.loads((log.path / "result.json").read_text())
    assert result["samples"] == 9 and not result["servo_trace"]
    assert result["source"] == "linuxcnc.stat"
    clock.t = 100
    assert log.status()["elapsed_s"] == result["elapsed_s"]
    rows = [json.loads(line) for line in (log.path / "samples.jsonl").read_text().splitlines()]
    assert rows[1]["axes"]["X"]["actual"] == 1.0003
    assert any(row.get("command") == "stop" for row in rows)


def test_completion_requires_observed_execution_and_settled_done(run):
    log, clock = run
    sample(log, InterpState.IDLE)
    assert log.active
    sample(log)
    for _ in range(2):
        sample(log, InterpState.IDLE)
    assert log.active
    clock.t = 2
    sample(log, InterpState.IDLE)
    assert log.phase == "completed_observed" and not log.needs_abort


def test_pause_receipt_is_independent_and_failed_resume_times_out(run):
    log, clock = run
    sample(log)
    _, live = sample(log, InterpState.PAUSED, tool_table=[{"id": 1}])
    live["tool_table"][0]["id"] = 999
    assert log.pause_context["tool_table"] == [{"id": 1}]
    log.command("resume")
    clock.t = 5.1
    sample(log, InterpState.PAUSED)
    assert log.phase == "resume_timeout" and log.needs_abort


@pytest.mark.parametrize("cause", ["estop", "fault", "timeout"])
def test_interruptions_cannot_become_completion(run, cause):
    log, clock = run
    snap, live = sample(log)
    if cause == "timeout":
        log.seen_running = False
        clock.t = 6
        snap = replace(snap, interp_state=InterpState.IDLE)
    elif cause == "estop":
        snap = replace(snap, task_state=TaskState.ESTOP)
    else:
        snap = replace(snap, errors=("joint following error",))
    log.sample(snap, live, [])
    assert log.phase == {"estop": "estop", "fault": "fault", "timeout": "start_timeout"}[cause]
    assert json.loads((log.path / "result.json").read_text())["status"] != "completed_observed"
