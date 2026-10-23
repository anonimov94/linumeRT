# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only LinuxCNC 2.9 status boundary, no Qt/ACTION/HAL. Model-Author: Codex.

The worker is disposable: an early failed tool mmap in LinuxCNC 2.9 must not
poison the monitor process. No error_channel reader: it would consume HMI errors.
Acquisition time is NOT a controller heartbeat (2.9 stat has none).
"""

import json
import math
import time
from dataclasses import dataclass
from typing import Protocol

AXES = "XYZABCUVW"
MAX_AGE = 0.5


class StatusPort(Protocol):
    actual_position: tuple[float, ...]
    linear_units: float
    angular_units: float
    axis_mask: int
    task_mode: int
    task_state: int
    interp_state: int
    estop: int
    enabled: bool

    def poll(self) -> None: ...


@dataclass(frozen=True)
class MachineSample:
    acquired_at: float
    # Absolute trajectory position in machine coordinates, NOT work/DRO offsets.
    positions: tuple[float | None, ...]
    mode: str
    task: str
    interpreter: str
    estop: bool
    enabled: bool

    def fresh(self, now: float) -> bool:
        return 0 <= now - self.acquired_at <= MAX_AGE


def number(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("invalid finite number")
    return float(value)


def read_status(status: StatusPort, api: object) -> dict:
    """Copy one polled NML status into JSON primitives, normalized to mm/degrees."""
    status.poll()
    linear, angular = number(status.linear_units), number(status.angular_units)
    if linear <= 0 or angular <= 0:
        raise ValueError("invalid machine units")
    mask = status.axis_mask
    if type(mask) is not int or not 0 < mask < 512:
        raise ValueError("invalid axis mask")
    if len(status.actual_position) != 9:
        raise ValueError("invalid position vector")
    positions = [number(v) / (angular if a in "ABC" else linear)
                 if mask & (1 << i) else None
                 for i, (a, v) in enumerate(zip(AXES, status.actual_position, strict=True))]
    if type(status.estop) not in (bool, int) or status.estop not in (0, 1):
        raise ValueError("invalid estop")
    if type(status.enabled) not in (bool, int) or status.enabled not in (0, 1):
        raise ValueError("invalid enable")
    def enum(field, names):
        value = getattr(status, field)
        if type(value) is not int:
            raise ValueError("invalid " + field)
        for name in names:
            if value == getattr(api, name):
                return name
        raise ValueError("unknown " + field)
    return dict(
        acquired_at=time.monotonic(), positions=positions,
        mode=enum("task_mode", ("MODE_MANUAL", "MODE_MDI", "MODE_AUTO")),
        task=enum("task_state", ("STATE_ESTOP", "STATE_ESTOP_RESET", "STATE_OFF", "STATE_ON")),
        interpreter=enum("interp_state", ("INTERP_IDLE", "INTERP_READING", "INTERP_PAUSED",
                                         "INTERP_WAITING")),
        estop=bool(status.estop), enabled=bool(status.enabled))


def decode_sample(payload: bytes, now: float) -> MachineSample:
    if len(payload) > 4096:
        raise ValueError("oversized status")
    data = json.loads(payload)
    if set(data) != set(MachineSample.__dataclass_fields__):
        raise ValueError("invalid status fields")
    positions = data["positions"]
    if not isinstance(positions, list) or len(positions) != 9:
        raise ValueError("invalid position vector")
    data["positions"] = tuple(None if v is None else number(v) for v in positions)
    data["acquired_at"] = number(data["acquired_at"])
    for field, choices in (
        ("mode", ("MODE_MANUAL", "MODE_MDI", "MODE_AUTO")),
        ("task", ("STATE_ESTOP", "STATE_ESTOP_RESET", "STATE_OFF", "STATE_ON")),
        ("interpreter", ("INTERP_IDLE", "INTERP_READING", "INTERP_PAUSED", "INTERP_WAITING")),
    ):
        if data[field] not in choices:
            raise ValueError("invalid " + field)
    if type(data["estop"]) is not bool or type(data["enabled"]) is not bool:
        raise ValueError("invalid boolean status")
    result = MachineSample(**data)
    if not result.fresh(now):
        raise ValueError("expired status")
    return result


if __name__ == "__main__":
    import linuxcnc

    # One fresh channel, one read, then exit. Never construct a command channel.
    print(json.dumps(read_status(linuxcnc.stat(), linuxcnc), allow_nan=False))
