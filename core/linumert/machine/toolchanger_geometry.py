"""Shared tool pocket geometry for Plant and the ATC generator.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude (original Plant geometry), Codex (shared core extraction).
"""

from __future__ import annotations

import math

from .schema import ToolChanger


def pocket_positions(tc: ToolChanger) -> list[tuple[float, float, float]]:
    """G53 spindle-nose positions; explicit pockets override base and pitch."""
    if tc.type == "manual" or tc.slots == 0:
        return []
    if tc.slot_positions is not None:
        pts = [tuple(float(v) for v in p) for p in tc.slot_positions]
    else:
        bx, by, bz = tc.base_position
        if tc.type == "rack_linear":
            a = math.radians(tc.base_orientation_deg)
            pts = [(bx + i * tc.pitch_mm * math.cos(a), by + i * tc.pitch_mm * math.sin(a), bz)
                   for i in range(tc.slots)]
        else:  # Each carousel/umbrella pocket indexes to one exchange position.
            pts = [(bx, by, bz)] * tc.slots
    if tc.approach_z is not None:
        pts = [(x, y, float(tc.approach_z)) for x, y, _ in pts]
    return [(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in pts]
