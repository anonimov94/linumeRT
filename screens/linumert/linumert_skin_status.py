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
MAX_PAYLOAD = 16384
MAX_PATH = 4096


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
    # Classic × Neon (Claude, 2026-10-24): program i pozycja na ścieżce, tylko odczyt.
    file: str
    motion_line: int
    g5x_offset: tuple[float, ...]
    g92_offset: tuple[float, ...]
    tool_offset: tuple[float, ...]
    rotation_xy: float
    distance_to_go: float
    dtg: tuple[float, ...]

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
    # Program i ścieżka (mm, XYZ). Pozycja w układzie detalu = G53 − g5x − g92 − tool_offset
    # (obrót XY pominięty w podglądzie). NIEZWERYFIKOWANE NA SPRZĘCIE.
    file: str = ""
    motion_line: int = 0
    g5x_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    g92_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    tool_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_xy: float = 0.0
    distance_to_go: float = 0.0
    dtg: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def work_position(self) -> tuple[float, float, float] | None:
        if any(v is None for v in self.positions[:3]):
            return None
        return tuple(p - a - b - c for p, a, b, c in zip(
            self.positions[:3], self.g5x_offset, self.g92_offset, self.tool_offset, strict=True))

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
    def xyz(field):
        values = getattr(status, field)
        if len(values) < 3:
            raise ValueError("invalid " + field)
        return [number(v) / linear for v in values[:3]]
    path = status.file
    if type(path) is not str or len(path) > MAX_PATH or "\x00" in path:
        raise ValueError("invalid file")
    line = status.motion_line
    if type(line) is not int or line < 0:
        raise ValueError("invalid motion_line")
    return dict(
        file=path, motion_line=line, g5x_offset=xyz("g5x_offset"),
        g92_offset=xyz("g92_offset"), tool_offset=xyz("tool_offset"),
        rotation_xy=number(status.rotation_xy),
        distance_to_go=number(status.distance_to_go) / linear, dtg=xyz("dtg"),
        acquired_at=time.monotonic(), positions=positions,
        mode=enum("task_mode", ("MODE_MANUAL", "MODE_MDI", "MODE_AUTO")),
        task=enum("task_state", ("STATE_ESTOP", "STATE_ESTOP_RESET", "STATE_OFF", "STATE_ON")),
        interpreter=enum("interp_state", ("INTERP_IDLE", "INTERP_READING", "INTERP_PAUSED",
                                         "INTERP_WAITING")),
        estop=bool(status.estop), enabled=bool(status.enabled))


def decode_sample(payload: bytes, now: float) -> MachineSample:
    if len(payload) > MAX_PAYLOAD:
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
    if type(data["file"]) is not str or len(data["file"]) > MAX_PATH or "\x00" in data["file"]:
        raise ValueError("invalid file")
    if type(data["motion_line"]) is not int or data["motion_line"] < 0:
        raise ValueError("invalid motion_line")
    for field in ("g5x_offset", "g92_offset", "tool_offset", "dtg"):
        values = data[field]
        if not isinstance(values, list) or len(values) != 3:
            raise ValueError("invalid " + field)
        data[field] = tuple(number(v) for v in values)
    data["rotation_xy"] = number(data["rotation_xy"])
    data["distance_to_go"] = number(data["distance_to_go"])
    result = MachineSample(**data)
    if not result.fresh(now):
        raise ValueError("expired status")
    return result


if __name__ == "__main__":
    import linuxcnc

    # One fresh channel, one read, then exit. Never construct a command channel.
    print(json.dumps(read_status(linuxcnc.stat(), linuxcnc), allow_nan=False))
