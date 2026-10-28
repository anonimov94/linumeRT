"""Generator makra remapu M6 dla ATC: odmowy, geometria Plant, przebieg na modelu magazynu.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 066.
Geometry and preflight regressions: Model-Author: Codex.
"""

import copy
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml
from linumert.machine.atc_macro import AtcMacroError, generate_atc_m6, plan_swap
from linumert.machine.schema import parse_machine
from linumert_plant.atc import ToolChangerModel, ToolSpec, pocket_positions

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "config" / "machines" / "router_atc_rack.yaml"
DT = 0.001


def _cfg(**tc):
    data = yaml.safe_load(ROUTER.read_text(encoding="utf-8"))
    data["toolchanger"].update(tc)
    return parse_machine(copy.deepcopy(data))


def test_macro_is_deterministic_and_has_the_expected_skeleton():
    text = generate_atc_m6(_cfg())
    assert text == generate_atc_m6(_cfg())
    assert "o<lrt_m6_atc> sub" in text and "o<lrt_m6_atc> endsub" in text
    assert re.search(r"(?m)^M6$", text) and "G43 H#<lrt_new>" in text and "G49" in text
    # kolejność: odłożenie starego przed pobraniem nowego, wbudowane M6 na końcu ruchów
    assert text.index("o<put> if") < text.index("o<get> if") < text.index("\nM6\n")
    assert "M64 P2" in text and "M65 P2" in text            # tool_release = wyjście 2
    assert "M66 P7 L4" in text and "M66 P7 L3" in text      # tool_clamped = wejście 7
    assert "M66 P8 L3" in text and "M66 P9 L3" in text      # osłona otwarta/zamknięta
    assert "G53 G0 X20 Y20" in text and "G53 G0 X320 Y20" in text


@pytest.mark.parametrize("change", [{"type": "carousel"}, {"approach_z": None}, {"outputs": {}},
                                    {"clamp": None}])
def test_generator_refuses_unsupported_or_incomplete_configuration(change):
    with pytest.raises(AtcMacroError):
        generate_atc_m6(_cfg(**change))


def test_plan_slot_positions_match_plant_geometry():
    cfg = _cfg()
    pockets = pocket_positions(cfg.toolchanger)
    for slot in range(1, 7):
        xy = [s for s in plan_swap(cfg, 0, slot) if s[0] == "xy"]
        assert [(round(s[1], 6), round(s[2], 6)) for s in xy] == [pockets[slot - 1][:2]]


def _drive(cfg, old: int, new: int) -> ToolChangerModel:
    """Wykonuje plan na modelu Plant: ruch nosa, wyjścia i czekanie na czujniki."""
    model = ToolChangerModel.from_config(cfg, {i: ToolSpec(40.0, 10.0) for i in range(1, 7)})
    if old:
        model.slots[old - 1] = None
        model.spindle_tool = old
    else:
        model.spindle_tool = None
    approach = pocket_positions(cfg.toolchanger)[0][2]
    nose = [*model.pockets[old - 1 if old else 0][:2], cfg.positions.safe_z]
    outputs = {"release": False, "cover": False}

    def mask() -> int:
        m = 0
        for flag, role in (("release", "clamp_release"), ("cover", "cover_open")):
            if outputs[flag] and role in model.roles_out:
                m |= 1 << model.io_out[model.roles_out[role]]
        return m

    def sensor(role: str) -> bool:
        m, v = model.inputs()
        return bool(v & (1 << model.io_in[model.sensor_names[role]]))

    faults = []
    for step in plan_swap(cfg, old, new):
        kind = step[0]
        if kind == "xy":
            nose[0], nose[1] = step[1], step[2]
        elif kind == "z":
            nose[2] = step[1]
        elif kind in outputs:
            outputs[kind] = step[1]
        for _ in range(2000 if kind in ("release", "cover", "wait") else 5):
            faults += model.step(DT, tuple(nose), mask())
        if kind == "wait":
            assert sensor(step[1]) == (step[2] == "high"), f"{step}: czujnik nie osiągnął stanu"
    assert approach == cfg.toolchanger.approach_z
    model.faults = [e for e in faults if e.kind in {
        "TOOL_DROP", "CLAMP_FAULT", "POCKET_OCCUPIED", "COVER_CRASH"}]
    return model


