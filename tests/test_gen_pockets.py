"""Testy prototypów kieszeni M3 (sesja 041).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-20
"""

import math
import re
from pathlib import Path

import pytest
from linumert.generators.pockets import PocketCircle, PocketRect


@pytest.mark.parametrize("generator,dimensions", [
    (PocketRect, {"width": 40.0, "height": 30.0}),
    (PocketCircle, {"diameter": 40.0}),
])
def test_pocket_generates_and_retracts(generator, dimensions):
    obj = generator()
    params = {"depth": 2.0, "tool_d": 8.0, **dimensions}
    values, issues = obj.normalize(params)
    assert not issues
    assert not obj.check(values, 1)
    lines = obj.generate(values)
    assert lines[-1] == "G0 Z5"
    assert "G1 Z-2 F100" in lines
    assert obj.generate(values) == lines
    assert obj.preview_2d(values)


@pytest.mark.parametrize("generator,dimensions", [
    (PocketRect, {"width": 8.0, "height": 30.0}),
    (PocketCircle, {"diameter": 8.0}),
])
def test_pocket_rejects_tool_that_does_not_fit(generator, dimensions):
    params = {"depth": 2.0, "tool_d": 8.0, **dimensions}
    assert any(issue.field == "tool_d" for issue in generator().validate(params))


def test_circle_emits_linuxcnc_center_arc():
    obj = PocketCircle()
    values, issues = obj.normalize({"diameter": 30.0, "tool_d": 10.0, "depth": 1.0})
    assert not issues
    assert any(line.startswith("G3 ") and " I-" in line and " J0 " in line
               for line in obj.generate(values))


def test_rect_stays_within_tool_center_bounds():
    obj = PocketRect()
    values, issues = obj.normalize({"width": 40.0, "height": 20.0,
                                    "tool_d": 10.0, "depth": 1.0})
    assert not issues
    assert all(abs(x) <= 15.0 and abs(y) <= 5.0
               for path in obj.preview_2d(values) for x, y in path)


def test_pocket_rejects_unsafe_z():
    assert any(issue.field == "safe_z" for issue in PocketCircle().validate(
        {"diameter": 30.0, "tool_d": 10.0, "depth": 1.0, "safe_z": 0.0}))


@pytest.mark.parametrize("patch", [{"step_down": 0.000001}, {"step_down": 0.0001},
                                  {"safe_z": 0.00001}, {"depth": 0.000001},
                                  {"diameter": 10.00001}])
def test_rejects_excessive_output_and_geometry_lost_in_rounding(patch):
    assert PocketCircle().validate({"diameter": 100, "tool_d": 10, "depth": 10, **patch})


@pytest.mark.parametrize("cls,dims", [(PocketRect, {"width": 40, "height": 30}),
                                     (PocketCircle, {"diameter": 40})])
@pytest.mark.parametrize("stepover", [50, 90])
@pytest.mark.parametrize("entry", ["plunge", "ramp", "helix"])
def test_generated_path_removes_pocket_material_without_cutting_outside(cls, dims, stepover, entry):
    from linumert_sim.cutter import make_cutter
    from linumert_sim.zmap import StockMap

    gen = cls()
    values, issues = gen.normalize({"depth": 2, "tool_d": 8, "cx": 25, "cy": 25,
                                    "stepover": stepover, "entry": entry, **dims})
    assert not issues and not gen.check(values, 0)
    stock = StockMap("BOX", 0, 0, 50, 50, -10, 0, cell=0.25)
    tool = make_cutter(1, 80, 8, "flat", {"d": 8, "l": 40, "flute_length": 20})
    before = stock.volume()
    _cut_program(stock, tool, gen.generate(values))
    area = math.pi * 20**2 if cls is PocketCircle else 40 * 30 - (4 - math.pi) * 4**2
    assert before - stock.volume() == pytest.approx(area * 2, rel=0.025)
    assert stock.h[0, 0] == 0 and stock.h[100, 100] == -2
    _assert_floor(stock, cls, dims, 0, 2)


