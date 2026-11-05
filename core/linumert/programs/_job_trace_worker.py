"""Single-use, private LinuxCNC gcode.parse worker, including actual T/M6/G43.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

Never import this into a live interpreter process. The parent supplies a private
HOME/TMPDIR/cwd; the optional C++ bridge loads only that job's tool.tbl. No NML/HAL.
"""

from __future__ import annotations

import ctypes
import json
import math
import os
import sys
from pathlib import Path

from .linuxcnc_check import limit_worker_lifetime

INCH = 25.4
MAX_CALLS = 100_000


class Tools:
    def __init__(self, library: str, table: str):
        self.lib = ctypes.CDLL(library)
        self.lib.lrt_tooldata_bridge_abi.argtypes = []
        self.lib.lrt_tooldata_bridge_abi.restype = ctypes.c_int
        if self.lib.lrt_tooldata_bridge_abi() != 1:
            raise RuntimeError("Niezgodne ABI prywatnej tabeli LinuxCNC")
        self.lib.lrt_tooldata_open.argtypes = [ctypes.c_char_p]
        self.lib.lrt_tooldata_open.restype = ctypes.c_int
        self.lib.lrt_tooldata_read.argtypes = [ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_int32)]
        self.lib.lrt_tooldata_read.restype = ctypes.c_int
        self.lib.lrt_tooldata_close.argtypes = []
        self.lib.lrt_tooldata_close.restype = None
        if self.lib.lrt_tooldata_open(str(table).encode()):
            raise RuntimeError("Nie można otworzyć prywatnej tabeli LinuxCNC")

    def read(self, pocket: int):
        number, orientation = ctypes.c_int32(), ctypes.c_int32()
        values = (ctypes.c_double * 12)()
        if self.lib.lrt_tooldata_read(pocket, ctypes.byref(number), values,
                                      ctypes.byref(orientation)):
            raise ValueError(f"Nie można odczytać kieszeni {pocket} prywatnej tabeli")
        # gcodemodule's GET_EXTERNAL_LENGTH_UNIT_TYPE is always INCHES.
        # Its get_tool API uses inches, unlike the job's mm tooldata mmap.
        out = list(values)
        for index in (0, 1, 2, 6, 7, 8, 9):
            out[index] /= INCH
        return (number.value, *out, orientation.value)

    def close(self):
        self.lib.lrt_tooldata_close()


def _mm(values):
    return [v * INCH if i in (0, 1, 2, 6, 7, 8) else v
            for i, v in enumerate(values)]


class Canon:
    """Normalize LinuxCNC callback doubles to mm, retaining tool and source line."""

    def __init__(self, table: Tools, parameters: str):
        self.table = table
        self.parameter_file = parameters
        self.line = 0
        self.tool = 0
        self.rpm = 0.0
        self.feed = 0.0
        self.calls = []
        self.motions = []
        self._emit("USE_LENGTH_UNITS", ["CANON_UNITS_MM"])

    def _emit(self, name, args):
        if len(self.calls) >= MAX_CALLS:
            raise ValueError("Przekroczono limit zdarzeń dokładnego toru")
        if any(isinstance(v, (int, float)) and not math.isfinite(v) for v in args):
            raise ValueError("Nieskończona współrzędna z interpretera")
        self.calls.append({"line": self.line, "name": name, "args": list(args)})

    def get_tool(self, pocket):
        return self.table.read(pocket)

    def get_external_length_units(self):
        return 1 / INCH

    def get_external_angular_units(self):
        return 1.0

    def get_axis_mask(self):
        return 7

    def get_block_delete(self):
        return False

    def check_abort(self):
        return False

    def next_line(self, state):
        self.line = int(state.sequence_number)
        self.rpm = {3: 1, 4: -1}.get(state.spindle, 0) * state.speed

    def set_plane(self, plane):
        name = {1: "CANON_PLANE_XY", 2: "CANON_PLANE_XZ", 3: "CANON_PLANE_YZ"}[plane]
        self._emit("SELECT_PLANE", [name])

    def set_g5x_offset(self, index, *values):
        self._emit("SET_G5X_OFFSET", [index, *_mm(values)])

    def set_g92_offset(self, *values):
        self._emit("SET_G92_OFFSET", _mm(values))

    def set_xy_rotation(self, angle):
        self._emit("SET_XY_ROTATION", [angle])

    def tool_offset(self, *values):
        self._emit("USE_TOOL_LENGTH_OFFSET", _mm(values))

    def change_tool(self, pocket):
        self.tool = self.table.read(pocket)[0]
        if self.tool < 0:
            raise ValueError(f"Nieznane narzędzie po M6, kieszeń {pocket}")
        self._emit("CHANGE_TOOL", [self.tool])

    def set_feed_rate(self, feed):
        self.feed = feed * INCH
        self._emit("SET_FEED_RATE", [self.feed])

    def dwell(self, seconds):
        self._emit("DWELL", [seconds])

    def _motion(self, name, values):
        # gcode.parse is LinuxCNC's preview interface and permits a zero feed.
        # Such an event cannot supply a valid diagnostic time/load calculation.
        if name != "STRAIGHT_TRAVERSE" and self.feed <= 0:
            raise ValueError(f"linia {self.line}: ruch roboczy bez dodatniego posuwu")
        self._emit(name, values)
        self.motions.append({"line": self.line, "name": name, "args": values,
                             "tool": self.tool, "rpm": self.rpm, "feed": self.feed})

    def straight_traverse(self, *values):
        self._motion("STRAIGHT_TRAVERSE", _mm(values))

    def straight_feed(self, *values):
        self._motion("STRAIGHT_FEED", _mm(values))

    def arc_feed(self, *values):
        args = [v * INCH if i in (0, 1, 2, 3, 5, 9, 10, 11) else v
                for i, v in enumerate(values)]
        self._motion("ARC_FEED", args)

    def comment(self, *args):
        pass

    message = comment
    set_traverse_rate = comment

    def canonical_text(self):
        def argument(value):
            return value if isinstance(value, str) else format(value, ".17g")
        return "".join(f"{i} N{c['line']} {c['name']}(" +
                       ", ".join(map(argument, c["args"])) + ")\n"
                       for i, c in enumerate(self.calls, 1))


def main(argv):
    config, = argv
    data = json.loads(Path(config).read_text(encoding="utf-8"))
    limit_worker_lifetime(str(data["timeout"]))
    os.nice(10)  # Diagnostic work stays outside the control/GUI scheduling priority.
    import gcode  # type: ignore[import-not-found]

    table = Tools(data["library"], data["table"])
    try:
        canon = Canon(table, data["parameters"])
        result, line = gcode.parse(data["program"], canon, data["initcodes"])
        # INTERP_EXIT (1), not EOF (2): require an executed M2/M30.
        if result != 1:
            raise ValueError(f"linia {line}: interpreter nie zakończył programu "
                             f"({gcode.strerror(result)})")
        print(json.dumps({"format": "linumert.job.trace", "version": 1,
                          "source": "linuxcnc.gcode", "module": str(gcode.__file__),
                          "completed": True, "calls": canon.calls, "motions": canon.motions,
                          "canonical": canon.canonical_text()}, allow_nan=False))
    finally:
        table.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, ValueError, AttributeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(3) from None