@pytest.mark.parametrize("old,new", [(0, 3), (2, 5), (4, 0)])
def test_plan_swaps_tools_on_the_plant_model_without_faults(old, new):
    cfg = _cfg()
    model = _drive(cfg, old, new)
    assert model.faults == []
    assert model.spindle_tool == (new or None)
    if old:
        assert model.slots[old - 1] == old   # stare narzędzie wróciło do swojego gniazda
    if new:
        assert model.slots[new - 1] is None  # nowe opuściło gniazdo


def test_configgen_atc_option_switches_remap_and_emits_macro():
    from linumert.machine.configgen import Options, render

    cfg = _cfg()
    plain = render(cfg, "sim")
    assert "ngc=lrt_m6\n" in next(v for k, v in plain.items() if k.endswith(".ini"))
    assert not any(k.endswith("lrt_m6_atc.ngc") for k in plain)
    files = render(cfg, "sim", Options(atc=True))
    ini = next(v for k, v in files.items() if k.endswith(".ini"))
    assert "REMAP = M6 modalgroup=6 ngc=lrt_m6_atc\n" in ini
    assert files["macros/lrt_m6_atc.ngc"] == generate_atc_m6(cfg)


def test_configgen_atc_option_refuses_carousel():
    from linumert.machine.configgen import Options, render

    with pytest.raises(AtcMacroError):
        render(_cfg(type="carousel"), "sim", Options(atc=True))


EXPLICIT = [[35, 40, -5], [90, 60, -5], [145, 35, -5],
            [205, 70, -5], [260, 45, -5], [335, 85, -5]]


@pytest.mark.parametrize("base,pitch", [([5000, 5000, -5], 1000), (None, None)])
def test_explicit_pockets_override_base_geometry_in_plan_and_macro(base, pitch):
    # REQ-VM-08: the machine and generated moves share the actual pocket positions.
    cfg = _cfg(slot_positions=EXPLICIT, base_position=base, pitch_mm=pitch)
    model = ToolChangerModel.from_config(cfg)
    text = generate_atc_m6(cfg)
    for slot, position in enumerate(model.pockets, 1):
        assert [s[1:] for s in plan_swap(cfg, 0, slot) if s[0] == "xy"] == [position[:2]]
        for var in ("lrt_old", "lrt_new"):
            block = (f"o<{var}_slot_{slot}> if [#<{var}> EQ {slot}]\n"
                     f"    G53 G0 X{position[0]:g} Y{position[1]:g}")
            assert block in text
    assert "5000" not in text and "1000" not in text


@pytest.mark.parametrize("old,new", [(0, 3), (2, 5), (4, 0)])
def test_explicit_pocket_swap_on_plant_has_no_drop_or_collision(old, new):
    cfg = _cfg(slot_positions=EXPLICIT, base_position=None, pitch_mm=None)
    model = _drive(cfg, old, new)
    assert model.faults == []
    assert model.spindle_tool == (new or None)


def test_rotated_rack_uses_shared_resolved_positions():
    cfg = _cfg(base_orientation_deg=90)
    assert pocket_positions(cfg.toolchanger)[-1][:2] == (20, 320)
    assert "G53 G0 X20 Y320" in generate_atc_m6(cfg)
    assert [s[1:] for s in plan_swap(cfg, 0, 6) if s[0] == "xy"] == [(20, 320)]


@pytest.mark.parametrize("change", [
    {"slot_positions": EXPLICIT[:-1]}, {"base_position": [5000, 20, -5]},
    {"base_orientation_deg": float("inf")}, {"pitch_mm": float("inf")},
    {"approach_z": -200}, {"retract_z": 5}, {"retract_z": -25},
    {"approach_z": float("nan")}, {"slot_positions": [[float("nan"), 20, -5]] * 6},
])
def test_unreachable_or_invalid_rack_is_rejected_before_export(change):
    cfg = _cfg()
    # Also defend callers that edit an already parsed, mutable configuration.
    cfg.toolchanger = cfg.toolchanger.model_copy(update=change)
    for action in (lambda: generate_atc_m6(cfg), lambda: plan_swap(cfg, 0, 1)):
        with pytest.raises(AtcMacroError):
            action()


def test_rounding_cannot_place_a_generated_coordinate_outside_the_axis_limits():
    cfg = _cfg(slot_positions=[[1.00004, 20, -5]] * 6)
    cfg.axis("X").soft_limits = (1.00003, 599)
    with pytest.raises(AtcMacroError, match="X"):
        generate_atc_m6(cfg)


