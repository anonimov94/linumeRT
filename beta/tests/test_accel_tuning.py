# SPDX-License-Identifier: GPL-2.0-or-later
"""Dobór przyspieszeń z budżetu uchybu (M1). Model-Author: Claude · 2026-10-25."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from linumert_plant.accel_tuning import (
    Trial,
    TuningError,
    build_program,
    report_markdown,
    tune_axis,
    write_acceleration,
)

ROOT = Path(__file__).resolve().parents[1]
MILL_Y2 = ROOT / "scenarios/machines/mill_servo_table_y2.yaml"
DATA = {"axes": [{"letter": "X", "max_acceleration": 1000, "max_velocity": 200,
                  "soft_limits": [1, 599]}]}


def fake(limit: float, per_unit: float = 0.0001):
    """Model: uchyb rośnie liniowo z przyspieszeniem; powyżej `limit` budżet jest przekroczony."""
    def run(data, letter, accel):
        ferr = accel * per_unit
        return Trial(accel, accel <= limit, ferr, "" if accel <= limit else "przekroczony uchyb")
    return run


# REQ-QA-02
def test_finds_limit_above_and_below_configured():
    up = tune_axis(DATA, "X", 0.2, fake(3000), tolerance=0.02)
    assert 2900 <= up.best_pass <= 3000 < up.first_fail
    assert up.recommended == pytest.approx(0.9 * up.best_pass, abs=10)
    assert up.trials[-1].passed
    assert up.trials[-1].accel == pytest.approx(0.9 * up.recommended, abs=10)
    assert any(t.accel == up.recommended and t.passed for t in up.trials)
    down = tune_axis(DATA, "X", 0.2, fake(400), tolerance=0.02)      # obecne za duże
    assert 390 <= down.best_pass <= 400 and down.recommended < 400


def test_resonance_hole_is_detected_and_avoided():
    """Krokowiec: pasmo utraty kroków pod największym przechodzącym przyspieszeniem."""
    def run(data, letter, accel):
        ok = not (4500 <= accel <= 7500)
        return Trial(accel, ok and accel <= 9000, 0.0, "" if ok else "zgubione kroki")
    result = tune_axis(DATA, "X", 0.2, run, tolerance=0.02)
    assert result.non_monotonic
    assert result.recommended < 4500 and result.trials[-1].passed
    assert "niemonotoniczne" in report_markdown(Path("m.yaml"), [result])


def test_capped_when_nothing_fails_and_trial_limit():
    capped = tune_axis(DATA, "X", 0.2, fake(1e9), max_factor=8)
    assert capped.capped and capped.first_fail is None and capped.best_pass == 8000
    with pytest.raises(TuningError, match="limit"):
        tune_axis(DATA, "X", 0.2, fake(3000), max_trials=3)


def test_no_pass_anywhere_is_an_error():
    with pytest.raises(TuningError, match="nawet"):
        tune_axis(DATA, "X", 0.2, fake(0.0))


@pytest.mark.parametrize("kwargs", [{"budget_mm": 0}, {"budget_mm": 200}, {"margin": 0},
                                    {"margin": 1.5}, {"tolerance": 0}, {"max_factor": 1}])
def test_invalid_parameters_are_refused(kwargs):
    args = {"budget_mm": 0.2, **kwargs}
    budget = args.pop("budget_mm")
    with pytest.raises(TuningError):
        tune_axis(DATA, "X", budget, fake(3000), **args)


def test_unknown_axis_and_missing_acceleration():
    with pytest.raises(TuningError, match="brak osi"):
        tune_axis(DATA, "Q", 0.2, fake(3000))
    with pytest.raises(TuningError, match="dodatniego"):
        tune_axis({"axes": [{"letter": "X"}]}, "X", 0.2, fake(3000))


def test_program_stays_inside_soft_limits():
    text, dist, velocity = build_program(DATA["axes"][0])
    values = [float(line.split("X")[1]) for line in text.splitlines() if line.startswith("G0")]
    assert all(1 < v < 599 for v in values) and dist == 150 and velocity == 200
    short, dist2, _ = build_program({"letter": "Z", "soft_limits": [-119, -1], "max_velocity": 80})
    assert dist2 == pytest.approx(0.6 * 118)
    assert all(-119 < float(ln.split("Z")[1]) < -1 for ln in short.splitlines()
               if ln.startswith("G0"))


def test_write_acceleration_edits_only_the_chosen_axis(tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(MILL_Y2.read_text(encoding="utf-8"), encoding="utf-8")
    before = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert write_acceleration(path, "X", 2345) is True
    assert write_acceleration(path, "X", 2345) is False
    after = yaml.safe_load(path.read_text(encoding="utf-8"))
    axes = {a["letter"]: a for a in after["axes"]}
    assert axes["X"]["max_acceleration"] == 2345
    for a in before["axes"]:
        if a["letter"] != "X":
            assert axes[a["letter"]]["max_acceleration"] == a["max_acceleration"]
    comments = MILL_Y2.read_text(encoding="utf-8").count("#")
    assert path.read_text(encoding="utf-8").count("#") == comments
    with pytest.raises(TuningError):
        write_acceleration(path, "Q", 1)
    assert not list(tmp_path.glob("*.tmp"))


def test_report_lists_results():
    result = tune_axis(DATA, "X", 0.2, fake(3000))
    text = report_markdown(Path("m.yaml"), [result])
    assert "NIEZWERYFIKOWANE NA SPRZĘCIE" in text and "| X |" in text and "PASS" in text


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")


def test_real_plant_mill_x_stays_within_budget_and_ferr_grows(core):
    from linumert_plant.accel_tuning import run_plant

    data = yaml.safe_load(MILL_Y2.read_text(encoding="utf-8"))
    slow = run_plant(data, "X", 500, 0.2)
    fast = run_plant(data, "X", 4000, 0.2)
    assert slow.passed and fast.passed, (slow, fast)
    # bezwładność: większe przyspieszenie daje większy uchyb
    assert 0.0 < slow.ferr_mm < fast.ferr_mm < 0.2
    tight = run_plant(data, "X", 4000, 0.05)                # ten sam ruch przekracza ciasny budżet
    assert not tight.passed and "budżet" in tight.reason
