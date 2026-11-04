"""Wrzeciono VFD w Plant: model, ramki hy_vfd, Modbus PDU i TCP (sesja 021).

Model-Author: Claude

Bez LinuxCNC: ramki jak w hy_comm.c (LinuxCNC 2.9) budowane w teście. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import os
import select
import socket
import struct
import threading
import tty

import pytest

from linumert_plant.drive_library import load_library
from linumert_plant.vfd import (
    CMD_RUN_FWD,
    CMD_RUN_REV,
    CMD_STOP,
    DEFAULT_MODBUS_MAP,
    FAULT_DRIVE,
    FAULT_NONE,
    FAULT_OVERLOAD,
    HyVfdProtocol,
    HyVfdPty,
    ModbusMap,
    ModbusTcpServer,
    SpindleModel,
    VfdFaults,
    crc16_modbus,
    seal,
)

DT = 0.001


def spindle(**kw) -> SpindleModel:
    tpl = load_library()["spindle_vfd_22kw"]

    class Cfg:
        class spindle:  # noqa: N801 — atrapa MachineConfig.spindle
            max_rpm = kw.get("max_rpm", 24000.0)
            min_rpm = kw.get("min_rpm", 6000.0)
            ramp_up_s = kw.get("ramp_up_s", 2.0)
            ramp_down_s = kw.get("ramp_down_s", 2.0)

    return SpindleModel.from_machine(Cfg, tpl)


def run(sp: SpindleModel, seconds: float) -> None:
    for _ in range(round(seconds / DT)):
        sp.step(DT)


def query(fn: int, *data: int) -> bytes:
    """Ramka zapytania jak hy_comm.c build_query_packet: adres, funkcja, długość, dane, CRC."""
    return seal(bytes([1, fn, len(data), *data]))


# --- CRC i ramki -------------------------------------------------------------------------------

def test_crc_known_vectors():
    # REQ-VD-01
    assert crc16_modbus(bytes.fromhex("01030000000A")) == 0xCDC5
    assert seal(bytes.fromhex("01030000000A"))[-2:] == bytes.fromhex("C5CD")
    assert crc16_modbus(b"") == 0xFFFF


@pytest.mark.parametrize(("fn", "data", "resp_len"), [
    (0x01, (5, 0, 0), 8), (0x02, (4, 0x13, 0x88), 8), (0x03, (CMD_STOP,), 6),
    (0x04, (1,), 8), (0x05, (0x27, 0x10), 7),
])
def test_hy_vfd_lengths_match_hy_comm(fn, data, resp_len):
    # REQ-VD-01 — długości zapytań i odpowiedzi jak compute_response_length w hy_comm.c
    proto = HyVfdProtocol(spindle())
    frame = query(fn, *data)
    assert len(frame) == HyVfdProtocol.QUERY_LEN[fn]
    reply = proto.handle(frame)
    assert reply is not None and len(reply) == resp_len
    assert crc16_modbus(reply[:-2]) == struct.unpack("<H", reply[-2:])[0]


def test_hy_vfd_rejects_bad_crc_and_other_slave():
    proto = HyVfdProtocol(spindle())
    frame = bytearray(query(0x04, 0))
    frame[-1] ^= 0xFF
    assert proto.handle(bytes(frame)) is None and proto.bad_crc == 1
    assert proto.handle(seal(bytes([2, 0x04, 1, 0]))) is None


def test_hy_vfd_parameters_and_rpm_mapping():
    # REQ-VD-01 — PD005/PD144 jak w hy_vfd: rated_motor_rev = PD144 / 50 · PD005
    sp = spindle()
    proto = HyVfdProtocol(sp)
    pd005 = proto.handle(query(0x01, 5, 0, 0))
    pd144 = proto.handle(query(0x01, 144, 0, 0))
    max_freq = (pd005[4] << 8 | pd005[5]) / 100.0
    rpm_at_50 = pd144[4] << 8 | pd144[5]
    assert rpm_at_50 / 50.0 * max_freq == pytest.approx(24000, rel=1e-3)
    # zapis PD144 (hy_vfd -S) zmienia przeliczenie Hz → obr/min
    proto.handle(query(0x02, 144, 0x2E, 0xE0))  # 12000 obr/min przy 50 Hz
    proto.handle(query(0x05, 0x13, 0x88))       # 50,00 Hz
    proto.handle(query(0x03, CMD_RUN_FWD))
    assert sp.command_rpm == pytest.approx(12000)


def test_hy_vfd_run_stop_and_status():
    # REQ-VD-01
    sp = spindle()
    proto = HyVfdProtocol(sp)
    proto.handle(query(0x05, 0x4E, 0x20))  # 200,00 Hz
    state = proto.handle(query(0x03, CMD_RUN_FWD))[3]
    assert state & 0x01 and not state & 0x04
    assert sp.command_rpm == pytest.approx(12000)
    run(sp, 4.0)
    out_f = proto.handle(query(0x04, 1))
    assert (out_f[4] << 8 | out_f[5]) == pytest.approx(20000, abs=200)
    rott = proto.handle(query(0x04, 3))
    assert (rott[4] << 8 | rott[5]) == pytest.approx(12000, abs=120)
    assert proto.handle(query(0x04, 0))[4:6] == bytes([0x4E, 0x20])  # SetF
    state = proto.handle(query(0x03, CMD_STOP))[3]
    assert not state & 0x01 and state & 0x08  # zatrzymuje się, jeszcze się kręci
    run(sp, 4.0)
    assert sp.rpm == pytest.approx(0, abs=1)


def test_hy_vfd_reverse():
    sp = spindle()
    proto = HyVfdProtocol(sp)
    proto.handle(query(0x05, 0x4E, 0x20))
    state = proto.handle(query(0x03, CMD_RUN_REV))[3]
    assert state & 0x04
    run(sp, 4.0)
    assert sp.rpm == pytest.approx(-12000, rel=0.02)
    assert proto.handle(query(0x03, CMD_RUN_REV))[3] & 0x20  # pracuje wstecz
    assert sp.at_speed


# --- model ------------------------------------------------------------------------------------

def test_ramp_reaches_max_in_ramp_up_time():
    # REQ-VD-01 — rampa falownika 0 → max w ramp_up_s, at-speed po dojściu wału
    sp = spindle(ramp_up_s=2.0)
    sp.set_speed(24000, True)
    run(sp, 1.0)
    assert sp.ramp_rpm == pytest.approx(12000, rel=0.01)
    assert not sp.at_speed
    run(sp, 1.0)
    assert sp.ramp_rpm == pytest.approx(24000)
    run(sp, 3.0)
    assert sp.at_speed and sp.fault == FAULT_NONE


def test_at_speed_tolerance_and_min_rpm():
    sp = spindle()
    sp.set_speed(1000, True)  # poniżej min_rpm → min_rpm
    assert sp.command_rpm == 6000
    run(sp, 2.0)
    assert sp.at_speed
    sp.set_speed(6200, True)  # 3 % różnicy → poza tolerancją 2 %
    assert not sp.at_speed
    sp.set_speed(6000, False)
    assert not sp.at_speed


def test_overload_trips_after_i2t():
    # REQ-VD-01 — obciążenie 2 N·m > znamionowy 1,75 N·m → FAULT_OVERLOAD po I²t, potem wybieg
    sp = spindle()
    sp.set_speed(6000, True)
    run(sp, 2.0)
    sp.load_torque = 2.0
    run(sp, 3.0)
    assert sp.fault == FAULT_NONE
    run(sp, 30.0)
    assert sp.fault == FAULT_OVERLOAD and not sp.running
    run(sp, 10.0)
    assert sp.rpm == pytest.approx(0, abs=1)
    sp.reset_fault()
    assert sp.fault == FAULT_NONE and sp.i2t == 0.0


def test_drive_fault_coasts_without_torque():
    # REQ-VD-01 — błąd falownika = wyłączone wyjście, wybieg na tarciu (wolniej niż rampa)
    sp = spindle()
    sp.set_speed(12000, True)
    run(sp, 4.0)
    sp.fault = FAULT_DRIVE
    run(sp, 0.5)
    assert sp.torque == 0.0
    assert sp.rpm > 9000  # rampa hamowania zeszłaby do 6000; wybieg na tarciu wolniej
    sp.set_speed(12000, True)
    assert not sp.running  # błąd blokuje start


# --- Modbus -----------------------------------------------------------------------------------

def test_modbus_pdu_write_read_and_exceptions():
    # REQ-VD-01 — funkcje 3, 4, 6, 16 i wyjątki 01/02/03
    sp = spindle()
    mb = ModbusMap(sp)
    m = DEFAULT_MODBUS_MAP
    assert mb.handle_pdu(struct.pack(">BHH", 6, m["speed_cmd"], 9000)) == struct.pack(
        ">BHH", 6, m["speed_cmd"], 9000)
    req = struct.pack(">BHHB", 16, m["command"], 2, 4) + struct.pack(">HH", 1, 9000)
    assert mb.handle_pdu(req) == req[:5]
    assert sp.running and sp.command_rpm == 9000
    run(sp, 3.0)
    resp = mb.handle_pdu(struct.pack(">BHH", 3, 0, 7))
    assert resp[:2] == bytes([3, 14])
    regs = dict(zip(m, struct.unpack(">7H", resp[2:]), strict=True))
    assert regs["speed_actual"] == pytest.approx(9000, abs=90)
    assert regs["status"] & 0b11 == 0b11 and regs["fault_code"] == 0
    assert mb.handle_pdu(struct.pack(">BHH", 4, m["status"], 1))[0] == 4
    assert mb.handle_pdu(bytes([0x2B, 0, 0])) == bytes([0xAB, 1])          # nieznana funkcja
    assert mb.handle_pdu(struct.pack(">BHH", 6, 99, 1)) == bytes([0x86, 2])  # zły adres
    assert mb.handle_pdu(struct.pack(">BHH", 3, 0, 0)) == bytes([0x83, 3])   # zła liczba
    assert mb.handle_pdu(bytes([3, 0])) == bytes([0x83, 3])                  # ucięta ramka


def test_modbus_reverse_and_fault_reset():
    sp = spindle()
    mb = ModbusMap(sp)
    mb.write(DEFAULT_MODBUS_MAP["speed_cmd"], 8000)
    mb.write(DEFAULT_MODBUS_MAP["command"], 3)
    assert sp.command_rpm == -8000
    sp.fault, sp.running = FAULT_DRIVE, False
    assert mb.read(DEFAULT_MODBUS_MAP["status"]) & 8
    assert mb.read(DEFAULT_MODBUS_MAP["fault_code"]) == FAULT_DRIVE
    mb.write(DEFAULT_MODBUS_MAP["command"], 4 | 1)
    assert sp.fault == FAULT_NONE and sp.running


def mbap(tid: int, pdu: bytes) -> bytes:
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, 1) + pdu


def test_modbus_tcp_localhost_and_comm_lost():
    # REQ-VD-01 — komunikacja Modbus TCP na localhost; utrata komunikacji = brak odpowiedzi
    sp = spindle()
    faults = VfdFaults()
    server = ModbusTcpServer(ModbusMap(sp), "127.0.0.1", 0, threading.Lock(), faults).start()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=2) as conn:
            conn.sendall(mbap(7, struct.pack(">BHH", 6, DEFAULT_MODBUS_MAP["speed_cmd"], 7000)))
            resp = conn.recv(64)
            assert struct.unpack(">HHHB", resp[:7]) == (7, 0, 6, 1)
            assert resp[7:] == struct.pack(">BHH", 6, DEFAULT_MODBUS_MAP["speed_cmd"], 7000)
            faults.comm_lost = True
            conn.sendall(mbap(8, struct.pack(">BHH", 3, 0, 2)))
            conn.settimeout(0.5)
            with pytest.raises(TimeoutError):
                conn.recv(64)
            faults.comm_lost = False
            conn.settimeout(2)
            conn.sendall(mbap(9, struct.pack(">BHH", 3, 0, 2)))
            resp = conn.recv(64)
            assert resp[:2] == b"\x00\x09" and resp[7:] == bytes([3, 4, 0, 0, 0x1B, 0x58])
    finally:
        server.close()


def test_hy_vfd_over_pty(tmp_path):
    # REQ-VD-01 — transport jak hy_vfd -d <dowiązanie>: ramka przez pseudoterminal
    sp = spindle()
    faults = VfdFaults()
    link = tmp_path / "hy_vfd"
    pty = HyVfdPty(HyVfdProtocol(sp), str(link), threading.Lock(), faults).start()
    fd = os.open(link, os.O_RDWR | os.O_NOCTTY)
    try:
        tty.setraw(fd)

        def ask(frame: bytes, n: int) -> bytes:
            os.write(fd, frame)
            data = b""
            while len(data) < n:
                ready, _, _ = select.select([fd], [], [], 1.0)
                if not ready:
                    break
                data += os.read(fd, n - len(data))
            return data

        reply = ask(query(0x05, 0x13, 0x88), 7)
        assert reply == seal(bytes([1, 0x05, 2, 0x13, 0x88]))
        faults.comm_lost = True
        assert ask(query(0x04, 0), 8) == b""
        faults.comm_lost = False
        assert len(ask(query(0x04, 0), 8)) == 8
    finally:
        os.close(fd)
        pty.close()
    assert not link.exists()


# --- integracja z serwerem Plant ----------------------------------------------------------------

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"


def test_plant_yaml_vfd_section(tmp_path):
    from linumert_plant.server import PlantConfigError, load_plant_config

    cfg_file = tmp_path / "plant.yaml"
    cfg_file.write_text("vfd: {device: run/hy_vfd, modbus_port: 1502, slave: 2,\n"
                        "      modbus_map: {command: 10, speed_cmd: 11}}\n", encoding="utf-8")
    vfd = load_plant_config(cfg_file).vfd
    assert vfd.device == tmp_path / "run" / "hy_vfd"
    assert (vfd.modbus_port, vfd.slave, vfd.modbus_map) == (1502, 2, {"command": 10,
                                                                     "speed_cmd": 11})
    cfg_file.write_text("vfd: {slave: 300, modbus_map: {foo: 1}}\n", encoding="utf-8")
    with pytest.raises(PlantConfigError) as err:
        load_plant_config(cfg_file)
    msg = str(err.value)
    assert "device" in msg and "vfd.slave" in msg and "foo" in msg


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


def _server(core, vfd=None):
    from linumert_plant.build_machine import build_machine
    from linumert_plant.server import PlantConfig, PlantServer

    machine = core.PlantMachine(build_machine(MACHINE))
    return PlantServer(machine, PlantConfig(vfd=vfd))


def test_server_spindle_from_lrt_net(core):
    # REQ-VD-01 — bez sekcji vfd wrzeciono zadaje spindle_cmd; spindle_actual z modelu
    from test_master import Master

    server = _server(core)
    assert server.spindle.max_rpm == 8000 and server.spindle.inertia == pytest.approx(8e-4)
    master = Master(len(server.drives), transport=server.handle)
    master.spindle_cmd = -3000.0
    for _ in range(3000):
        master.exchange()
    assert master.last.spindle_actual == pytest.approx(-3000, rel=0.02)
    assert server.report()["spindle"]["fault"] == FAULT_NONE
    master.spindle_cmd = 0.0
    for _ in range(3000):
        master.exchange()
    assert master.last.spindle_actual == pytest.approx(0, abs=1)


def test_server_spindle_over_modbus_tcp(core):
    # REQ-VD-01 — sekcja vfd: Modbus TCP steruje wrzecionem, LRT-NET tylko odczytuje obroty
    from test_master import Master

    from linumert_plant.vfd import VfdConfig, start_servers

    server = _server(core, VfdConfig(modbus_port=0))
    servers = start_servers(server.cfg.vfd, server.spindle, server._lock, server.vfd_faults)
    master = Master(len(server.drives), transport=server.handle)
    master.spindle_cmd = 5000.0  # ignorowane przy falowniku
    try:
        port = servers[0].port
        with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
            pdu = struct.pack(">BHHB", 16, 0, 2, 4) + struct.pack(">HH", 1, 4000)
            conn.sendall(mbap(1, pdu))
            assert conn.recv(64)[7:] == pdu[:5]
            for _ in range(3000):
                master.exchange()
            assert master.last.spindle_actual == pytest.approx(4000, rel=0.02)
            conn.sendall(mbap(2, struct.pack(">BHH", 3, DEFAULT_MODBUS_MAP["status"], 1)))
            assert conn.recv(64)[-2:] == b"\x00\x03"  # pracuje i at-speed
    finally:
        for srv in servers:
            srv.close()
