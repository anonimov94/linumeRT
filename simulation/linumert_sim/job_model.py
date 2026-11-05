"""Strict diagnostic models built only from immutable job resources.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

No drive-library lookup, generic holder, substitute cutter or default drive force
may silently turn incomplete input into a positive job diagnostic.
"""

import math

from linumert.machine.schema import MachineConfig
from linumert.tools.db import Tool

from .cutter import make_cutter
from .machine import Body, Machine, _axis_force


def frozen_machine(config: MachineConfig, drives: dict) -> Machine:
    expected = {d.name: d for d in config.drives}
    if set(drives) != set(expected):
        raise ValueError("Snapshot napędów nie odpowiada maszynie zadania")
    for key, row in drives.items():
        if row["template"] != expected[key].template:
            raise ValueError(f"Niezgodny szablon snapshotu napędu {key}")
    model = Machine(name=config.machine.name, path="job:machine.yaml+drives.json")
    for axis in config.axes:
        forces = [_axis_force(drives[key]["parameters"]) for key in axis.drives]
        if not forces or any(f is None or not math.isfinite(f) or f <= 0 for f in forces):
            raise ValueError(f"Oś {axis.letter}: snapshot nie określa siły wszystkich napędów")
        model.axis_force[axis.letter] = sum(forces)
        model.travel[axis.letter] = axis.travel
    spindle = config.spindle
    if spindle is None or spindle.drive not in drives:
        raise ValueError("Brak napędu wrzeciona w snapshotcie")
    curve = drives[spindle.drive]["parameters"].get("motor", {}).get("torque_curve", [])
    if (len(curve) < 2 or any(len(p) != 2 or any(not math.isfinite(v) or v < 0 for v in p)
                              for p in curve)
            or any(a[0] >= b[0] for a, b in zip(curve, curve[1:], strict=False))):
        raise ValueError("Brak poprawnej krzywej momentu wrzeciona w snapshotcie")
    model.spindle_curve = [(float(w), float(t)) for w, t in curve]
    model.spindle_max_rpm = spindle.max_rpm
    for body in config.collision_bodies:
        if body.attached_to in ("head", "spindle") and (
                body.shape != "cylinder" or any(abs(v) > 1e-6 for v in body.position[:2])):
            raise ValueError(f"Bryła {body.name}: diagnostyka wymaga współosiowego walca ruchomego")
        # Offline CAM is not a probing or magazine exchange operation. Contact
        # with these declared bodies must not use the live engine's exemptions.
        attached = "table" if body.attached_to in ("toolsetter", "magazine") else body.attached_to
        model.bodies.append(Body(body.name, body.shape, attached,
                                 tuple(body.size), body.position))
    if not any(b.moving for b in model.bodies) or not any(not b.moving for b in model.bodies):
        raise ValueError("Model zadania wymaga jawnych brył ruchomych i stałych")
    # Declared forbidden volumes are obstacles too, including the full tool and
    # spindle envelope, rather than a test of the spindle nose alone.
    for zone in config.forbidden_zones:
        model.bodies.append(Body(zone.name, "box", "table",
            tuple(b - a for a, b in zip(zone.min, zone.max, strict=True)),
            tuple((a + b) / 2 for a, b in zip(zone.min, zone.max, strict=True))))
    return model


def frozen_cutters(rows: list[dict]) -> dict:
    cutters = {}
    for row in rows:
        tool = Tool(**row)
        p = tool.params
        prefix = f"T{tool.number}: "
        if tool.type not in ("flat", "drill_118"):
            raise ValueError(prefix + "pełny profil tego typu nie jest jeszcze obsługiwany")
        required = ("d", "l", "flute_length", "holder_d", "holder_l", "flutes", "max_rpm", "hand")
        if any(k not in p or isinstance(p[k], bool) or not math.isfinite(p[k]) for k in required):
            raise ValueError(prefix + "wymagane jawne wymiary ostrza/oprawki, "
                             "liczba ostrzy, kierunek i RPM")
        gauge = tool.offsets.get("Z", 0)
        if (any(abs(v) > 1e-6 for k, v in tool.offsets.items() if k != "Z")
                or not math.isfinite(gauge) or gauge <= 0):
            raise ValueError(prefix + "wymagana dodatnia długość Z bez innych korekcji")
        if (any(p[k] <= 0 for k in required if k != "hand")
                or p["flutes"] != int(p["flutes"]) or p["hand"] not in (-1, 1)
                or p["flute_length"] > p["l"] or p["holder_d"] < p["d"]
                or abs(p["l"] + p["holder_l"] - gauge) > 1e-6
                or abs(p.get("d_wear", 0)) > 1 or tool.tool_diameter() < 0.1):
            raise ValueError(prefix + "niespójne wymiary ostrza/oprawki lub długość Z")
        cutter = make_cutter(tool.number, gauge, tool.tool_diameter(), tool.type, p)
        if cutter.cut_top > p["flute_length"] + 1e-6:
            raise ValueError(prefix + "część tnąca nie obejmuje wierzchołka wiertła")
        if tool.number in cutters:
            raise ValueError(prefix + "powtórzony numer narzędzia")
        cutters[tool.number] = cutter
    return cutters
