"""Conservative continuous sweeps against every declared fixed machine body.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

Expanded boxes enclose cylinder/box contact. This may report a possible collision
near a rounded corner; it cannot skip a thin obstacle between sampled positions.
For arcs, the caller inflates each chord by its maximum deviation.
"""

from .engine import Event
from .machine import FIXTURE


def _entry(a, b, lo, hi):
    first, last = 0.0, 1.0
    for x, y, low, high in zip(a, b, lo, hi, strict=True):
        delta = y - x
        if delta == 0:
            if x < low or x > high:
                return None
        else:
            p, q = sorted(((low - x) / delta, (high - x) / delta))
            first, last = max(first, p), min(last, q)
            if first > last:
                return None
    return first


def sweep(machine, cutter, a, b, *, line, tool, inflation=0.0):
    parts = []
    gauge = cutter.gauge if cutter else 0.0
    if cutter:
        parts = [("narzedzie", cutter.radius, -gauge, cutter.cut_top - gauge, 0, 0)]
        parts += [(name, r, z0 - gauge, z1 - gauge, 0, 0)
                  for name, r, z0, z1 in cutter.parts()]
    for body in machine.bodies:
        if body.moving:
            z0, z1 = body.z_range()
            parts.append((body.name, body.size[0] / 2, z0, z1, *body.position[:2]))
    events = []
    for name, r, z0, z1, ox, oy in parts:
        for body in machine.bodies:
            if body.moving:
                continue
            sx, sy = body.size[:2] if body.shape == "box" else (body.size[0],) * 2
            bx, by, _ = body.position
            bz0, bz1 = body.z_range()
            lo = (bx - sx / 2 - r - ox - inflation,
                  by - sy / 2 - r - oy - inflation, bz0 - z1 - inflation)
            hi = (bx + sx / 2 + r - ox + inflation,
                  by + sy / 2 + r - oy + inflation, bz1 - z0 + inflation)
            at = _entry(a, b, lo, hi)
            if at is None:
                continue
            nose = tuple(x + (y - x) * at for x, y in zip(a, b, strict=True))
            code = "K-304" if body.attached in FIXTURE else "K-305"
            event = Event(code, "collision", line, tool, (nose[0], nose[1], nose[2] - gauge),
                          {"line": line, "tool": tool, "element": f"{name} – {body.name}"},
                          (name, body.name)).to_dict()
            event["conservative"] = True
            event["text"] += " (konserwatywna obwiednia przejazdu)"
            events.append(event)
    return events