def _assert_floor(stock, cls, dims, wall, depth):
    import numpy as np

    x, y = np.meshgrid(stock.xs - 25, stock.ys - 25)
    angle = math.radians(dims.get("rotation", 0))
    x, y = math.cos(angle) * x + math.sin(angle) * y, -math.sin(angle) * x + math.cos(angle) * y
    if cls is PocketCircle:
        distance = np.hypot(x, y) - (dims["diameter"] / 2 - wall)
    else:
        radius = max(4, dims.get("corner_radius", 4) - wall)
        qx = np.abs(x) - (dims["width"] / 2 - wall - radius)
        qy = np.abs(y) - (dims["height"] / 2 - wall - radius)
        distance = (np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) +
                    np.minimum(np.maximum(qx, qy), 0) - radius)
    # Siatka 0,25 mm: odsuwamy asercje o jedną komórkę od obrysu.
    assert np.allclose(stock.h[distance < -stock.cell], -depth), "wyspy na dnie"
    assert np.all(stock.h[distance > stock.cell] == 0), "cięcie poza obrysem"


def _cut_program(stock, tool, lines):
    pos = (0.0, 0.0, 5.0)
    for line in lines:
        if not line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
            continue
        words = {k: float(v) for k, v in re.findall(r"([XYZIJ])(-?[0-9.]+)", line)}
        end = tuple(words.get(k, pos[i]) for i, k in enumerate("XYZ"))
        if line.startswith(("G2 ", "G3 ")):
            start = pos
            center = (pos[0] + words["I"], pos[1] + words["J"])
            radius = math.hypot(words["I"], words["J"])
            a = math.atan2(pos[1] - center[1], pos[0] - center[0])
            b = math.atan2(end[1] - center[1], end[0] - center[0])
            sign = 1 if line.startswith("G3 ") else -1
            sweep = ((sign * (b - a)) % math.tau or math.tau) * sign
            for i in range(1, 129):
                angle = a + sweep * i / 128
                point = (center[0] + radius * math.cos(angle),
                         center[1] + radius * math.sin(angle),
                         start[2] + (end[2] - start[2]) * i / 128)
                stock.cut(tool, pos, point)
                pos = point
        else:
            result = stock.cut(tool, pos, end)
            if line.startswith("G0 "):
                assert result.removed == 0, line
        pos = end


@pytest.mark.parametrize("entry", ["plunge", "ramp"])
@pytest.mark.plant
def test_rectangular_pocket_on_stepper_plant(tmp_path, entry):
    from linumert_plant.scenario import Scenario, Step, run_mock

    root = Path(__file__).resolve().parents[1]
    gen = PocketRect()
    values, issues = gen.normalize({"width": 16, "height": 12, "tool_d": 8, "depth": 1,
                                    "cx": 100, "cy": 100, "z_top": -20, "safe_z": -15,
                                    "feed": 600, "plunge": 300, "entry": entry})
    assert not issues and not gen.check(values, 0)
    path = tmp_path / "pocket.ngc"
    # Atrapa Plant nie interpretuje łuków. G91.1 nie zmienia ruchów liniowych;
    # pełny wynik obu generatorów sprawdza poniżej rzeczywisty rs274.
    path.write_text("\n".join(gen.generate(values)).replace("G91.1", "") + "\nM2\n")
    scenario = Scenario("pocket_run", None, root / "config/machines/router_gantry_steppers.yaml",
                        duration=45, substeps=10, program=path,
                        steps=[Step("enable", at=0), Step("home", at=0.01),
                               Step("program", at=0.1)])
    scenario.expect = [{"completed": True}, {"no_alarm": True}] + [
        {"max_following_error": {"axis": axis, "mm": 0.2}} for axis in "XYZ"]
    result = run_mock(scenario)
    assert result.passed, [(c.name, c.detail) for c in result.criteria if not c.passed]


