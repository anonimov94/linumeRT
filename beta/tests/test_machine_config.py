"""Testy schematu i walidacji machine.yaml (sesja 010)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from linumert.machine.schema import MachineConfigError, parse_machine
from linumert.machine.validate import load_valid_machine, validate_machine

ROOT = Path(__file__).resolve().parent.parent
MACHINES = sorted((ROOT / "config" / "machines").glob("*.yaml"))
BASE = yaml.safe_load((ROOT / "config/machines/router_gantry_steppers.yaml").read_text("utf-8"))


def _check(mutate) -> list[str]:
    data = copy.deepcopy(BASE)
    mutate(data)
    try:
        cfg = parse_machine(data)
    except MachineConfigError as exc:
        return exc.errors
    return validate_machine(cfg)


def _axis(data, letter):
    return next(a for a in data["axes"] if a["letter"] == letter)


def test_examples_exist():
    assert len(MACHINES) >= 5


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.name)
def test_examples_valid(path):  # REQ-VM-01
    # jedyne zrodlo prawdy: kazdy przyklad ladowany tym samym kodem co Plant i generator
    cfg = load_valid_machine(path)
    assert cfg.machine.name == path.stem


def test_single_source_loader():  # REQ-VM-01
    import linumert.machine.schema as schema

    assert schema.load_machine is not None
    assert not hasattr(schema, "load_machine_for_plant")


def test_unknown_field_rejected():  # REQ-VM-11
    errors = _check(lambda d: d["machine"].update(kolor="czerwony"))
    assert any("machine.kolor" in e and "nieznane pole" in e for e in errors)


def test_missing_estop_rejected():  # REQ-VM-11
    errors = _check(lambda d: d["io"].pop("estop"))
    assert any("io.estop" in e and "brak wymaganego pola" in e for e in errors)


def test_estop_input_undefined():  # REQ-VM-11
    errors = _check(lambda d: d["io"]["estop"].update(input="nie_ma"))
    assert any("io.estop.input" in e for e in errors)


def test_duplicate_axis_letter():  # REQ-VM-11
    errors = _check(lambda d: d["axes"].append(copy.deepcopy(_axis(d, "X"))))
    assert any("os X wystepuje wiecej niz raz" in e for e in errors)


def test_preset_axes_mismatch():  # REQ-VM-11
    errors = _check(lambda d: d["kinematics"].update(preset="xyza_rotary"))
    assert any("kinematics.preset" in e for e in errors)


def test_preset_and_chain_together():  # REQ-VM-11
    link = {"id": "a", "kind": "linear", "axis": [1, 0, 0]}
    errors = _check(lambda d: d["kinematics"].update(chain=[link]))
    assert any("dokladnie jedno" in e for e in errors)


def test_chain_unknown_parent():  # REQ-VM-11
    def mutate(d):
        link = {"id": "x", "kind": "linear", "axis": [1, 0, 0], "parent": "zz"}
        d["kinematics"] = {"chain": [link]}

    assert any("nieznany czlon zz" in e for e in _check(mutate))


def test_soft_limits_outside_travel():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X").update(soft_limits=[-5, 599]))
    assert any("axes[0].soft_limits" in e and "travel" in e for e in errors)


def test_travel_reversed():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X").update(travel=[600, 0]))
    assert any("axes[0].travel" in e for e in errors)


def test_limit_switch_inside_soft_range():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X")["limits"]["min"].update(position=50))
    assert any("limits.min.position" in e for e in errors)


def test_hardstop_before_limit_switch():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X")["hardstops"]["max"].update(position=599))
    assert any("hardstops.max.position" in e for e in errors)


def test_unknown_drive_reference():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X").update(drives=["brak"]))
    assert any("nieznany naped brak" in e for e in errors)


def test_duplicate_drive_name():  # REQ-VM-11
    extra = {"name": "drv_x", "template": "stepper_open_loop"}
    errors = _check(lambda d: d["drives"].append(extra))
    assert any("powtorzona nazwa napedu drv_x" in e for e in errors)


def test_drive_shared_between_axes():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "Z").update(drives=["drv_x"]))
    assert any("drv_x" in e and "wielu osi" in e for e in errors)


def test_spindle_drive_unknown():  # REQ-VM-11
    errors = _check(lambda d: d["spindle"].update(drive="brak"))
    assert any("spindle.drive" in e for e in errors)


def test_gantry_requires_squaring():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "Y")["homing"].update(gantry_square=False))
    assert any("gantry_square" in e for e in errors)


def test_gantry_requires_skew_limit():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "Y").pop("gantry_max_skew"))
    assert any("gantry_max_skew" in e for e in errors)


def test_single_drive_with_skew_rejected():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X").update(gantry_max_skew=1.0))
    assert any("tylko osi z wieloma napedami" in e for e in errors)


def test_homing_switch_without_sensor():  # REQ-VM-11
    def mutate(d):
        axis = _axis(d, "X")
        axis.pop("home_sensor")
        axis["limits"].pop("min")
        axis["hardstops"].pop("min")

    assert any("axes[0].homing.method" in e for e in _check(mutate))


def test_hardstop_homing_needs_parameters():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X")["homing"].update(method="hardstop"))
    assert any("hardstop wymaga pol" in e for e in errors)


def test_xy_homed_before_z():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "Z")["homing"].update(order=5))
    assert any("przed osia Z" in e for e in errors)


def test_limit_input_undefined():  # REQ-VM-11
    errors = _check(lambda d: d["io"]["inputs"].pop("lim_x_min"))
    assert any("lim_x_min nie jest zdefiniowane" in e for e in errors)


def test_duplicate_io_pin():  # REQ-VM-11
    errors = _check(lambda d: d["io"]["inputs"].update(lim_x_max=1))
    assert any("io.inputs: numer 1 uzyty wielokrotnie" in e for e in errors)


def test_spindle_rpm_order():  # REQ-VM-11
    errors = _check(lambda d: d["spindle"].update(min_rpm=30000))
    assert any("spindle.min_rpm" in e for e in errors)


def test_safe_z_out_of_range():  # REQ-VM-11
    errors = _check(lambda d: d["positions"].update(safe_z=50))
    assert any("positions.safe_z" in e for e in errors)


def test_forbidden_zone_inverted():  # REQ-VM-11
    zone = {"name": "imadlo", "min": [10, 10, -50], "max": [5, 20, -10]}
    errors = _check(lambda d: d.update(forbidden_zones=[zone]))
    assert any("forbidden_zones[0]" in e for e in errors)


def test_toolchanger_slots_mismatch():  # REQ-VM-11
    tc = {"type": "rack_linear", "slots": 3, "slot_positions": [[0, 0, 0]]}
    errors = _check(lambda d: d.update(toolchanger=tc))
    assert any("toolchanger.slot_positions" in e for e in errors)


def test_manual_changer_with_slots():  # REQ-VM-11
    errors = _check(lambda d: d.update(toolchanger={"type": "manual", "slots": 2}))
    assert any("toolchanger.slots" in e for e in errors)


def test_collision_box_wrong_size():  # REQ-VM-11
    body = {
        "name": "b",
        "shape": "box",
        "attached_to": "table",
        "size": [10, 10],
        "position": [0, 0, 0],
    }
    errors = _check(lambda d: d.update(collision_bodies=[body]))
    assert any("collision_bodies[0]" in e for e in errors)


def test_negative_speed_rejected():  # REQ-VM-11
    errors = _check(lambda d: _axis(d, "X").update(max_velocity=-1))
    assert any("axes[0].max_velocity" in e and "wieksza niz 0" in e for e in errors)


def test_unknown_template_when_library_given():  # REQ-VM-11
    cfg = parse_machine(copy.deepcopy(BASE))
    errors = validate_machine(cfg, drive_templates={"servo_cia402"})
    assert any("brak szablonu stepper_nema23_3nm" in e for e in errors)


def test_errors_collected_together():  # REQ-VM-11
    def mutate(d):
        _axis(d, "X").update(drives=["brak"])
        d["spindle"].update(min_rpm=99999)

    errors = _check(mutate)
    assert len(errors) >= 2


def test_bad_yaml_file(tmp_path):  # REQ-VM-11
    path = tmp_path / "zly.yaml"
    path.write_text("a: [", encoding="utf-8")
    with pytest.raises(MachineConfigError) as info:
        load_valid_machine(path)
    assert "niepoprawny YAML" in info.value.errors[0]


def test_missing_file(tmp_path):  # REQ-VM-11
    with pytest.raises(MachineConfigError):
        load_valid_machine(tmp_path / "brak.yaml")


def test_root_not_mapping():  # REQ-VM-11
    with pytest.raises(MachineConfigError):
        parse_machine([1, 2])
