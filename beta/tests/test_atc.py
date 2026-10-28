"""Magazyn narzędzi, pozycje wymiany i kolizje w Plant (REQ-VM-08, VM-09, VM-10; sesja 020).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 020.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

from linumert.machine.schema import parse_machine
from linumert_plant.atc import ToolChangerModel, ToolSetterModel, ToolSpec, pocket_positions
from linumert_plant.collisions import CollisionModel

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "config" / "machines" / "router_atc_rack.yaml"
MILL = ROOT / "config" / "machines" / "mill_servo_table.yaml"
DT = 0.001


def _data(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _router(**tc) -> ToolChangerModel:
    data = _data(ROUTER)
    data["toolchanger"].update(tc)
    return ToolChangerModel.from_config(parse_machine(data), {3: ToolSpec(40.0, 10.0)})


def _out(model: ToolChangerModel, *roles: str) -> int:
    mask = 0
    for role in roles:
        mask |= 1 << model.io_out[model.roles_out[role]]
    return mask


def _run(model, seconds, nose, outputs=0):
    events = []
    for _ in range(round(seconds / DT)):
        events += model.step(DT, nose, outputs)
    return events


def _sensor(model, role) -> bool:
    mask, value = model.inputs()
    bit = 1 << model.io_in[model.sensor_names[role]]
    assert mask & bit
    return bool(value & bit)


def test_atc_rack_geometry():  # REQ-VM-08: atc_rack_geometry
    cfg = parse_machine(_data(ROUTER))
    assert pocket_positions(cfg.toolchanger) == [(20 + 60 * i, 20, -20) for i in range(6)]
    data = _data(ROUTER)
    data["toolchanger"]["base_orientation_deg"] = 90
    rotated = pocket_positions(parse_machine(data).toolchanger)
    assert [p[:2] for p in rotated] == [pytest.approx((20, 20 + 60 * i)) for i in range(6)]
    data["toolchanger"]["slot_positions"] = [[10 * i, 5, 0] for i in range(6)]
    listed = pocket_positions(parse_machine(data).toolchanger)
    assert listed == [(10 * i, 5, -20) for i in range(6)]  # wysokość gniazda = approach_z


def test_atc_carousel_index():  # REQ-VM-08: atc_carousel_index
    data = _data(ROUTER)
    data["io"]["outputs"]["carousel_step"] = 4
    data["io"]["inputs"]["carousel_pos"] = 10
    data["toolchanger"] = {"type": "carousel", "slots": 8, "base_position": [400, 100, -5],
                           "radius_mm": 100, "approach_z": -20, "retract_z": -5,
                           "index_ms": 500, "sensors": {"carousel_in_position": "carousel_pos"},
                           "outputs": {"carousel_step": "carousel_step"}}
    m = ToolChangerModel.from_config(parse_machine(data))
    far, step = (0, 0, 0), _out(m, "carousel_step")
    assert m.carousel_pos == 0 and _sensor(m, "carousel_in_position")
    _run(m, 0.25, far, step)
    assert not _sensor(m, "carousel_in_position") and m.active_pockets() == []
    _run(m, 0.26, far, step)  # 500 ms od zbocza
    assert m.carousel_pos == 1 and _sensor(m, "carousel_in_position")
    _run(m, 1.0, far, step)  # stałe wyjście: bez kolejnego kroku
    assert m.carousel_pos == 1
    _run(m, 0.01, far, 0)
    _run(m, 0.6, far, step)
    assert m.carousel_pos == 2 and m.active_pockets() == [2]


def test_atc_cover_timing():  # REQ-VM-08: atc_cover_timing
    m = _router()
    far, cover = (500, 500, 0), _out(m, "cover_open")
    assert _sensor(m, "cover_closed") and not _sensor(m, "cover_open")
    _run(m, 0.01, far, cover)
    assert not _sensor(m, "cover_closed") and not _sensor(m, "cover_open")
    _run(m, 0.78, far, cover)
    assert not _sensor(m, "cover_open")
    _run(m, 0.02, far, cover)  # 800 ms
    assert _sensor(m, "cover_open")
    _run(m, 0.8, far, 0)
    assert _sensor(m, "cover_closed")


def test_rack_tool_exchange_physics():  # REQ-VM-08: wymiana tylko w gnieździe, zacisk z czasem
    m = _router()
    cover, release = _out(m, "cover_open"), _out(m, "cover_open", "clamp_release")
    above, pocket = (140, 20, -5), (140, 20, -20)  # gniazdo 3 (T3)
    _run(m, 0.85, above, cover)
    assert _run(m, 0.35, above, release) == [] and not m.clamped and not _sensor(m, "clamped")
    assert _run(m, 0.1, pocket, release) == []  # pusty, zwolniony: wejście w oprawkę
    events = _run(m, 0.35, pocket, cover)  # zaciśnięcie
    assert [e.kind for e in events] == ["TOOL_PICKED"] and m.spindle_tool == 3
    assert m.slots[2] is None and _sensor(m, "clamped") and m.tool_spec().length == 40.0
    _run(m, 0.1, above, cover)
    events = _run(m, 0.35, (170, 20, -5), release)  # zwolnienie między gniazdami
    assert [e.kind for e in events] == ["TOOL_DROP"] and m.spindle_tool is None


def test_rack_clamp_fault_and_cover_crash():  # REQ-VM-08
    m = _router()
    cover = _out(m, "cover_open")
    _run(m, 0.85, (20, 20, -5), cover)
    events = _run(m, 0.05, (20, 20, -20), cover)  # puste wrzeciono, zacisk zamknięty, T1
    assert [e.kind for e in events] == ["CLAMP_FAULT"] and events[0].tool == 1
    m2 = _router()
    events = _run(m2, 0.05, (80, 20, -15), 0)  # osłona zamknięta, nos pod retract_z nad regałem
    assert [e.kind for e in events] == ["COVER_CRASH"]


def test_manual_change_position():  # REQ-VM-09: manual_change_position
    m = ToolChangerModel.from_config(parse_machine(_data(MILL)))
    assert m.type == "manual" and m.manual_pos == (300, 450, -5)
    assert m.manual_change(4, (300.5, 449.5, -5.0)) is None and m.spindle_tool == 4
    ev = m.manual_change(5, (100, 100, -5))
    assert ev is not None and ev.kind == "MANUAL_CHANGE_POSITION" and m.spindle_tool == 5


def test_toolsetter_measure():  # REQ-VM-09: toolsetter_measure
    cfg = parse_machine(_data(ROUTER))
    ts = ToolSetterModel.from_config(cfg)
    assert ts.top == -70 and ts.bit == 6
    length = 42.0
    contact_nose = None
    for i in range(400):  # zjazd nosem co 0,1 mm nad czujnikiem
        nose_z = -10.0 - i * 0.1
        if ts.contact((50.0, 50.0, nose_z - length)):
            contact_nose = nose_z
            break
    assert contact_nose is not None
    assert contact_nose - ts.top == pytest.approx(length, abs=0.1)  # zmierzona długość
    assert not ts.contact((80.0, 50.0, -80.0))  # obok czujnika


def test_crash_head_magazine():  # REQ-VM-10: crash_head_magazine
    col = CollisionModel.from_config(parse_machine(_data(ROUTER)))
    tool = ToolSpec(50.0, 10.0)
    assert col.check(DT, (20, 20, -20), tool, exchange_aligned=True) == []  # wymiana w gnieździe
    assert col.check(DT, (170, 20, -10), None) == []
    events = col.check(DT, (170, 20, -40), None)
    assert [e.pair for e in events] == [("wrzeciono", "magazyn")]
    assert events[0].depth_mm == pytest.approx(10.0)
    assert col.check(DT, (170, 20, -41), None) == []  # ta sama kolizja: bez powtórzenia
    events = col.check(DT, (500, 500, -10), tool)
    assert events == []
    events = col.check(DT, (170, 20, -10), tool)  # narzędzie (50 mm) w magazynie poza gniazdem
    assert [e.pair for e in events] == [("narzedzie", "magazyn")]


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(str(exc))
    return core_binding


def test_magazine_io_over_lrtnet(core):  # REQ-VM-08: wejścia/wyjścia magazynu w LRT-NET
    from linumert_plant.build_machine import build_machine
    from linumert_plant.server import PlantConfig, PlantServer

    sys.path.insert(0, str(ROOT / "plant" / "server"))
    from test_master import Master

    server = PlantServer(core.PlantMachine(build_machine(ROUTER)), PlantConfig())
    master = Master(len(server.drives), transport=server.handle)
    cfg = parse_machine(copy.deepcopy(_data(ROUTER)))
    bits = cfg.io.inputs
    master.exchange()
    assert master.last.digital_in >> bits["cover_closed"] & 1
    assert master.last.digital_in >> bits["tool_clamped"] & 1
    master.digital_out = 1 << cfg.io.outputs["cover_open"] | 1 << cfg.io.outputs["tool_release"]
    for _ in range(850):
        master.exchange()
    din = master.last.digital_in
    assert din >> bits["cover_opened"] & 1 and not din >> bits["cover_closed"] & 1
    assert not din >> bits["tool_clamped"] & 1  # zacisk zwolniony po 300 ms
    assert server.report()["slots"] == [1, 2, 3, 4, 5, 6]
