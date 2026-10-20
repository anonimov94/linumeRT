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
    pos = (0.0, 0.0, 5.0)
    for line in gen.generate(values):
        if not line.startswith(("G0 ", "G1 ", "G3 ")):
            continue
        words = {k: float(v) for k, v in re.findall(r"([XYZIJ])(-?[0-9.]+)", line)}
        end = tuple(words.get(k, pos[i]) for i, k in enumerate("XYZ"))
        if line.startswith("G3 "):
            start = pos
            center = (pos[0] + words["I"], pos[1] + words["J"])
            radius = math.hypot(words["I"], words["J"])
            a = math.atan2(pos[1] - center[1], pos[0] - center[0])
            b = math.atan2(end[1] - center[1], end[0] - center[0])
            sweep = (b - a) % math.tau or math.tau
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
    area = math.pi * 20**2 if cls is PocketCircle else 40 * 30 - (4 - math.pi) * 4**2
    assert before - stock.volume() == pytest.approx(area * 2, rel=0.025)
    assert stock.h[0, 0] == 0 and stock.h[100, 100] == -2


@pytest.mark.parametrize("entry", ["plunge", "ramp"])
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
