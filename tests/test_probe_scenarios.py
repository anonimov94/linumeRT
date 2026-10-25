"""Scenariusze sondowania Plant (sesja 033): kryteria `probed`, `probe_repeat`, `probe_tripped`
oraz spójność scenariuszy z geometrią celu sondy w machine.yaml. Bez LinuxCNC (wykonanie G38
sprawdza `test_linuxcnc_only_scenario` z markerem `linuxcnc`).

Model-Author: Claude · 2026-10-25. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from linumert_plant.scenario import ScenarioResult, evaluate, load_scenario

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "plant" / "scenarios"
MILL = ROOT / "config" / "machines" / "mill_servo_table.yaml"
NAMES = ("probe_z_touchplate", "probe_corner")


def _target() -> tuple[list[float], list[float], float]:
    probe = yaml.safe_load(MILL.read_text(encoding="utf-8"))["probe"]
    return probe["target"]["min"], probe["target"]["max"], probe["tip_length"]


def _result(name: str, probes: dict) -> ScenarioResult:
    res = ScenarioResult(load_scenario(SCENARIOS / f"{name}.yaml"), "linuxcnc")
    res.probes = probes
    return res


def _shot(x: float = 0.0, y: float = 0.0, z: float = 0.0, tripped: bool = True) -> dict:
    return {"tripped": tripped, "pos": [x, y, z]}


def _ideal_z(bias: float = 0.0) -> dict:
    _, hi, tip = _target()
    z = hi[2] + tip + bias
    return {"z1": _shot(z=z), "z2": _shot(z=z), "z3": _shot(z=z), "air": _shot(tripped=False)}


def _ideal_corner(bias: float = 0.0) -> dict:
    lo, _, _ = _target()
    x, y = lo[0] + bias, lo[1] + bias
    return {"xr": _shot(x=x), "x1": _shot(x=x), "x2": _shot(x=x),
            "yr": _shot(y=y), "y1": _shot(y=y), "y2": _shot(y=y)}


def _failed(res: ScenarioResult) -> list[str]:
    evaluate(res)
    return [c.name for c in res.criteria if not c.passed]


@pytest.mark.parametrize("name", NAMES)
def test_probe_scenarios_are_linuxcnc_only_and_tagged(name: str) -> None:  # REQ-VM-09
    scen = load_scenario(SCENARIOS / f"{name}.yaml")
    assert scen.master == "linuxcnc" and scen.requirements == ["REQ-VM-09"]
    captures = {s.params["name"] for s in scen.steps if s.action == "capture"}
    used = set()
    for crit in scen.expect:
        (kind, arg), = crit.items()
        if kind.startswith("probe"):
            used |= set(arg["captures"]) if "captures" in arg else {arg["capture"]}
        if kind == "probed" and "calibrate" in arg:
            used.add(arg["calibrate"]["capture"])
    assert used and used <= captures, (used - captures)


def test_expected_values_follow_machine_yaml_geometry() -> None:  # REQ-VM-09
    """Oczekiwane wartości nie są wzięte z pomiaru, tylko z celu sondy w machine.yaml."""
    lo, hi, tip = _target()
    expect = {}
    for name in NAMES:
        for crit in load_scenario(SCENARIOS / f"{name}.yaml").expect:
            (kind, arg), = crit.items()
            if kind == "probed":
                expect[arg["axis"]] = arg["value"]
    assert expect == {"Z": hi[2] + tip, "X": lo[0], "Y": lo[1]}


def test_ideal_probes_pass_all_criteria() -> None:  # REQ-VM-09
    assert _failed(_result("probe_z_touchplate", _ideal_z())) == []
    assert _failed(_result("probe_corner", _ideal_corner())) == []


def test_absolute_error_beyond_tolerance_fails_even_after_calibration() -> None:  # REQ-VM-09
    # Stały błąd 0,03 mm: wzorzec go usuwa, ale błąd bezwzględny (±0,02) wciąż jest za duży.
    failed = _failed(_result("probe_z_touchplate", _ideal_z(bias=0.03)))
    assert any("Z z1 = -30.0 ± 0.02" in n for n in failed)
    assert not any("po kalibracji" in n for n in failed)


def test_constant_bias_within_absolute_tolerance_passes_with_calibration() -> None:  # REQ-VM-09
    # Systematyczne 0,015 mm (luz napędu): błąd bezwzględny mieści się w ±0,02, po kalibracji ~0.
    assert _failed(_result("probe_z_touchplate", _ideal_z(bias=0.015))) == []
    assert _failed(_result("probe_corner", _ideal_corner(bias=0.015))) == []


def test_position_dependent_error_is_not_removed_by_calibration() -> None:  # REQ-VM-09
    probes = _ideal_z()
    probes["z3"] = _shot(z=-30.0 + 0.015)     # w drugim miejscu błąd inny niż we wzorcu
    failed = _failed(_result("probe_z_touchplate", probes))
    assert any("po kalibracji na z1" in n for n in failed)


def test_poor_repeatability_fails() -> None:  # REQ-VM-09
    probes = _ideal_z()
    probes["z2"] = _shot(z=-30.0 + 0.01)
    assert any("powtarzalność Z" in n for n in _failed(_result("probe_z_touchplate", probes)))


def test_probe_in_air_must_not_trip_and_missing_shots_fail() -> None:  # REQ-VM-09
    probes = _ideal_z()
    probes["air"] = _shot(tripped=True)
    assert any("air nie zadziałała" in n for n in _failed(_result("probe_z_touchplate", probes)))
    # brak zrzutu albo sonda niezadziałana (pozycja sprzed próby) nie jest wynikiem pomiaru
    failed = _failed(_result("probe_z_touchplate", {"z1": _shot(z=-30.0, tripped=False)}))
    assert len(failed) >= 5
