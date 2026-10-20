"""API awarii Plant (`faults.py`, sesja 024): każda awaria — włączenie, skutek, zdjęcie.

Model-Author: Claude

Wymaga rdzenia C (kompilator, Linux/WSL), inaczej testy są pomijane. Master: atrapa
`plant/server/test_master.py` (LRT-NET bez gniazd, lockstep), w teście opóźnienia — UDP.
NIEZWERYFIKOWANE z LinuxCNC (scenariusze z LinuxCNC: tests/test_scenario_linuxcnc.py).
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest
from linumert_plant.faults import FaultError, Faults
from linumert_plant.lrtnet import FLAG_ESTOP_OPEN, FLAG_FAULT
from linumert_plant.server import PlantConfig, PlantServer
from test_master import Master, MasterError

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config" / "machines" / "mill_servo_table.yaml"
ATC = ROOT / "config" / "machines" / "router_atc_rack.yaml"


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


def _server(core, machine: Path = MILL, **cfg) -> PlantServer:
    from linumert_plant.build_machine import build_model
    from linumert_plant.machine_drives import load_machine_drives

    mcfg, drives = load_machine_drives(machine)
    return PlantServer(core.PlantMachine(build_model(mcfg, drives, seed=1)), PlantConfig(**cfg),
                       drive_params={n: i.params for n, i in drives.items()})


def _master(server: PlantServer) -> Master:
    master = Master(len(server.drives), transport=server.handle)
    master.enable()
    return master


def _bit(master: Master, bit: int) -> int:
    return master.last.digital_in >> bit & 1


def _run(master: Master, n: int) -> None:
    for _ in range(n):
        master.exchange()


def test_catalog_lists_all_faults(core) -> None:
    kinds = [f["kind"] for f in Faults.catalog()]
    assert kinds == ["estop", "drive_fault", "frame_loss", "delay", "limit", "axis_jam",
                     "vfd_loss", "atc_sensor", "estop_channel"]
    server = _server(core)
    for kind, params, fragment in (("brak", {}, "nieznana awaria"),
                                   ("drive_fault", {}, "brak parametru drive"),
                                   ("drive_fault", {"drive": "x"}, "nieznany napęd"),
                                   ("drive_fault", {"drive": "drv_x", "code": "ZLY"}, "rodzaj"),
                                   ("limit", {"input": "probe"}, "nie jest wejściem krańcówki"),
                                   ("limit", {"input": "nie_ma"}, "nieznane wejście"),
                                   ("frame_loss", {"percent": 0}, "poza"),
                                   ("axis_jam", {"axis": "Q"}, "nie ma osi"),
                                   ("atc_sensor", {"input": "probe"}, "czujnikiem magazynu")):
        with pytest.raises(FaultError, match=fragment):
            server.faults.inject(kind, **params)
    with pytest.raises(FaultError, match="nie jest aktywna"):
        server.faults.clear("estop")
    assert server.faults.active() == []


def test_estop_fault(core) -> None:
    server = _server(core)
    master = _master(server)
    server.faults.inject("estop")
    _run(master, 20)
    assert master.last.flags & FLAG_ESTOP_OPEN
    assert server.machine.input("estop") is False  # NC: otwarty obwód
    assert "FAULT" in master.states()  # reakcja sto (machine.yaml io.estop.action)
    server.faults.clear("estop")
    master.enable()
    assert not master.last.flags & FLAG_ESTOP_OPEN
    assert all(s == "OPERATION_ENABLED" for s in master.states())


def test_drive_fault_sticky_until_cleared(core) -> None:
    server = _server(core)
    master = _master(server)
    entry = server.faults.inject("drive_fault", drive="drv_z", code="overload")
    assert entry["alarm"] == "E-4202"
    _run(master, 5)
    z = server.drives.index("drv_z")
    assert master.states()[z] == "FAULT" and master.last.flags & FLAG_FAULT
    assert master.last.axes[z].error_code == 0x2350
    with pytest.raises(MasterError):  # fault reset odrzucany, dopóki przyczyna trwa
        master.enable(max_cycles=200)
    server.faults.clear("drive_fault", drive="drv_z")
    master.enable()
    assert master.states()[z] == "OPERATION_ENABLED"


def _lossy(master: Master) -> bool:
    try:
        master.exchange()
        return True
    except MasterError:  # ramka bez odpowiedzi: master i tak idzie dalej (jak wątek servo)
        master.seq = (master.seq + 1) & 0xFFFFFFFF
        master.time_ns += master.cycle_ns
        return False


def test_frame_loss_percent_and_link_loss(core) -> None:  # REQ-QA-03
    server = _server(core)
    master = _master(server)
    server.faults.inject("frame_loss", percent=30)
    answered = sum(_lossy(master) for _ in range(2000))
    assert 1300 < answered < 1500 and server.fault_state.dropped == 2000 - answered
    assert master.last.frames_lost > 0  # Plant widzi dziury w numeracji
    server.faults.clear("frame_loss")
    server.faults.inject("frame_loss", percent=100)  # zerwane łącze
    assert not any(_lossy(master) for _ in range(80))
    server.faults.clear("frame_loss")
    master.exchange()
    assert server.watchdog_tripped and "FAULT" in master.states()  # E-4003
    master.enable()
    assert not server.watchdog_tripped


def test_frame_loss_is_deterministic(core) -> None:  # REQ-QA-04
    def pattern() -> list[bool]:
        server = _server(core)
        master = _master(server)
        server.faults.inject("frame_loss", percent=50)
        return [_lossy(master) for _ in range(300)]

    assert pattern() == pattern()


def test_delay_over_udp(core) -> None:
    server = _server(core, mode="realtime", watchdog_ms=500)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve, args=(sock,), daemon=True)
    thread.start()
    master = Master(len(server.drives), port=sock.getsockname()[1], timeout=2.0)
    try:
        def rtt() -> float:
            t = time.monotonic()
            master.exchange()
            return time.monotonic() - t

        base = min(rtt() for _ in range(5))
        server.faults.inject("delay", ms=40)
        delayed = min(rtt() for _ in range(5))
        server.faults.clear("delay")
        after = min(rtt() for _ in range(5))
    finally:
        server.stop()
        thread.join(timeout=5)
        master.close()
        sock.close()
    assert delayed >= 0.04 > base and after < 0.04


def test_limit_switch_fault(core) -> None:
    server = _server(core)
    master = _master(server)
    bit = server.machine.model.inputs["lim_x_max"]
    assert _bit(master, bit) == 1  # NC w spoczynku zamknięty
    server.faults.inject("limit", input="lim_x_max")
    master.exchange()
    assert _bit(master, bit) == 0
    server.faults.clear("limit", input="lim_x_max")
    master.exchange()
    assert _bit(master, bit) == 1


def test_axis_jam_blocks_motion_and_restores(core) -> None:
    def travel(jam: bool) -> tuple[int, PlantServer]:
        server = _server(core)
        master = _master(server)
        start = master.last.axes[0].actual_pos
        if jam:
            server.faults.inject("axis_jam", axis="X")
        master.move(0, 4_000, 100_000.0, 1_000_000.0)
        _run(master, 50)
        return abs(master.last.axes[0].actual_pos - start), server

    free, _ = travel(False)
    jammed, server = travel(True)
    assert free > 3_900 and jammed < 0.5 * free
    before = dict(server.live_base["drv_x"]["mechanics"])
    server.faults.clear("axis_jam", axis="X")
    values = server.live_values()["drv_x"]
    assert values["mechanics.friction_static"] == before["friction_static"]
    assert values["mechanics.friction_coulomb"] == before["friction_coulomb"]


def test_vfd_loss_without_vfd_section(core) -> None:
    server = _server(core)
    master = _master(server)
    master.spindle_cmd = 6000.0
    _run(master, 3000)
    running = master.last.spindle_actual
    assert running > 5000
    server.faults.inject("vfd_loss")
    _run(master, 6000)
    assert master.last.spindle_actual < 0.3 * running  # wybieg bez napędu
    server.faults.clear("vfd_loss")
    _run(master, 3000)
    assert master.last.spindle_actual > 5000


def test_vfd_loss_with_vfd_section_silences_modbus(core) -> None:
    from linumert_plant.vfd import VfdConfig

    server = _server(core, vfd=VfdConfig(device=None, modbus_port=0))
    server.faults.inject("vfd_loss")
    assert server.vfd_faults.comm_lost
    server.faults.clear("vfd_loss")
    assert not server.vfd_faults.comm_lost


def test_atc_sensor_stuck(core) -> None:
    server = _server(core, ATC)
    master = _master(server)
    bit = server.machine.model.inputs["tool_clamped"]
    normal = _bit(master, bit)
    server.faults.inject("atc_sensor", input="tool_clamped", closed=not normal)
    _run(master, 2)
    assert _bit(master, bit) == int(not normal)
    assert [f["kind"] for f in server.faults.active()] == ["atc_sensor"]
    server.faults.clear_all()
    _run(master, 2)
    assert _bit(master, bit) == normal and server.faults.active() == []


def test_estop_two_channels_mirror_and_stuck_channel(core) -> None:
    """Kanał B (estop_b) = kanał A tego samego grzyba; awaria estop_channel blokuje B."""
    server = _server(core)
    master = _master(server)
    a, b = server.machine.model.inputs["estop"], server.machine.model.inputs["estop_b"]
    _run(master, 2)
    assert (_bit(master, a), _bit(master, b)) == (1, 1)
    server.faults.inject("estop")
    _run(master, 2)
    assert (_bit(master, a), _bit(master, b)) == (0, 0)  # grzyb: oba kanały otwarte
    server.faults.clear("estop")
    server.faults.inject("estop_channel", closed=False)
    _run(master, 2)
    assert (_bit(master, a), _bit(master, b)) == (1, 0)  # rozbieżność → lrt_estop2.fault
    server.faults.clear("estop_channel")
    _run(master, 2)
    assert _bit(master, b) == 1
