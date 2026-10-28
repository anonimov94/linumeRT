"""Scenariusze Plant z atrapą mastera, runner i raport (sesja 024).

Model-Author: Claude

Scenariusze z `plant/scenarios/` w lockstep bez LinuxCNC (CI); te z `master: both` dodatkowo
z LinuxCNC RIP w tests/test_scenario_linuxcnc.py. Wymaga rdzenia C (kompilator, Linux/WSL).
"""

from __future__ import annotations

import copy
import random
import sys
from pathlib import Path

import pytest
import yaml
from linumert.machine.schema import MachineConfigError, load_machine
from linumert_plant.scenario import (
    ScenarioError,
    ScenarioResult,
    evaluate,
    load_scenario,
    parse_program,
    run_mock,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "plant" / "scenarios"
MACHINES = sorted((ROOT / "config" / "machines").glob("*.yaml"))
sys.path.insert(0, str(ROOT / "tools"))
import run_scenario  # noqa: E402

STARTER = ("first_motion", "homing_all", "rapid_vs_feed", "too_much_accel_stepper",
           "drive_fault_mid_program", "estop_mid_program")


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


def _scenarios() -> list[Path]:
    return sorted(p for p in SCENARIOS.glob("*.yaml") if p.stem != "matrix_smoke")


def test_starter_scenarios_exist() -> None:
    names = {p.stem for p in _scenarios()}
    assert set(STARTER) <= names
    for path in _scenarios():
        scen = load_scenario(path)
        assert scen.requirements, f"{path.name}: brak requirements"
        assert scen.name == path.stem


def _mock_scenarios() -> list[Path]:
    """Scenariusze wykonalne na atrapie (`master: linuxcnc` wymaga G38 i LinuxCNC RIP)."""
    return [p for p in _scenarios() if load_scenario(p).master != "linuxcnc"]


@pytest.mark.parametrize("path", _mock_scenarios(), ids=lambda p: p.stem)
def test_scenario_passes_with_mock_master(core, path: Path) -> None:
    res = run_mock(load_scenario(path))
    failed = [f"{c.name}: {c.detail}" for c in res.criteria if not c.passed]
    assert res.passed, failed


def test_scenario_is_deterministic(core) -> None:  # REQ-QA-04
    a = run_mock(load_scenario(SCENARIOS / "drive_fault_mid_program.yaml"))
    b = run_mock(load_scenario(SCENARIOS / "drive_fault_mid_program.yaml"))
    assert a.stats["digest"] == b.stats["digest"] and a.alarms == b.alarms
    assert a.telemetry["drives"]["drv_x"]["act"] == b.telemetry["drives"]["drv_x"]["act"]


def test_failing_criteria_are_reported(core, tmp_path) -> None:
    text = (SCENARIOS / "first_motion.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    data["machine"] = str(ROOT / "config/machines/mill_servo_table.yaml")
    data["program"] = str(SCENARIOS / "programs/first_motion.ngc")
    data["expect"] = [{"alarm": {"code": "E-4200"}}, {"position": {"axis": "X", "value": 7}},
                      {"lost_steps": {"axis": "X", "min": 1}}]
    data["steps"].append({"at": 1.0, "action": "clear", "fault": "estop"})
    path = tmp_path / "zly.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    res = run_mock(load_scenario(path))
    assert not res.passed
    names = [c.name for c in res.criteria if not c.passed]
    assert any("alarm E-4200" in n for n in names) and any("pozycja X" in n for n in names)
    assert any("krok clear" in n for n in names)  # zdjęcie nieaktywnej awarii = FAIL, nie wyjątek


@pytest.mark.parametrize("machine", MACHINES, ids=lambda p: p.stem)
def test_matrix_smoke_on_every_machine(core, machine: Path) -> None:  # REQ-QA-02
    res = run_mock(load_scenario(SCENARIOS / "matrix_smoke.yaml", machine=machine))
    assert res.passed, [f"{c.name}: {c.detail}" for c in res.criteria if not c.passed]


# ---- format i program ---------------------------------------------------------------------

@pytest.mark.parametrize("patch, fragment", [
    ({"master": "robot"}, "master"),
    ({"requirements": ["REQ-1"]}, "REQ-XX-NN"),
    ({"steps": [{"action": "skok"}]}, "action"),
    ({"steps": [{"action": "fault", "at_line": 3}]}, "at_line wymaga"),
    ({"expect": []}, "co najmniej jedno"),
    ({"expect": [{"cos": 1}]}, "jedno kryterium"),
    ({"machine": "brak.yaml"}, "brak pliku"),
    ({"extra": 1}, "nieznane pole extra"),
])
def test_scenario_validation(tmp_path, patch: dict, fragment: str) -> None:
    data = {"name": "t", "machine": str(MACHINES[0]), "expect": [{"no_alarm": True}]}
    data.update(patch)
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ScenarioError, match=fragment):
        load_scenario(path)


def test_parse_program_subset() -> None:
    blocks = parse_program("(x)\nG21 G90\nG1 X10 Y-2.5 F600 ; komentarz\nX20\nG91 G0 Z1\n"
                           "M3 S1000\nM5\nM30\n")
    assert [b.line for b in blocks] == [2, 3, 4, 5, 6, 7, 8]
    assert blocks[1].motion == "G1" and blocks[1].target == {"X": 10.0, "Y": -2.5}
    assert blocks[1].feed == 600 and blocks[2].motion == "G1"  # modalny G1
    assert blocks[3].incremental and blocks[3].motion == "G0"
    assert blocks[4].spindle == 1000 and blocks[5].spindle == 0 and blocks[6].end
    with pytest.raises(ScenarioError, match="G2 nieobsługiwane"):
        parse_program("G2 X1 Y1 I1")
    with pytest.raises(ScenarioError, match="bez G0/G1"):
        parse_program("X5")


def test_evaluate_criteria_without_plant() -> None:
    scen = load_scenario(SCENARIOS / "first_motion.yaml")
    scen.expect = [{"max_following_error": {"axis": "X", "mm": 0.1}},
                   {"lost_steps": {"axis": "X", "max": 0}}, {"alarm": {"code": "E-1100",
                                                                          "within_s": 1}},
                   {"no_alarm": {"allowed": ["E-1100"]}}, {"oracle": "PASS"},
                   {"frames": {"lost_max": 0}}, {"completed": True}]
    res = ScenarioResult(scen, "mock", alarms={"E-1100": 0.5}, ferr_max={"X": 0.2},
                         lost_steps={"X": 0}, completed=True, oracle={"result": "PASS"},
                         stats={"lost": 0})
    evaluate(res)
    assert [c.passed for c in res.criteria] == [False, True, True, True, True, True, True]


# ---- runner i raport ----------------------------------------------------------------------

def test_runner_cli_and_report(core, tmp_path, capsys) -> None:
    out = tmp_path / "raporty"
    assert run_scenario.main(["first_motion", "estop_mid_program", "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "PASS  first_motion" in text and "PASS  estop_mid_program" in text
    page = (out / "first_motion.html").read_text(encoding="utf-8")
    assert "<svg" in page and "PASS" in page and "REQ-VM-01" in page and "drv_x" in page
    assert "first_motion.html" in (out / "index.html").read_text(encoding="utf-8")
    assert run_scenario.main(["brak_takiego"]) == 2


def test_runner_exit_code_on_fail(core, tmp_path) -> None:
    data = yaml.safe_load((SCENARIOS / "link_loss.yaml").read_text(encoding="utf-8"))
    data["machine"] = str(ROOT / "config/machines/mill_servo_table.yaml")
    data["expect"] = [{"no_alarm": True}]
    path = tmp_path / "fail.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert run_scenario.main([str(path), "--no-report"]) == 1


def test_runner_ssh_command_without_ssh(capsys) -> None:
    assert run_scenario.main(["first_motion", "--ssh", "lrt@10.77.0.10", "--remote-dir",
                              "/opt/linumeRT", "--master", "mock", "--print-ssh"]) == 0
    cmd = capsys.readouterr().out.strip()
    assert cmd.startswith("ssh -o BatchMode=yes lrt@10.77.0.10 ")
    assert "cd /opt/linumeRT && python3 tools/run_scenario.py first_motion --master mock" \
        in cmd and "--ssh" not in cmd.split("tools/run_scenario.py")[1]


# ---- fuzz machine.yaml --------------------------------------------------------------------

def _mutate(node, rng: random.Random):
    """Losowa zmiana jednego liścia albo usunięcie klucza (deterministycznie z ziarna)."""
    if isinstance(node, dict) and node:
        key = rng.choice(sorted(node))
        if rng.random() < 0.15:
            del node[key]
        else:
            node[key] = _mutate(node[key], rng)
        return node
    if isinstance(node, list) and node:
        i = rng.randrange(len(node))
        node[i] = _mutate(node[i], rng)
        return node
    return rng.choice([None, -1, 0, 1e9, -1e9, "x", [], {}, True, 3.5, "NC", float("nan")])


def test_fuzz_machine_yaml(core, tmp_path) -> None:  # REQ-QA-03
    """Uszkodzony machine.yaml: albo poprawny model, albo MachineConfigError — nic innego."""
    from linumert.machine.drives.drive_template import TemplateError
    from linumert.machine.drives.machine_drives import load_machine_drives
    from linumert_plant.build_machine import build_model

    rng = random.Random(24)
    accepted = rejected = 0
    for k in range(120):
        base = yaml.safe_load(MACHINES[k % len(MACHINES)].read_text(encoding="utf-8"))
        data = copy.deepcopy(base)
        for _ in range(rng.randint(1, 3)):
            _mutate(data, rng)
        path = tmp_path / f"fuzz_{k}.yaml"
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        try:
            load_machine(path)
            mcfg, drives = load_machine_drives(path)
            core.PlantMachine(build_model(mcfg, drives, seed=1))
            accepted += 1
        except (MachineConfigError, TemplateError):
            rejected += 1
    assert accepted + rejected == 120 and rejected > 30
