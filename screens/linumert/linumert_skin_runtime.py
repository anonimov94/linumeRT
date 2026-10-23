# SPDX-License-Identifier: GPL-2.0-or-later
"""Prototype skin metadata and presentation switch gate, without machine commands.

Model-Author: Codex. This gate is not a safety function. A future host must sample
the controller again immediately before replacing a view, keeping global controls.
"""

import json
import math
from dataclasses import dataclass

from linumert_skin_contract import SKIN_IDS

VIEW_IDS = frozenset({"dro", "gcode", "tools", "toolpath", "machine", "workpiece",
                      "alarms", "cycle", "manual", "diagnostics"})
GLOBAL_IDS = frozenset({"alarms", "estop_status", "stop", "feed_hold", "mode"})


def _strings(value, allowed, field):
    if (not isinstance(value, list) or not value
            or any(not isinstance(item, str) or item not in allowed for item in value)
            or len(set(value)) != len(value)):
        raise ValueError(f"Invalid {field}")
    return tuple(value)


@dataclass(frozen=True)
class SkinManifest:
    """Validated metadata only. No paths, imports or executable entry points."""

    skin: str
    version: str
    views: tuple[str, ...]
    global_controls: tuple[str, ...]
    resolutions: tuple[tuple[int, int], ...]
    api: int = 1

    @classmethod
    def from_json(cls, text: str):
        data = json.loads(text)
        fields = {"skin", "version", "api", "views", "global_controls", "resolutions"}
        if not isinstance(data, dict) or set(data) != fields:
            raise ValueError("Invalid manifest fields")
        if type(data["api"]) is not int or data["api"] != 1:
            raise ValueError("Unsupported skin API")
        if not isinstance(data["skin"], str) or data["skin"] not in SKIN_IDS:
            raise ValueError("Unsupported skin")
        version = data["version"]
        if (not isinstance(version, str) or len(version.split(".")) != 3
                or any(not part.isascii() or not part.isdigit() for part in version.split("."))):
            raise ValueError("Expected numeric major.minor.patch version")
        views = _strings(data["views"], VIEW_IDS, "views")
        controls = _strings(data["global_controls"], GLOBAL_IDS, "global_controls")
        if set(views) != VIEW_IDS or set(controls) != GLOBAL_IDS:
            raise ValueError("Missing required views or global controls")
        resolutions = data["resolutions"]
        if (not isinstance(resolutions, list) or not resolutions
                or any(not isinstance(size, list) or len(size) != 2
                       or any(type(n) is not int or n <= 0 for n in size)
                       for size in resolutions)):
            raise ValueError("Invalid resolutions")
        sizes = tuple(tuple(size) for size in resolutions)
        if len(set(sizes)) != len(sizes) or not {(1280, 800), (1920, 1080)} <= set(sizes):
            raise ValueError("Required resolutions: 1280x800 and 1920x1080")
        return cls(data["skin"], version, views, controls, sizes)


@dataclass(frozen=True)
class SwitchSnapshot:
    """A controller adapter must explicitly supply every switch precondition.

    sampled_at and now use the same local monotonic clock. 'stopped' includes
    axes and spindle. An idle interpreter alone does not imply no JOG/homing.
    """

    sampled_at: float
    connected: bool
    stopped: bool
    interpreter_idle: bool
    queue_empty: bool
    homing: bool
    command_pending: bool


@dataclass(frozen=True)
class SwitchDecision:
    allowed: bool
    reason: str


def switch_gate(snapshot: SwitchSnapshot | None, now: float) -> SwitchDecision:
    """Evaluate presentation replacement only; never stops/resets the machine."""
    if snapshot is None:
        return SwitchDecision(False, "status_unavailable")
    times = (snapshot.sampled_at, now)
    if any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in times):
        return SwitchDecision(False, "invalid_timestamp")
    age = now - snapshot.sampled_at
    if age < 0 or age > 0.5:
        return SwitchDecision(False, "status_stale")
    flags = (snapshot.connected, snapshot.stopped, snapshot.interpreter_idle,
             snapshot.queue_empty, snapshot.homing, snapshot.command_pending)
    if any(type(flag) is not bool for flag in flags):
        return SwitchDecision(False, "status_unavailable")
    for confirmed, reason in ((snapshot.connected, "status_unavailable"),
                              (snapshot.interpreter_idle, "program_active"),
                              (snapshot.queue_empty, "motion_queued"),
                              (snapshot.stopped, "motion_active"),
                              (not snapshot.homing, "homing_active"),
                              (not snapshot.command_pending, "command_pending")):
        if not confirmed:
            return SwitchDecision(False, reason)
    return SwitchDecision(True, "stopped_and_idle")
