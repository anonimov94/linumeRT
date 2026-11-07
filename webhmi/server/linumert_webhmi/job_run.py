"""Persistent observational run log, outside RT; no controller commands.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import copy
import json
import math
import time
import uuid
from datetime import UTC, datetime

from linumert.programs.job import json_text
from linumert.programs.job_binding import same_context

TERMINAL = {"completed_observed", "aborted", "estop", "fault", "start_timeout",
            "resume_timeout", "unavailable", "client_lost"}


class RunLog:
    def __init__(self, root, identity, *, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.run_id = uuid.uuid4().hex
        self.path = root / "runs" / self.run_id
        self.path.mkdir(parents=True, mode=0o700)
        self.phase = "starting"
        self.seen_running = False
        self.stop_requested = False
        self.resume_requested = False
        self.resume_at = None
        self.needs_abort = False
        self.samples = 0
        self.quiet = 0
        self.finished = None
        self.last_line = 0
        self.alarms = {}
        self.client_loss_at = None
        self.pause_context = None
        self._pause_candidate = None
        self._pause_samples = 0
        self.identity = {"format": "linumert.job.run", "version": 1, "run_id": self.run_id,
            **{k: identity[k] for k in ("job_id", "execution_id", "verification_id", "target")},
            "started_at": datetime.now(UTC).isoformat(), "source": "linuxcnc.stat",
            "sampling": "NML poll; tooldata/HAL reads sequential, not an atomic servo trace"}
        (self.path / "manifest.json").write_text(json_text(self.identity), encoding="utf-8")
        self.stream = (self.path / "samples.jsonl").open("x", encoding="utf-8", buffering=1)
        self.event("run_requested")

    @property
    def active(self):
        return self.phase not in TERMINAL

    def event(self, name, **data):
        self.stream.write(json_text({"event": name, "t": self.clock() - self.started,
                                     **data}).replace("\n", " ").strip() + "\n")

    def command(self, name):
        self.event("command", command=name)
        if name == "stop":
            self.stop_requested = True
        if name == "resume":
            self.resume_requested = True
            self.resume_at = self.clock()

    @staticmethod
    def context(snap, live):
        return {"program": snap.program_file, "tool": snap.tool_number,
                "commanded": {a.name: a.commanded for a in snap.axes},
                **{k: live.get(k) for k in ("tool_offset", "g5x_index", "g5x_offset",
                                           "g92_offset", "rotation_xy", "tool_table")}}

    def sample(self, snap, live, alarms):
        if not self.active:
            return
        elapsed = self.clock() - self.started
        if live.get("hmi_alive") is False and self.client_loss_at is None:
            self.client_loss_at = elapsed
            self.event("client_lost_observed")
        self.samples += 1
        self.last_line = max(self.last_line, live.get("motion_line") or 0)
        for alarm in alarms:
            self.alarms.setdefault(str(alarm["id"]), {**alarm, "observed_at_s": elapsed})
        row = {"t": elapsed, "poll_time": snap.timestamp, "line": snap.current_line,
               "motion_line": live.get("motion_line"), "task": snap.task_state.value,
               "mode": snap.mode.value, "interp": snap.interp_state.value,
               "tool": snap.tool_number, "tool_offset": live.get("tool_offset"),
               "g5x_offset": live.get("g5x_offset"), "g92_offset": live.get("g92_offset"),
               "axes": {a.name: {"commanded": a.commanded, "actual": a.position,
                                 "following_error": a.following_error} for a in snap.axes},
               "overrides": [snap.feed_override, snap.rapid_override, snap.spindle_override],
               "alarms": alarms, "errors": list(snap.errors)}
        row.update({k: live.get(k) for k in
                    ("inpos", "current_vel", "task_done", "hal", "hmi_alive")})
        self.stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        interp = snap.interp_state.value
        if snap.task_state.value == "estop":
            self.finish("client_lost" if self.client_loss_at is not None else "estop")
        elif snap.errors or alarms or snap.task_state.value != "on":
            self.finish("fault")
        elif interp in ("reading", "waiting"):
            self.seen_running = True
            self.phase = "stopping" if self.stop_requested else "running"
            self.quiet = 0
            self.pause_context = None
            self._pause_candidate, self._pause_samples = None, 0
            self.resume_requested = False
        elif interp == "paused":
            self.seen_running = True
            self.phase = "paused"
            if self.resume_requested and self.clock() - self.resume_at > 5:
                self.finish("resume_timeout")
                return
            if self.pause_context is None:
                context = self.context(snap, live)
                # LinuxCNC inpos stays false when a paused motion queue is pending.
                # Require a stable commanded context and settled feedback instead.
                settled = self.paused_settled(snap, live)
                self._pause_samples = (self._pause_samples + 1 if settled
                    and same_context(context, self._pause_candidate) else 1 if settled else 0)
                self._pause_candidate = copy.deepcopy(context)
                if self._pause_samples >= 3:
                    self.pause_context = copy.deepcopy(context)
                    self.event("pause_settled", context=self.pause_context)
        elif interp == "idle" and (self.stop_requested or self.seen_running):
            quiet = (live.get("inpos") is True and live.get("task_done") is True
                     and isinstance(live.get("current_vel"), (int, float))
                     and abs(live["current_vel"]) < 1e-4)
            self.quiet = self.quiet + 1 if quiet else 0
            if self.quiet >= 3:
                self.finish("aborted" if self.stop_requested else "completed_observed")
        elif elapsed > 5:
            self.finish("start_timeout")

    @staticmethod
    def paused_settled(snap, live):
        velocity = live.get("current_vel")
        return (isinstance(velocity, (int, float)) and not isinstance(velocity, bool)
                and math.isfinite(velocity) and abs(velocity) < 1e-4 and bool(snap.axes)
                and all(math.isfinite(a.position) and math.isfinite(a.commanded)
                        and abs(a.position - a.commanded) < .001
                        and math.isfinite(a.following_error) and abs(a.following_error) < .001
                        for a in snap.axes))

    def finish(self, phase):
        if not self.active:
            return
        self.finished = self.clock()
        self.needs_abort = phase in {"fault", "start_timeout", "resume_timeout", "unavailable"}
        self.phase = phase
        self.event("terminal", phase=phase)
        result = {**self.identity, "status": phase, "elapsed_s": self.finished - self.started,
                  "samples": self.samples, "last_line": self.last_line,
                  "alarms": list(self.alarms.values()),
                  "client_loss_at_s": self.client_loss_at,
                  "completion_evidence": "idle after observed running; gateway command log",
                  "servo_trace": False}
        (self.path / "result.json").write_text(json_text(result), encoding="utf-8")
        self.stream.close()

    def unavailable(self):
        self.phase, self.finished, self.needs_abort = "unavailable", self.clock(), True
        try:
            self.stream.close()
        except OSError:
            pass

    def status(self):
        return {"run_id": self.run_id, "phase": self.phase, "samples": self.samples,
                "elapsed_s": (self.finished if self.finished is not None else self.clock())
                             - self.started,
                "line": self.last_line}
