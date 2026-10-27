"""Generator makra remapu M6 dla ATC: odmowy, geometria Plant, przebieg na modelu magazynu.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 066.
"""

import copy
import re
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
    assert "X[20 + [#<lrt_new> - 1] * 60] Y[20 + [#<lrt_new> - 1] * 0]" in text.replace(".0", "")


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
    nose = [20.0 + 60 * (old - 1 if old else 0), 20.0, cfg.positions.safe_z]
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
