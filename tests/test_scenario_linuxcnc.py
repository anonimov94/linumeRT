"""Scenariusze `master: both` z prawdziwym LinuxCNC RIP i Plant na localhost (sesja 024).

Model-Author: Claude

Marker `linuxcnc`; wymaga RIP (tools/ci/build-linuxcnc.sh) i rdzenia Plant. Porty LRT-NET
47820–47829 (prompts/START-PODZIAL.md §2). Te same pliki co w tests/test_scenario.py, inny master.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from linumert_plant.scenario import load_scenario

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "plant" / "scenarios"
BOTH = sorted(p for p in SCENARIOS.glob("*.yaml") if load_scenario(p).master == "both")


@pytest.mark.parametrize("index, path", list(enumerate(BOTH)), ids=[p.stem for p in BOTH])
def test_scenario_with_linuxcnc(index: int, path: Path) -> None:  # REQ-QA-03
    from linumert_plant.scenario_linuxcnc import run_linuxcnc
    from rip_support import rip_root

    rip_root()  # bez RIP: pominięty
    res = run_linuxcnc(load_scenario(path), port=47820 + index)
    failed = [f"{c.name}: {c.detail}" for c in res.criteria if not c.passed]
    assert res.passed, (failed, res.alarms, res.log[-15:])


def test_linuxcnc_master_rejects_other_machine() -> None:
    from linumert_plant.scenario import ScenarioError
    from linumert_plant.scenario_linuxcnc import run_linuxcnc

    scen = load_scenario(SCENARIOS / "too_much_accel_stepper.yaml")
    with pytest.raises(ScenarioError, match="mill_servo_table"):
        run_linuxcnc(scen)
