"""Bazowanie po rozruchu w Plant z atrapą mastera w stylu LinuxCNC (sesja 015, REQ-VM-07).

Model-Author: Claude
Scenariusze REQ-VM-07: home_switch, home_switch_index, home_hardstop, home_absolute,
home_drive_internal, home_gantry_square; do tego start losowy z ziarna i plik stanu.
Master widzi tylko wejścia i impulsy (jak LinuxCNC); dokładność sprawdzamy rzeczywistym
położeniem osi z Plant. Testy wymagają kompilatora C (Linux/WSL), inaczej są pomijane.
NIEZWERYFIKOWANE z LinuxCNC i na sprzęcie (sesja 018: te same scenariusze z homemod).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from linumert.machine.schema import parse_machine
from linumert_plant.build_machine import ENC_ABSOLUTE, ENC_IDEAL, ENC_INCREMENTAL, build_model
from linumert_plant.drive_library import load_library
from linumert_plant.machine_drives import resolve_machine_drives

ROOT = Path(__file__).resolve().parents[1]
MACHINES = ROOT / "config" / "machines"
SERVO_DT = 1e-3
BATTERY_CODE = 0xFF03  # 603Fh awarii ENCODER_BATTERY (E-4211)


@pytest.fixture(scope="module")
def plant():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding.PlantMachine


def _data(name: str) -> dict:
    return yaml.safe_load((MACHINES / f"{name}.yaml").read_text(encoding="utf-8"))


def _axis(data: dict, letter: str) -> dict:
    return next(a for a in data["axes"] if a["letter"] == letter)


def _model(data: dict, seed: int = 1, start: str = "random"):
    cfg = parse_machine(data)
    return build_model(cfg, resolve_machine_drives(cfg, load_library()), seed=seed, start=start)


def _started(plant, data: dict, seed: int = 1):
    from linumert_plant.homing_master import HomingMaster

    machine = plant(_model(data, seed))
    master = HomingMaster(machine)
    machine.enable_all(master.plant_dt)
    return machine, master


# ---- start po włączeniu --------------------------------------------------------------------


def test_random_start_seed_in_soft_limits(plant):  # REQ-VM-07
    data = _data("mill_servo_table")
    a = plant(_model(data, seed=11))
    b = plant(_model(data, seed=11))
    c = plant(_model(data, seed=12))
    for axis in a.model.config.axes:
        lo, hi = axis.soft_limits
        assert lo <= a.joint_position(axis.letter) <= hi
        assert a.joint_position(axis.letter) == b.joint_position(axis.letter)
    assert any(a.joint_position(x.letter) != c.joint_position(x.letter)
               for x in a.model.config.axes)
    center = plant(_model(data, start="center"))
    assert center.joint_position("X") == pytest.approx(300.0)
    with pytest.raises(ValueError, match="start"):
        _model(data, start="state")


def test_encoders_per_axis_type():  # REQ-VM-07
    servo = _model(_data("mill_servo_table"))
    assert servo.encoders["drv_x"] == ENC_INCREMENTAL
    steppers = _model(_data("router_gantry_steppers"))
    assert steppers.encoders["drv_x"] == ENC_IDEAL  # krokowiec bez sprzężenia: brak enkodera
    data = _data("mill_servo_table")
    _axis(data, "Z")["homing"] = {"method": "absolute", "order": 0}
    assert _model(data).encoders["drv_z"] == ENC_ABSOLUTE
    assert servo.counts_per_unit["drv_x"] == pytest.approx(131072 / 10.0, rel=1e-4)  # 10 mm/obr


def test_incremental_encoder_reports_zero_until_homed(plant):  # REQ-VM-07
    machine, _ = _started(plant, _data("mill_servo_table"), seed=3)
    assert machine.joint_position("X") > 1.0          # oś stoi gdzieś w przejeździe...
    assert abs(machine.position_actual("drv_x")) <= 2  # ...a master widzi zero


# ---- metody a–e ----------------------------------------------------------------------------


def test_home_switch(plant):  # REQ-VM-07 (a): krańcówka/czujnik, zjazd i dojazd latch_speed
    data = _data("mill_servo_table")
    _axis(data, "X")["homing"] = {"method": "switch", "direction": -1, "search_speed": 40,
                                  "latch_speed": 4, "order": 1}
    physical, starts = [], set()
    for seed in (1, 2, 3):
        machine, master = _started(plant, data, seed)
        starts.add(round(machine.joint_position("X"), 3))
        master.home_axis("X")
        assert master.position("X") == pytest.approx(0.0, abs=0.01)
        master.move("X", 100.0, 50.0)
        physical.append(machine.joint_position("X") - 100.0)
        assert machine.drive_state("drv_x") == "OPERATION_ENABLED"
    assert len(starts) == 3  # trzy różne starty po włączeniu
    # Baza = zadziałanie krańcówki X min (0,5 mm) przy dojeździe 4 mm/s, niezależnie od startu.
    # Tolerancja: okres mastera 1 ms (4 µm) + drgania styku 1 ms (4 µm) + luz śruby 10 µm
    # (krańcówka po stronie stołu, enkoder na silniku).
    for value in physical:
        assert value == pytest.approx(0.5, abs=0.02)
    assert max(physical) - min(physical) < 0.008


def test_home_switch_release(plant):  # REQ-VM-07 (a): wolny zjazd, baza na zwolnieniu styku NC
    data = _data("mill_servo_table")
    _axis(data, "X")["homing"] = {"method": "switch", "direction": -1, "search_speed": 40,
                                  "latch_speed": 1, "latch": "release", "order": 1}
    physical = []
    for seed in (1, 2):
        machine, master = _started(plant, data, seed)
        master.home_axis("X")
        assert master.position("X") == pytest.approx(0.0, abs=0.01)
        # Krańcówka X min 0,5 mm, histereza 0,2 mm: styk NC zamyka się znowu przy 0,7 mm;
        # stół stoi tam, gdzie styk się zwolnił (1 mm/s: okres mastera i drgania styku ~2 µm).
        assert machine.joint_position("X") == pytest.approx(0.7, abs=0.005)
        master.move("X", 100.0, 50.0)
        physical.append(machine.joint_position("X") - 100.0)
    assert max(physical) - min(physical) < 0.008  # powtarzalność bazy


def test_home_switch_index_release(plant):  # REQ-VM-07 (b): indeks szukany od krańcówki
    data = _data("mill_servo_table")
    _axis(data, "X")["homing"]["latch"] = "release"
    machine, master = _started(plant, data, 4)
    master.home_axis("X")
    master.move("X", 50.0, 50.0)
    assert machine.joint_position("X") - 50.0 == pytest.approx(10.0, abs=0.02)


def test_latch_release_only_for_switch_methods():
    from linumert.machine.schema import Homing

    with pytest.raises(ValueError, match="latch: release"):
        Homing(method="hardstop", latch="release", reduced_torque_pct=20, detect="torque",
               detect_threshold=100, detect_time_ms=20)


def test_home_switch_index(plant):  # REQ-VM-07 (b): czujnik + impuls indeksu
    data = _data("mill_servo_table")  # X: switch_index w przykładzie
    physical = []
    for seed in (4, 5):
        machine, master = _started(plant, data, seed)
        master.home_axis("X")
        master.move("X", 50.0, 50.0)
        physical.append(machine.joint_position("X") - 50.0)
    # Indeks silnika co 10 mm (śruba 10 mm/obr): pierwszy za krańcówką 0,5 mm to 10 mm.
    # Tolerancja: odczyt indeksu co 1 ms (4 µm) + luz 10 µm; powtarzalność bez drgań styku.
    for value in physical:
        assert value == pytest.approx(10.0, abs=0.02)
    assert max(physical) - min(physical) < 0.005  # indeks dokładniejszy niż sam czujnik


@pytest.mark.parametrize("detect,threshold", [("torque", 180.0), ("following_error", 0.05)])
def test_home_hardstop(plant, detect, threshold):  # REQ-VM-07 (c): twardy zderzak
    data = _data("mill_servo_table")
    x = _axis(data, "X")
    x["hardstops"]["drive_fault"] = False  # zderzak jest bazą: bez awarii E-4207
    x["homing"] = {"method": "hardstop", "direction": -1, "search_speed": 4, "latch_speed": 1,
                   "order": 1, "reduced_torque_pct": 20, "detect": detect,
                   "detect_threshold": threshold, "detect_time_ms": 20}
    machine, master = _started(plant, data, seed=6)
    limit_before = machine.od_read("drv_x", 0x6072)
    master.home_axis("X")
    assert machine.od_read("drv_x", 0x6072) == limit_before  # limit momentu przywrócony
    assert machine.drive_state("drv_x") == "OPERATION_ENABLED"   # bez błędu nadążania
    assert "CRASH_HARDSTOP" in machine.joint_events("X")
    master.move("X", 20.0, 20.0)
    # Zderzak X min na -2 mm, sztywność 500 N/mm. Przy 20 % momentu (1,27 N·m, śruba 10 mm/obr)
    # siła docisku F = 0,254 N·m · 2π / 10 mm ≈ 160 N, wgniecenie najwyżej F/k ≈ 0,32 mm;
    # detekcja (próg, czas) zatrzaskuje bazę wcześniej, ale już w zderzaku.
    home = machine.joint_position("X") - 20.0
    assert -2.33 < home < -2.0


def test_home_absolute(plant, tmp_path):  # REQ-VM-07 (d): enkoder absolutny i bateria
    from linumert_plant.homing_master import HomingError, HomingMaster
    from linumert_plant.plant_state import apply_state, load_state, save_state

    data = _data("mill_servo_table")
    _axis(data, "Z")["homing"] = {"method": "absolute", "order": 0}
    state = tmp_path / "plant_state.json"

    # Uruchomienie 1: pierwsze włączenie, pozycja z enkodera, jazda, wyłączenie (zapis stanu).
    machine, master = _started(plant, data, seed=7)
    master.home_axis("Z")  # bez ruchu
    z_counts = machine.position_actual("drv_z")
    machine.hold_position("drv_z")
    for _ in range(50):
        master.tick()
    save_state(machine, state)
    physical = machine.joint_position("Z")
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["drives"]["drv_z"]["absolute"]["valid"] is True

    # Uruchomienie 2: inny losowy start, ale stan z pliku: ta sama pozycja i impulsy.
    machine2 = plant(_model(data, seed=99))
    apply_state(machine2, load_state(state))
    master2 = HomingMaster(machine2)
    machine2.enable_all(SERVO_DT)
    assert machine2.joint_position("Z") == pytest.approx(physical, abs=1e-6)
    assert machine2.position_actual("drv_z") == pytest.approx(z_counts, abs=3)
    master2.home_axis("Z")
    machine2.set_battery("drv_z", False)  # bateria pada w czasie pracy...
    assert machine2.position_actual("drv_z") == pytest.approx(z_counts, abs=3)  # ...bez skutku
    save_state(machine2, state)

    # Uruchomienie 3: po wyłączeniu bez baterii licznik obrotów przepadł: E-4211.
    machine3 = plant(_model(data, seed=5))
    apply_state(machine3, load_state(state))
    for _ in range(3000):  # rozruch napędu (boot_time_s), potem awaria przy pierwszej ocenie
        machine3.step(SERVO_DT)
        if machine3.drive_state("drv_z") != "NOT_READY":
            break
    machine3.step(SERVO_DT, 2)
    assert machine3.drive_state("drv_z") == "FAULT"
    assert machine3.drive_error_code("drv_z") == BATTERY_CODE
    assert 0 <= machine3.position_actual("drv_z") < 131072  # został jeden obrót
    master3 = HomingMaster(machine3)
    with pytest.raises(HomingError, match="E-4211"):
        master3.home_axis("Z")
    machine3.set_controlword("drv_z", 0x0080)  # reset awarii
    machine3.step(SERVO_DT, 2)
    machine3.enable_all(SERVO_DT)
    with pytest.raises(HomingError, match="nieważna"):
        master3.home_axis("Z")
    master3.set_absolute_home("Z")  # ustawienie bazy: tryb 6, metoda 35 (607Ch = offset)
    assert master3.home_axis("Z").drives["drv_z"].homed
    assert machine3.absolute_state("drv_z")[1] is True


def test_home_drive_internal(plant):  # REQ-VM-07 (e): bazowanie w napędzie CiA 402 (tryb 6)
    data = _data("mill_servo_table")
    _axis(data, "X")["homing"] = {"method": "drive", "cia402_method": 17, "direction": -1,
                                  "search_speed": 40, "latch_speed": 4, "order": 1}
    physical = []
    for seed in (8, 9):
        machine, master = _started(plant, data, seed)
        result = master.home_axis("X")
        assert result.drives["drv_x"].homed
        assert machine.od_read("drv_x", 0x6061) == 8  # z powrotem CSP
        master.move("X", 30.0, 50.0)
        physical.append(machine.joint_position("X") - 30.0)
    # Metoda 17: baza na zboczu zwolnienia krańcówki (0,5 mm + histereza 0,2 mm). Napęd widzi
    # styk z opóźnieniem jednego kroku 1 ms i do 1 ms drgań styku; przy 4 mm/s to do ok. 12 µm,
    # plus luz 10 µm i dojazd po bazie.
    for value in physical:
        assert 0.7 <= value <= 0.735
    assert max(physical) - min(physical) < 0.012


def test_home_drive_internal_error_is_reported(plant):  # REQ-VM-07 (e)
    from linumert_plant.homing_master import HomingError

    data = _data("mill_servo_table")
    _axis(data, "X")["homing"] = {"method": "drive", "cia402_method": 7, "order": 1}
    machine, master = _started(plant, data, seed=1)
    with pytest.raises(HomingError, match="E-4210"):
        master.home_axis("X")


def test_home_gantry_square(plant):  # REQ-VM-07: wyrównanie gantry na dwóch czujnikach
    data = _data("mill_servo_table")
    data["io"]["inputs"]["lim_y_min_2"] = 8  # czujnik drugiej strony belki
    machine = plant(_model(data, seed=10))
    y1 = machine.drive_position("drv_y1")
    machine.set_drive_position("drv_y2", y1 + 0.4)  # belka skrzywiona po wyłączeniu
    from linumert_plant.homing_master import HomingMaster

    master = HomingMaster(machine)
    machine.enable_all(SERVO_DT)
    assert machine.joint_skew("Y") == pytest.approx(-0.4, abs=1e-6)
    master.home_axis("Y")
    master.move("Y", 200.0, 50.0)
    assert abs(machine.joint_skew("Y")) < 0.01
    assert machine.joint_position("Y") - 200.0 == pytest.approx(0.5, abs=0.01)

    # Bez czujnika drugiej strony u mastera bazowanie z wyrównaniem jest niemożliwe.
    from linumert_plant.homing_master import HomingError

    machine, master = _started(plant, _data("mill_servo_table"), seed=10)
    with pytest.raises(HomingError, match="_2"):
        master.home_axis("Y")


def test_home_all_order_and_stepper_router(plant):  # REQ-VM-07: kolejność osi, krokowce
    data = copy.deepcopy(_data("router_gantry_steppers"))
    data["io"]["inputs"]["lim_y_min_2"] = 8
    machine, master = _started(plant, data, seed=2)
    results = master.home_all()
    assert list(results) == ["Z", "X", "Y"]  # order: Z=0, potem X i Y
    for letter in ("X", "Y", "Z"):
        assert all(d.homed for d in results[letter].drives.values())
    assert machine.drive_state("drv_x") == "OPERATION_ENABLED"
    master.move("X", 100.0, 50.0)
    assert machine.lost_steps("drv_x") == 0
    # Krokowiec: luz 20 µm, master zna tylko pozycję zadaną.
    assert machine.joint_position("X") - 100.0 == pytest.approx(0.5, abs=0.035)


# ---- plik stanu ----------------------------------------------------------------------------


def test_state_file_roundtrip_and_errors(plant, tmp_path):  # REQ-VM-07
    from linumert_plant.plant_state import PlantStateError, apply_state, load_state, save_state

    data = _data("mill_servo_table")
    machine = plant(_model(data, seed=1))
    machine.set_drive_position("drv_y2", machine.drive_position("drv_y1") + 0.3)
    path = save_state(machine, tmp_path / "s.json")
    other = plant(_model(data, seed=2))
    apply_state(other, load_state(path))
    for drive in ("drv_x", "drv_y1", "drv_y2", "drv_z"):
        assert other.drive_position(drive) == pytest.approx(machine.drive_position(drive))
    assert other.joint_skew("Y") == pytest.approx(-0.3, abs=1e-9)  # rozjazd też przetrwał

    state = load_state(path)
    wrong = dict(state, machine="inna")
    with pytest.raises(PlantStateError, match="inna"):
        apply_state(plant(_model(data)), wrong)
    bad = copy.deepcopy(state)
    bad["drives"]["drv_nieznany"] = {"position": 1.0}
    bad["drives"]["drv_x"]["absolute"] = {"offset": 1, "valid": True}
    with pytest.raises(PlantStateError, match="drv_nieznany.*drv_x.absolute|drv_x.absolute"):
        apply_state(plant(_model(data)), bad)
    (tmp_path / "zly.json").write_text("{", encoding="utf-8")
    with pytest.raises(PlantStateError, match="uszkodzony"):
        load_state(tmp_path / "zly.json")
    with pytest.raises(PlantStateError, match="brak pliku"):
        load_state(tmp_path / "nie_ma.json")
    (tmp_path / "v2.json").write_text('{"version": 2}', encoding="utf-8")
    with pytest.raises(PlantStateError, match="wersja"):
        load_state(tmp_path / "v2.json")
