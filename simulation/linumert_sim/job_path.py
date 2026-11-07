"""Diagnostic geometry from executed LinuxCNC callbacks, never from G-code text.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

Coordinates remain float64 mm. Offset/TLO changes preserve the physical spindle
nose; the synthetic line-zero move initializes it without sweeping through stock.
This is an offline material sampler, not an execution planner.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from linumert.programs.limits import EPS, _arc_candidates

MOTION = {"STRAIGHT_TRAVERSE", "STRAIGHT_FEED", "ARC_FEED"}
PLANES = {"CANON_PLANE_XY": (0, 1, 2), "CANON_PLANE_XZ": (2, 0, 1),
          "CANON_PLANE_YZ": (1, 2, 0)}


def _xyz(values):
    if len(values) != 9 or any(not math.isfinite(v) for v in values):
        raise ValueError("Niepełne współrzędne dokładnego toru XYZ")
    if any(abs(v) > EPS for v in values[3:]):
        raise ValueError("Diagnostyka materiału obsługuje wyłącznie XYZ")
    return tuple(values[:3])


@dataclass(frozen=True)
class Frame:
    g5x: tuple = (0.0, 0.0, 0.0)
    g92: tuple = (0.0, 0.0, 0.0)
    tlo: tuple = (0.0, 0.0, 0.0)
    rotation: float = 0.0

    def machine(self, p):
        x, y, z = (p[i] + self.g92[i] for i in range(3))
        a = math.radians(self.rotation)
        q = (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z)
        return tuple(q[i] + self.g5x[i] + self.tlo[i] for i in range(3))

    def program(self, p):
        x, y, z = (p[i] - self.g5x[i] - self.tlo[i] for i in range(3))
        a = math.radians(self.rotation)
        q = (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a), z)
        return tuple(q[i] - self.g92[i] for i in range(3))


@dataclass(frozen=True)
class Segment:
    line: int
    tool: int
    rpm: float
    feed: float                 # mm/min, unused for rapid
    rapid: bool
    start: tuple               # spindle nose in machine coordinates
    end: tuple
    length: float
    frame: Frame
    program_start: tuple
    program_end: tuple
    plane: tuple = (0, 1, 2)
    center: tuple | None = None
    radius: float = 0.0
    angle: float = 0.0
    sweep: float = 0.0         # signed radians

    def point(self, fraction):
        if fraction == 1:
            return self.end
        p = [a + (b - a) * fraction
             for a, b in zip(self.program_start, self.program_end, strict=True)]
        if self.center is not None:
            first, second, _ = self.plane
            a = self.angle + self.sweep * fraction
            p[first] = self.center[0] + self.radius * math.cos(a)
            p[second] = self.center[1] + self.radius * math.sin(a)
        return self.frame.machine(p)

    def sample_count(self, seconds, *, step_mm=0.25, dt=0.05, chord_mm=0.005):
        count = max(1, math.ceil(self.length / step_mm), math.ceil(seconds / dt))
        if self.center is not None:
            step = min(math.pi / 4, 2 * math.acos(max(-1, 1 - chord_mm / self.radius)))
            count = max(count, math.ceil(abs(self.sweep) / step))
        if count > 1_000_000:
            raise ValueError(f"linia {self.line}: przekroczony limit próbek diagnostyki")
        return count


def segments(trace, start_mm):
    """Yield every real motion, preserving frames and executed tool selection.

    The caller obtains this trace only after job integrity, rs274 semantics and
    cross-interface agreement. Malformed/unsupported callbacks fail explicitly.
    """
    if (trace.get("format") != "linumert.job.trace" or trace.get("version") != 1
            or trace.get("completed") is not True or trace.get("source") != "linuxcnc.gcode"):
        raise ValueError("Brak kompletnego dokładnego toru LinuxCNC")
    frame = Frame()
    position = (0.0, 0.0, 0.0)
    plane = (0, 1, 2)
    tool = 0
    index = 0
    initialized = False
    began = False
    for call in trace["calls"]:
        name, args, line = call["name"], call["args"], call["line"]
        if not isinstance(line, int) or line < 0:
            raise ValueError("Zdarzenie bez numeru linii źródłowej")
        if name in ("SET_G5X_OFFSET", "SET_G92_OFFSET", "USE_TOOL_LENGTH_OFFSET",
                    "SET_XY_ROTATION"):
            nose = frame.machine(position)
            fields = dict(g5x=frame.g5x, g92=frame.g92, tlo=frame.tlo, rotation=frame.rotation)
            if name == "SET_XY_ROTATION":
                if len(args) != 1 or not math.isfinite(args[0]):
                    raise ValueError("Niepoprawny obrót układu detalu")
                fields["rotation"] = args[0]
            else:
                key = {"SET_G5X_OFFSET": "g5x", "SET_G92_OFFSET": "g92",
                       "USE_TOOL_LENGTH_OFFSET": "tlo"}[name]
                fields[key] = _xyz(args[1:] if name == "SET_G5X_OFFSET" else args)
            frame = Frame(**fields)
            position = frame.program(nose)
        elif name == "SELECT_PLANE":
            if len(args) != 1 or args[0] not in PLANES:
                raise ValueError("Nieobsługiwana płaszczyzna łuku")
            plane = PLANES[args[0]]
        elif name == "USE_LENGTH_UNITS":
            if args != ["CANON_UNITS_MM"]:
                raise ValueError("Dokładny tor materiału wymaga współrzędnych mm")
        elif name == "CHANGE_TOOL":
            tool, = args
        elif name == "SET_FEED_RATE":
            pass  # executed feed is attached to each motion by the callback receiver
        elif name == "DWELL":
            raise ValueError(f"linia {line}: czas postoju nie jest jeszcze obsługiwany")
        elif name in MOTION:
            if index >= len(trace["motions"]):
                raise ValueError("Brak metadanych ruchu dokładnego toru")
            motion = trace["motions"][index]
            index += 1
            if any(motion[k] != call[k] for k in ("name", "args", "line")):
                raise ValueError(f"linia {line}: niezgodne metadane ruchu")
            if (motion["tool"] != tool or not isinstance(tool, int) or tool < 0
                    or any(not math.isfinite(motion[k]) for k in ("rpm", "feed"))):
                raise ValueError(f"linia {line}: niepoprawne narzędzie/obroty/posuw")
            center, radius, angle, sweep = None, 0.0, 0.0, 0.0
            if name == "ARC_FEED":
                if len(args) != 12 or any(not math.isfinite(v) for v in args):
                    raise ValueError(f"linia {line}: niepełny łuk XYZ")
                if any(abs(v) > EPS for v in args[6:]):
                    raise ValueError("Łuk z osiami innymi niż XYZ")
                if not float(args[4]).is_integer():
                    raise ValueError("Niecałkowita liczba obrotów łuku")
                # Share strict circular-arc validation with analytical limit checks.
                end = _arc_candidates(position + (0, 0, 0), args, plane, strict=True)[-1][:3]
                first, second, spiral = plane
                center = tuple(args[2:4])
                radius = math.hypot(position[first] - center[0], position[second] - center[1])
                angle = math.atan2(position[second] - center[1], position[first] - center[0])
                finish = math.atan2(end[second] - center[1], end[first] - center[0])
                direction = 1 if args[4] > 0 else -1
                turns = abs(args[4])
                sweep = (turns * math.tau if math.hypot(end[first] - position[first],
                         end[second] - position[second]) <= EPS else
                         ((finish - angle) * direction) % math.tau + (turns - 1) * math.tau)
                sweep *= direction
                length = math.hypot(radius * sweep, end[spiral] - position[spiral])
            else:
                end = _xyz(args)
                length = math.dist(position, end)
            nose, target = frame.machine(position), frame.machine(end)
            if line == 0:
                if began:
                    raise ValueError("Inicjalizacja toru po rozpoczęciu programu")
                initialized = True
            else:
                if not initialized or (not began and math.dist(nose, start_mm) > EPS):
                    raise ValueError("Początek dokładnego toru nie odpowiada założonej pozycji")
                began = True
                if name != "STRAIGHT_TRAVERSE" and motion["feed"] <= 0:
                    raise ValueError(f"linia {line}: brak dodatniego posuwu")
                yield Segment(line, tool, motion["rpm"], motion["feed"],
                              name == "STRAIGHT_TRAVERSE", nose, target, length,
                              frame, position, end, plane, center, radius, angle, sweep)
            position = end
        else:
            raise ValueError(f"linia {line}: nieobsługiwane zdarzenie materiału {name}")
    if index != len(trace["motions"]) or not began:
        raise ValueError("Niekompletny strumień ruchu materiału")