@pytest.mark.linuxcnc
@pytest.mark.parametrize("cls,dims", [(PocketRect, {"width": 40, "height": 30}),
                                     (PocketCircle, {"diameter": 40})])
@pytest.mark.parametrize("entry", ["plunge", "ramp", "helix"])
def test_complete_pocket_in_linuxcnc_from_nondefault_modes(tmp_path, cls, dims, entry):
    from linumert.programs.linuxcnc_check import check_with_linuxcnc

    gen = cls()
    path = tmp_path / "pocket.ngc"
    # Odziedziczone G18/G91/G90.1/G93 nie mogą zmienić generowanej ścieżki.
    program = gen.generate_ngc({"depth": 2, "tool_d": 8, "entry": entry, **dims}, path.name)
    path.write_text("G18 G91 G90.1 G93\n" + program)
    result = check_with_linuxcnc(path)
    assert result.ok, result.messages


@pytest.mark.parametrize("entry", ["ramp", "helix"])
def test_entry_has_no_vertical_cut_and_respects_slope(entry):
    gen = PocketCircle()
    values, issues = gen.normalize({"diameter": 30, "tool_d": 8, "depth": 3.3,
                                    "step_down": 2, "entry": entry, "entry_angle": 2})
    assert not issues and not gen.check(values, 0)
    pos = (0, 0, 5)
    reached = 0
    for line in gen.generate(values):
        if not line.startswith(("G0 ", "G1 ", "G3 ")):
            continue
        words = {k: float(v) for k, v in re.findall(r"([XYZIJ])(-?[0-9.]+)", line)}
        end = tuple(words.get(k, pos[i]) for i, k in enumerate("XYZ"))
        if end[2] < min(reached, pos[2]):
            distance = (math.pi * abs(words["I"]) if line.startswith("G3 ")
                        else math.hypot(end[0] - pos[0], end[1] - pos[1]))
            assert distance > 0, line
            assert (pos[2] - end[2]) / distance <= math.tan(math.radians(2)) + 0.0001
            assert line.startswith(("G1 ", "G3 "))
            reached = end[2]
        pos = end
    assert reached == -3.3


@pytest.mark.parametrize("entry", ["ramp", "helix"])
def test_rejects_entry_too_small_or_excessive(entry):
    assert PocketCircle().validate({"diameter": 8.0001, "tool_d": 8, "depth": 1,
                                    "entry": entry})
    assert PocketCircle().validate({"diameter": 8.001, "tool_d": 8, "depth": 100,
                                    "entry": entry, "entry_angle": 0.1})


@pytest.mark.parametrize("cls,dims,entry", [
    (PocketRect, {"width": 12, "height": 10}, "helix"),
    (PocketCircle, {"diameter": 12}, "ramp"),
])
def test_entry_golden(cls, dims, entry):
    program = cls().generate_ngc({"tool_d": 8, "depth": 1, "entry": entry,
                                  "entry_angle": 5, **dims}, "pocket.ngc")
    golden = Path(__file__).parent / "golden" / f"pocket_{entry}.ngc"
    assert program == golden.read_text()


@pytest.mark.parametrize("cls,dims", [
    (PocketRect, {"width": 32, "height": 24, "corner_radius": 8, "rotation": 37}),
    (PocketCircle, {"diameter": 32}),
])
@pytest.mark.parametrize("finish", [False, True])
def test_allowances_and_finishing_match_material(cls, dims, finish):
    from linumert_sim.cutter import make_cutter
    from linumert_sim.zmap import StockMap

    gen = cls()
    params = {"depth": 2, "tool_d": 8, "cx": 25, "cy": 25, "entry": "helix",
              "direction": "cw", "wall_allowance": 1, "floor_allowance": 0.3,
              "finish": finish, **dims}
    values, issues = gen.normalize(params)
    assert not issues and not gen.check(values, 0)
    stock = StockMap("BOX", 0, 0, 50, 50, -10, 0, cell=0.25)
    tool = make_cutter(1, 80, 8, "flat", {"d": 8, "l": 40, "flute_length": 20})
    before = stock.volume()
    _cut_program(stock, tool, gen.generate(values))
    wall = 0 if finish else 1
    depth = 2 if finish else 1.7
    area = (math.pi * (16 - wall)**2 if cls is PocketCircle else
            (32 - 2 * wall) * (24 - 2 * wall) - (4 - math.pi) * (8 - wall)**2)
    assert before - stock.volume() == pytest.approx(area * depth, rel=0.025)
    assert stock.h[100, 100] == pytest.approx(-depth)
    assert stock.h[0, 0] == 0
    _assert_floor(stock, cls, dims, wall, depth)
    assert ("( wykanczanie dna )" in gen.generate(values)) == finish


