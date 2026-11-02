"""Testy budowy wirtualnej obrabiarki z machine.yaml i rdzenia C przez ctypes (sesja 014).

Model-Author: Claude
Scenariusze REQ-VM-02…05: kin_gantry, kin_xyza, kin_trunnion, gantry_skew_alarm, hardstop_crash,
limit_switch_trip, shared_limit_input. Testy dynamiki wymagają kompilatora C (Linux/WSL);
w innym środowisku są pomijane, a budowa modelu (bez C) jest testowana zawsze.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from linumert.machine.schema import MachineConfigError, parse_machine
from linumert_plant.build_machine import LINUXCNC_KINEMATICS, MAX_IO, build_machine, build_model
from linumert_plant.drive_library import load_library
from linumert_plant.machine_drives import resolve_machine_drives

ROOT = Path(__file__).resolve().parents[1]
MACHINES = ROOT / "config" / "machines"
EXAMPLES = sorted(MACHINES.glob("*.yaml"))
SERVO_DT = 1e-3
STEPPER_DT = 1e-4  # krokowiec bez sprzężenia: krok ≤ 100 µs (drive.h)
STO_CODE, HW_LIMIT_CODE = 0xFF02, 0xFF01


@pytest.fixture(scope="module")
def plant():
    """Klasa PlantMachine z załadowanym rdzeniem C albo pominięcie testu."""
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding.PlantMachine


def _data(name: str) -> dict:
    return yaml.safe_load((MACHINES / f"{name}.yaml").read_text(encoding="utf-8"))


def _model(data: dict):
    cfg = parse_machine(data)
    return build_model(cfg, resolve_machine_drives(cfg, load_library()))


def _rx(a: float, p):
    """R_x(a)^T · p (obrót odwrotny wokół X)."""
    c, s = math.cos(a), math.sin(a)
    return (p[0], c * p[1] + s * p[2], -s * p[1] + c * p[2])


def _rz(a: float, p):
    """R_z(a)^T · p."""
    c, s = math.cos(a), math.sin(a)
    return (c * p[0] + s * p[1], -s * p[0] + c * p[1], p[2])


def _close(actual, expected, tol=1e-6):
    assert actual == pytest.approx(expected, abs=tol), (actual, expected)


def _at(machine, letter: str, value: float) -> None:
    """Ustawia oś i czeka 3 ms, aż ustaną drgania styków (debounce_ms = 1 w przykładach)."""
    machine.set_joint_position(letter, value)
    machine.step(STEPPER_DT, 30)


# ---- budowa modelu (bez rdzenia C) -------------------------------------------------------


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_examples_build_model(path):  # REQ-VM-01, REQ-VM-03
    model = build_machine(path)
    cfg = model.config
    assert model.joints == [a.letter for a in cfg.axes]
    assert model.drives == [d.name for d in cfg.drives]
    assert model.spindle == cfg.spindle.drive
    assert set(model.links) >= set(model.joints)
    assert model.kinematics == LINUXCNC_KINEMATICS[cfg.kinematics.preset]
    text = model.to_text()
    assert "joint.0.drive0" in text and "estop.input" in text


def test_five_examples_exist():
    assert len(EXAMPLES) == 5


def test_gantry_maps_two_drives_and_skew():  # REQ-VM-03
    model = build_machine(MACHINES / "router_gantry_steppers.yaml")
    settings = dict(model.settings)
    y = model.joints.index("Y")
    assert model.joint_drives["Y"] == ["drv_y1", "drv_y2"]
    assert settings[f"joint.{y}.drive0"] == model.drives.index("drv_y1")
    assert settings[f"joint.{y}.drive1"] == model.drives.index("drv_y2")
    assert settings[f"joint.{y}.max_skew"] == pytest.approx(0.5e-3)
    assert LINUXCNC_KINEMATICS["router_gantry_xyz"]["coordinates"] == "XYYZ"


def test_shared_home_sensor_uses_limit_input():  # REQ-VM-05
    model = build_machine(MACHINES / "router_gantry_steppers.yaml")
    assert model.home_inputs == {"X": "lim_x_min", "Y": "lim_y_min", "Z": "lim_z_max"}
    trunnion = build_machine(MACHINES / "mill_xyzac_trunnion.yaml")
    assert trunnion.home_inputs["A"] == "home_a"


def test_build_rejects_unsupported_configuration():  # REQ-VM-04, REQ-VM-11
    data = _data("router_gantry_steppers")
    data["axes"][0]["hardstops"]["min"]["stiffness_n_mm"] = 900
    data["io"]["inputs"]["toolsetter"] = MAX_IO + 3
    with pytest.raises(MachineConfigError) as err:
        _model(data)
    text = "\n".join(err.value.errors)
    assert "axes[0].hardstops" in text and "sztywność" in text
    assert "io.inputs.toolsetter" in text and "32 bity" in text


def test_chain_branch_and_axes_are_validated():  # REQ-VM-02
    data = _data("router_xyza")
    data["kinematics"] = {"chain": [
        {"id": "Y", "kind": "linear", "axis": [0, 1, 0]},
        {"id": "X", "kind": "linear", "axis": [1, 0, 0], "parent": "Y"},
        {"id": "Z", "kind": "linear", "axis": [0, 0, 1], "parent": "X", "branch": "workpiece"},
        {"id": "A", "kind": "linear", "axis": [1, 0, 0]},
    ]}
    with pytest.raises(MachineConfigError) as err:
        _model(data)
    text = "\n".join(err.value.errors)
    assert "chain[2].branch" in text
    assert "czlon A ma rodzaj linear" in text


# ---- maszyny w rdzeniu C --------------------------------------------------------------------


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_examples_build_in_plant(plant, path):  # REQ-VM-01, REQ-VM-02, REQ-VM-03
    machine = plant(build_machine(path))
    centered = plant(build_machine(path, start="center"))
    cfg = machine.model.config
    for axis in cfg.axes:
        # Od sesji 015 start po włączeniu jest losowy w soft limits (REQ-VM-07).
        lo, hi = axis.soft_limits
        assert lo <= machine.joint_position(axis.letter) <= hi
        _close(centered.joint_position(axis.letter), 0.5 * (lo + hi))
    assert machine.input(cfg.io.estop.input)  # NC: pętla zamknięta
    assert machine.events() == set()
    machine.step(STEPPER_DT, 10)
    assert machine.time == pytest.approx(10 * STEPPER_DT)


def test_kin_gantry(plant):  # REQ-VM-02
    machine = plant(build_machine(MACHINES / "router_gantry_steppers.yaml"))
    for x, y, z in ((0.0, 0.0, 0.0), (120.0, 800.0, -50.0), (599.0, 3.0, -119.0)):
        for letter, value in zip("XYZ", (x, y, z), strict=True):
            machine.set_joint_position(letter, value)
        tip = (x, y, z - 20.0)  # sonda 20 mm
        _close(machine.tool_tip(), tip)
        _close(machine.tool_tip(workpiece=True), tip)
    # gantry: oś Y = średnia dwóch napędów
    machine.set_drive_position("drv_y2", 3.4)
    _close(machine.joint_position("Y"), 3.2)


def test_kin_mill_table_moves_workpiece(plant):  # REQ-VM-02
    machine = plant(build_machine(MACHINES / "mill_servo_table.yaml"))
    for letter, value in zip("XYZ", (100.0, 200.0, -30.0), strict=True):
        machine.set_joint_position(letter, value)
    _close(machine.tool_tip(), (0.0, 0.0, -90.0))  # narzędzie stoi w X/Y, rusza stół
    _close(machine.tool_tip(workpiece=True), (100.0, 200.0, -90.0))


def test_kin_xyza(plant):  # REQ-VM-02
    machine = plant(build_machine(MACHINES / "router_xyza.yaml"))
    p = (300.0, 40.0, -20.0)
    for a in (0.0, 30.0, 90.0, -45.0):
        for letter, value in zip("XYZA", (*p, a), strict=True):
            machine.set_joint_position(letter, value)
        _close(machine.tool_tip(), p)
        _close(machine.tool_tip(workpiece=True), _rx(math.radians(a), p))
    machine.set_joint_position("A", 90.0)
    _close(machine.tool_tip(workpiece=True), (300.0, -20.0, -40.0))


def test_kin_trunnion(plant):  # REQ-VM-02
    machine = plant(build_machine(MACHINES / "mill_xyzac_trunnion.yaml"))
    x, y, z = 150.0, 75.0, -40.0
    for a, c in ((0.0, 0.0), (-90.0, 0.0), (-30.0, 45.0), (15.0, 400.0)):
        for letter, value in zip("XYZAC", (x, y, z, a, c), strict=True):
            machine.set_joint_position(letter, value)
        _close(machine.tool_tip(), (x, 0.0, z))  # bez sondy: długość narzędzia 0
        expected = _rz(math.radians(c), _rx(math.radians(a), (x, y, z)))
        _close(machine.tool_tip(workpiece=True), expected)
    machine.set_tool_length(50.0)
    machine.set_joint_position("A", 0.0)
    machine.set_joint_position("C", 0.0)
    _close(machine.tool_tip(workpiece=True), (x, y, z - 50.0))


def test_gantry_skew_alarm(plant):  # REQ-VM-03
    machine = plant(build_machine(MACHINES / "router_gantry_steppers.yaml"))
    machine.set_joint_position("Y", 450.0)
    machine.set_drive_position("drv_y2", 450.4)  # rozjazd 0,4 mm < 0,5 mm
    _close(machine.joint_skew("Y"), -0.4)
    assert "GANTRY_SKEW" not in machine.events()
    machine.set_drive_position("drv_y2", 450.6)
    assert "GANTRY_SKEW" in machine.joint_events("Y")
    assert "GANTRY_SKEW" not in machine.joint_events("X")


def test_gantry_skew_alarm_one_side_fails(plant):  # REQ-VM-03
    machine = plant(build_machine(MACHINES / "router_gantry_steppers.yaml"))
    machine.enable_all(STEPPER_DT)
    machine.clear_events()
    machine.inject_fault("drv_y2", 4)  # przetężenie jednej strony portalu
    machine.move("Y", 455.0, speed=20.0, dt=STEPPER_DT)
    machine.step(STEPPER_DT, 500)
    assert abs(machine.joint_skew("Y")) > 0.5
    assert {"GANTRY_SKEW", "DRIVE_FAULT"} <= machine.events()
    assert machine.drive_state("drv_y1") == "OPERATION_ENABLED"
    assert machine.drive_state("drv_y2") == "FAULT"


def test_hardstop_crash(plant):  # REQ-VM-04
    machine = plant(build_machine(MACHINES / "mill_servo_table.yaml"))
    machine.set_joint_position("X", 598.0)
    machine.enable_all(SERVO_DT)
    machine.clear_events()
    machine.move("X", 601.5, speed=20.0, dt=SERVO_DT)
    assert "CRASH_HARDSTOP" not in machine.events()
    assert "LIMIT_TRIP" in machine.joint_events("X")  # krańcówka 599,5 przed zderzakiem 602
    machine.move("X", 606.0, speed=20.0, dt=SERVO_DT)
    machine.step(SERVO_DT, 50)
    assert "CRASH_HARDSTOP" in machine.joint_events("X")
    assert 0.0 < machine.impact_speed("X") < 50.0
    # drive_fault: true → awaria napędu E-4207 (603Fh = 0xFF01)
    assert machine.drive_state("drv_x") == "FAULT"
    assert machine.drive_error_code("drv_x") == HW_LIMIT_CODE
    assert machine.drive_state("drv_y1") == "OPERATION_ENABLED"


def test_hardstop_without_drive_fault(plant):  # REQ-VM-04
    data = _data("mill_servo_table")
    data["axes"][0]["hardstops"]["drive_fault"] = False
    machine = plant(_model(data))
    machine.set_joint_position("X", 600.0)
    machine.enable_all(SERVO_DT)
    peak = 0.0
    for k in range(1, 201):
        machine.set_joint_target("X", 600.0 + 3.0 * k / 200)
        machine.step(SERVO_DT)
        peak = max(peak, machine.joint_position("X"))
    assert "CRASH_HARDSTOP" in machine.events()
    assert 602.0 < peak < 604.0  # zderzak sprężysty: penetracja zamiast twardego obcięcia
    assert machine.drive_error_code("drv_x") != HW_LIMIT_CODE


def test_limit_switch_trip(plant):  # REQ-VM-05
    machine = plant(build_machine(MACHINES / "router_gantry_steppers.yaml"))
    _at(machine, "X", 10.0)
    assert machine.input("lim_x_min") and machine.input("lim_x_max")  # NC zamknięte
    _at(machine, "X", 0.5)  # punkt zadziałania
    assert not machine.input("lim_x_min")
    assert "LIMIT_TRIP" in machine.joint_events("X")
    _at(machine, "X", 0.65)  # histereza 0,2 mm
    assert not machine.input("lim_x_min")
    _at(machine, "X", 0.75)
    assert machine.input("lim_x_min")
    _at(machine, "X", 599.6)
    assert not machine.input("lim_x_max")
    assert "LIMIT_TRIP" not in machine.joint_events("Y")


def test_limit_switch_trip_while_moving(plant):  # REQ-VM-05
    machine = plant(build_machine(MACHINES / "router_gantry_steppers.yaml"))
    machine.set_joint_position("X", 3.0)
    machine.enable_all(STEPPER_DT)
    machine.clear_events()
    machine.move("X", 0.2, speed=10.0, dt=STEPPER_DT)
    machine.step(STEPPER_DT, 100)  # debounce 1 ms: styk ustalony
    assert "LIMIT_TRIP" in machine.joint_events("X")
    assert not machine.input("lim_x_min")
    assert "CRASH_HARDSTOP" not in machine.events()


def test_shared_limit_input(plant):  # REQ-VM-05
    data = _data("router_gantry_steppers")
    inputs = data["io"]["inputs"]
    for name in ("lim_x_min", "lim_x_max", "lim_y_min", "lim_y_max", "lim_z_max"):
        del inputs[name]
    inputs["limits_chain"] = 1
    for axis in data["axes"]:
        for switch in axis["limits"].values():
            switch["input"] = "limits_chain"
    machine = plant(_model(data))
    assert machine.input("limits_chain")  # łańcuch NC zamknięty
    for letter, position in (("X", 599.8), ("Y", 0.2), ("Z", -0.2)):
        _at(machine, letter, position)
        assert not machine.input("limits_chain"), letter
        middle = 300.0 if letter == "X" else (450.0 if letter == "Y" else -60.0)
        _at(machine, letter, middle)
        assert machine.input("limits_chain"), letter
    assert all("LIMIT_TRIP" in machine.joint_events(letter) for letter in "XYZ")


def test_estop_loop_sto(plant):
    machine = plant(build_machine(MACHINES / "mill_servo_table.yaml"))
    machine.enable_all(SERVO_DT)
    machine.set_estop(True)
    assert not machine.input("estop")
    machine.step(SERVO_DT, 5)
    assert "ESTOP" in machine.events()
    assert all(machine.drive_state(d) == "FAULT" for d in machine.model.drives)
    assert machine.drive_error_code("drv_x") == STO_CODE


def test_estop_loop_quick_stop(plant):
    data = _data("mill_servo_table")
    data["io"]["estop"]["action"] = "quick_stop"
    machine = plant(_model(data))
    machine.enable_all(SERVO_DT)
    machine.set_estop(True)
    machine.step(SERVO_DT, 500)
    states = {machine.drive_state(d) for d in machine.model.drives}
    assert "OPERATION_ENABLED" not in states and "FAULT" not in states


def test_probe_plate_and_box(plant):
    router = plant(build_machine(MACHINES / "router_gantry_steppers.yaml"))
    for letter, value in zip("XYZ", (130.0, 130.0, -79.0), strict=True):
        router.set_joint_position(letter, value)
    assert not router.input("probe")
    router.set_joint_position("Z", -81.0)  # koniec sondy -101 < -100
    assert router.input("probe") and "PROBE" in router.events()
    mill = plant(build_machine(MACHINES / "mill_servo_table.yaml"))
    for letter, value in zip("XYZ", (300.0, 400.0, -45.0), strict=True):
        mill.set_joint_position(letter, value)
    assert mill.input("probe")  # koniec -105 w przygotówce [-110, -90]
    mill.set_joint_position("X", 360.0)
    assert not mill.input("probe")


def test_cli_machine_build():
    result = subprocess.run(
        [sys.executable, "-m", "linumert_plant", "machine", "build",
         str(MACHINES / "mill_xyzac_trunnion.yaml")],
        cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    assert result.returncode == 0, result.stderr
    assert "xyzac-trt-kins" in result.stdout
    assert "A: drv_a" in result.stdout
    bad = subprocess.run(
        [sys.executable, "-m", "linumert_plant", "machine", "build", str(ROOT / "brak.yaml")],
        cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    assert bad.returncode == 1
    assert "nie mozna odczytac" in bad.stderr

