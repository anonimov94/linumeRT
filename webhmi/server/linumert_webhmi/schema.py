"""Schemat stanu (JSON dla przeglądarki) i polecenia bramy web.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Wersja schematu ``SCHEMA_VERSION`` rośnie przy każdej zmianie niezgodnej wstecz; przeglądarka
sprawdza ją przy połączeniu. Wartości nieskończone (limity programowe bez ograniczenia) idą
jako ``null``, bo JSON nie zna ``inf``.
"""

from __future__ import annotations

import math
from typing import Literal

from linumert.cnc import MachineSnapshot
from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = 1
MAX_MDI_CHARS = 200
MAX_JOG_SPEED_MM_S = 50.0  # górna granica jogu z przeglądarki (3000 mm/min)
AXIS = Literal["X", "Y", "Z", "A", "B", "C", "U", "V", "W"]


def _num(value: float) -> float | None:
    return value if math.isfinite(value) else None


def snapshot_to_dict(snap: MachineSnapshot) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "task_state": snap.task_state.value,
        "mode": snap.mode.value,
        "interp_state": snap.interp_state.value,
        "axes": [
            {
                "name": a.name,
                "position": round(a.position, 4),
                "work_position": round(snap.work_position(a.name), 4),
                "following_error": round(a.following_error, 4),
                "homed": a.homed,
                "soft_min": _num(a.soft_min),
                "soft_max": _num(a.soft_max),
                "limit_hit": a.limit_hit,
            }
            for a in snap.axes
        ],
        "all_homed": snap.all_homed,
        "line": snap.current_line,
        "program": snap.program_file,
        "feed_override": snap.feed_override,
        "rapid_override": snap.rapid_override,
        "spindle_override": snap.spindle_override,
        "spindle_speed": snap.spindle_speed,
        "spindle_direction": snap.spindle_direction,
        "tool": snap.tool_number,
        "work_offset": snap.work_offset_name,
        "gcodes": list(snap.active_gcodes),
        "mcodes": list(snap.active_mcodes),
        "errors": list(snap.errors),
    }


class Command(BaseModel):
    """Polecenie z przeglądarki; pole ``cmd`` wybiera akcję, reszta to jej argumenty."""

    cmd: Literal["estop", "power_on", "power_off", "mode", "home", "mdi", "run", "pause",
                 "resume", "stop", "override", "jog", "jog_stop"]
    mode: Literal["manual", "mdi", "auto"] | None = None
    axis: AXIS | None = None
    text: str | None = Field(default=None, max_length=MAX_MDI_CHARS)
    from_line: int = Field(default=1, ge=1, le=10_000_000)
    feed: float | None = Field(default=None, ge=0.0, le=2.0)
    rapid: float | None = Field(default=None, ge=0.0, le=1.0)
    spindle: float | None = Field(default=None, ge=0.0, le=2.0)
    speed: float | None = None  # mm/s ze znakiem (jog)

    @field_validator("text")
    @classmethod
    def _single_line(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("MDI: jedna niepusta linia bez znaków sterujących")
        return value

    @field_validator("speed")
    @classmethod
    def _finite_speed(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value)
                                  or abs(value) > MAX_JOG_SPEED_MM_S):
            raise ValueError(f"prędkość jogu w zakresie ±{MAX_JOG_SPEED_MM_S:g} mm/s")
        return value
