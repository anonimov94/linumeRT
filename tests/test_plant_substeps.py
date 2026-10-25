"""Wynik atrapy Plant nie zależy od `timing.substeps` (rdzeń C: interpolacja celu CSP w cyklu).

Model-Author: Claude · uruchomienie zadania A z przekazania Codex (M1).
Regresja po PR #116: cel 607Ah z cyklu mastera trafiał do napędu w pierwszym podkroku (n-krotny
impuls FF) — frezarka E-4201, router tysiące zgubionych kroków. Opis: docs/raporty/plant_substeps.md.
Wymaga rdzenia C (kompilator, Linux/WSL).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from linumert_plant.scenario import Scenario, Step, run_mock

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "plant/scenarios/machines/mill_servo_table_y2.yaml"
ROUTER = ROOT / "config/machines/router_gantry_steppers.yaml"

# REQ-QA-02
CASES = [
    (MILL, "G0 Z-15", (1, 2, 4, 8, 16)),
    (MILL, "G0 X100 Y80", (1, 2, 4, 8)),
    # n = 1 (krok 1 ms) jest za gruby dla pola krokowca — to ograniczenie modelu, nie regresja
    (ROUTER, "G0 X10", (2, 4, 8, 16)),
    (ROUTER, "G0 X100", (2, 4, 8, 16)),
    (ROUTER, "G1 X100 F600", (2, 4, 8, 16)),
    (ROUTER, "G0 Y100", (2, 4, 8, 16)),
]


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")


def _run(machine: Path, program: str, n: int, tmp_path: Path):
    path = tmp_path / f"p{n}.ngc"
    path.write_text(f"G90\nG0 Z-5\n{program}\nM2\n", encoding="utf-8")
    scen = Scenario("substeps", None, machine, duration=60, substeps=n, program=path,
                    steps=[Step("enable", at=0), Step("home", at=0.01), Step("program", at=0.1)])
    scen.expect = ([{"completed": True}, {"no_alarm": True}] +
                   [{"lost_steps": {"axis": a, "max": 0}} for a in "XYZ"])
    return run_mock(scen)


@pytest.mark.parametrize(("machine", "program", "counts"), CASES,
                         ids=[f"{m.stem}-{p}" for m, p, _ in CASES])
def test_result_independent_of_substeps(core, machine, program, counts, tmp_path) -> None:
    results = {n: _run(machine, program, n, tmp_path) for n in counts}
    for n, res in results.items():
        failed = [f"{c.name}: {c.detail}" for c in res.criteria if not c.passed]
        assert res.passed, f"substeps={n}: {failed}"
    ref = results[counts[-1]].ferr_max
    for n, res in results.items():
        for axis in "XYZ":
            assert res.ferr_max[axis] == pytest.approx(ref[axis], abs=0.05), \
                f"substeps={n} oś {axis}: {res.ferr_max[axis]:.3f} vs {ref[axis]:.3f} mm"