@pytest.mark.parametrize("old,new", [(-1, 1), (1, -1), (7, 1), (1, 7), (7, 7)])
def test_invalid_tool_ids_cannot_select_unmapped_pockets(old, new):
    with pytest.raises(AtcMacroError, match="numer narzędzia"):
        plan_swap(_cfg(), old, new)


def test_macro_checks_both_tool_ids_before_noop_or_any_motion():
    text = generate_atc_m6(_cfg())
    guard = text[text.index("o<range> if"):text.index("o<range> endif")]
    assert "#<lrt_old> LT 0" in guard and "#<lrt_old> GT 6" in guard
    assert "#<lrt_new> LT 0" in guard and "#<lrt_new> GT 6" in guard
    assert text.index("o<range> endif") < text.index("o<same> if") < text.index("G53 G0")


def _interpret_swap(tmp_path, slot, startup="G21 G90 G94 M5"):
    from linumert.machine.configgen import Options, render
    from linumert.programs.linuxcnc_check import InterpreterUnavailable, find_linuxcnc

    try:
        prefix, _ = find_linuxcnc()
    except InterpreterUnavailable as exc:
        pytest.skip(str(exc))
    table = tmp_path / "tool.tbl"
    table.write_text("".join(f"T{i} P{i} Z40 D10\n" for i in range(1, 7)), encoding="utf-8")
    cfg = _cfg(slot_positions=EXPLICIT, base_position=None, pitch_mm=None)
    files = render(cfg, "sim", Options(atc=True, tool_table=str(table)))
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    ini = tmp_path / next(name for name in files if name.endswith(".ini"))
    parameters = tmp_path / "linumert.var"
    parameters.touch()
    program = tmp_path / "swap.ngc"
    program.write_text(f"{startup}\nT{slot} M6\nM2\n", encoding="utf-8")
    args = ["-i", str(ini), "-t", str(table), "-v", str(parameters), "-n", "2", str(program)]
    command = " ".join(prefix + ["exec rs274 " + shlex.join(args)])
    # Never share tool mmap or variable files with an operator's controller.
    run = subprocess.run(["bash", "-c", command], cwd=tmp_path,
                         env={**os.environ, "HOME": str(tmp_path), "LC_ALL": "C"},
                         stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    output = run.stdout + run.stderr
    (tmp_path / "interpreter.log").write_text(output, encoding="utf-8")
    return run, cfg


@pytest.mark.linuxcnc
@pytest.mark.parametrize("slot", [1, 3, 6])
def test_explicit_pocket_is_reached_by_the_real_interpreter(tmp_path, slot):
    """Syntax/canonical geometry only; standalone rs274 does not exercise HAL sensors."""
    run, cfg = _interpret_swap(tmp_path, slot)
    output = run.stdout + run.stderr
    assert run.returncode == 0 and "PROGRAM_END()" in run.stdout, output
    assert f"CHANGE_TOOL({slot})" in run.stdout, output
    feed = re.findall(r"STRAIGHT_FEED\(([^)]*)\)", run.stdout)
    points = [tuple(float(v) for v in entry.split(",")[:3]) for entry in feed]
    expected = (*EXPLICIT[slot - 1][:2], cfg.toolchanger.approach_z)
    assert expected in points, output


@pytest.mark.linuxcnc
@pytest.mark.parametrize("startup,message", [
    ("G20 G90 G94 M5", "G21 G90 G94"),
    ("G21 G91 G94 M5", "G21 G90 G94"),
    ("G21 G90 G93 F1 M5", "G21 G90 G94"),
    ("G21 G90 G95 F1 M5", "G21 G90 G94"),
    ("G21 G90 G94 S1000 M3", "M5"),
])
def test_modal_or_spindle_precondition_refuses_before_motion_or_outputs(tmp_path, startup, message):
    run, _ = _interpret_swap(tmp_path, 3, startup)
    output = run.stdout + run.stderr
    assert message in output, output
    assert "PROGRAM_END()" not in run.stdout, output
    for action in ("STRAIGHT_TRAVERSE(", "STRAIGHT_FEED(",
                   "SET_AUX_OUTPUT_BIT(", "CLEAR_AUX_OUTPUT_BIT(", "CHANGE_TOOL("):
        assert action not in run.stdout, output