@pytest.mark.parametrize("patch,field", [
    ({"corner_radius": 3}, "corner_radius"),
    ({"corner_radius": 4.000001}, "corner_radius"),
    ({"corner_radius": 16}, "corner_radius"),
    ({"wall_allowance": 12}, "tool_d"),
    ({"floor_allowance": 2}, "floor_allowance"),
    ({"floor_allowance": 1.1, "finish": True}, "floor_allowance"),
])
def test_invalid_finishing_geometry(patch, field):
    issues = PocketRect().validate({"width": 40, "height": 30, "tool_d": 8,
                                     "depth": 2, **patch})
    assert any(issue.field == field for issue in issues)


@pytest.mark.parametrize("direction", ["cw", "ccw"])
def test_rotated_preview_matches_gcode_bounds_and_direction(direction):
    gen = PocketRect()
    values, issues = gen.normalize({"width": 40, "height": 30, "tool_d": 8, "depth": 1,
                                    "corner_radius": 7, "rotation": 90, "direction": direction})
    assert not issues and not gen.check(values, 0)
    paths = gen.preview_2d(values)
    assert max(x for p in paths for x, y in p) == pytest.approx(11)
    assert max(y for p in paths for x, y in p) == pytest.approx(16)
    outer = paths[-1]
    area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
               in zip(outer, outer[1:], strict=False))
    assert (area > 0) == (direction == "ccw")
    arc = "G2" if direction == "cw" else "G3"
    assert any(line.startswith(arc + " ") for line in gen.generate(values))


@pytest.mark.linuxcnc
@pytest.mark.parametrize("cls,dims", [
    (PocketRect, {"width": 32, "height": 24, "corner_radius": 8, "rotation": 37}),
    (PocketCircle, {"diameter": 32}),
])
@pytest.mark.parametrize("direction", ["cw", "ccw"])
def test_finishing_in_linuxcnc(tmp_path, cls, dims, direction):
    from linumert.programs.linuxcnc_check import check_with_linuxcnc

    params = {"depth": 2, "tool_d": 8, "entry": "helix", "direction": direction,
              "wall_allowance": 1, "floor_allowance": 0.3, "finish": True, **dims}
    path = tmp_path / "finished.ngc"
    path.write_text(cls().generate_ngc(params, path.name))
    result = check_with_linuxcnc(path)
    assert result.ok, result.messages


@pytest.mark.parametrize("name,dims", [
    ("pocket_rect", {"width": 12, "height": 10}),
    ("pocket_circle", {"diameter": 12}),
])
def test_saved_version_one_keeps_original_gcode(name, dims):
    from linumert.generators.pockets import register
    from linumert.generators.registry import GeneratorRegistry
    from linumert.programs.compiler import compile_program
    from linumert.programs.lnx import LnxProgram, Step

    registry = GeneratorRegistry()
    register(registry)
    assert registry.latest(name).version == 2
    program = LnxProgram(name="legacy.ngc", steps=[Step(generator=name, version=1,
                                                     params={"tool_d": 8, "depth": 1, **dims})])
    golden = Path(__file__).parent / "golden" / f"{name}_v1.ngc"
    assert compile_program(program, registry, source="legacy.ngc") == golden.read_text()
