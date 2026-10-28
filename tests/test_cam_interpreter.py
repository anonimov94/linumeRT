# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile new paths and ask real LinuxCNC rs274 to interpret. Model-Author: Codex."""
import json

import pytest
from linumert.generators import engraving, shapes, stl_trace, surfacing
from linumert.generators.registry import GeneratorRegistry
from linumert.programs.compiler import compile_program
from linumert.programs.linuxcnc_check import run_interpreter
from linumert.programs.lnx import LnxProgram, Step


@pytest.mark.linuxcnc
@pytest.mark.parametrize("kind", ["zigzag", "one_way", "crosshatch", "concentric",
                                 "rectangle", "rounded_rectangle", "ellipse", "star",
                                 "text", "stl"])
def test_new_cam_paths_in_real_interpreter(tmp_path, kind):
    registry = GeneratorRegistry()
    for group in (engraving, shapes, stl_trace, surfacing):
        group.register(registry)
    if kind in ("zigzag", "one_way", "crosshatch", "concentric"):
        gen = surfacing.FaceMillStrategies()
        params = {"mode": kind, "axis": "Y", "x1": 30, "y1": 20, "tool_d": 8, "depth": 0.5}
    elif kind in ("text", "stl"):
        gen = engraving.EngraveText() if kind == "text" else stl_trace.StlSection()
        params = {"paths": json.dumps([[[0, 0], [10, 0], [10, 10], [0, 0]]])}
    else:
        gen = shapes.ShapeEngrave()
        params = {"shape": kind, "strategy": "outline_hatch", "spacing": 3, "depth": 0.5}
    program = LnxProgram(name="CAM", steps=[Step(generator=gen.name, version=gen.version,
                                                params=params)])
    path = tmp_path / "cam.ngc"
    path.write_text(compile_program(program, registry), encoding="utf-8")
    result = run_interpreter(path)
    assert result.returncode == 0 and "PROGRAM_END()" in result.stdout, result.stderr
    assert "STRAIGHT_FEED" in result.stdout
