"""Wrzeciono z falownikiem (VFD) w Plant: model, protokół hy_vfd (RTU) i Modbus TCP (sesja 021).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 021.

Model: bezwładność, krzywa momentu i tarcie z szablonu napędu wrzeciona (plant/library/drives),
rampa falownika (`spindle.ramp_up_s` / `ramp_down_s` z machine.yaml), obciążenie [N·m]
(parametr w locie), przeciążenie I²t, at-speed (tolerancja 2 %).

Protokół zgodny z komponentem LinuxCNC `hy_vfd` (ramki RTU z kodami funkcji 0x01–0x05 i CRC
Modbus; kod własny, z opisu ramek): 0x01/0x02 odczyt/zapis parametru PDnnn, 0x03 polecenie
(0x01 praca w przód, 0x11 wstecz, 0x08 stop) z odpowiedzią bajtem stanu, 0x04 odczyt statusu
(0 SetF, 1 OutF [0,01 Hz], 2 OutA [0,1 A], 3 obroty [obr/min], 4 DCV, 5 ACV, 6 licznik, 7 temp.),
0x05 częstotliwość zadana [0,01 Hz]. Transport: pseudoterminal (`os.openpty`) z dowiązaniem
pod ścieżką urządzenia (`hy_vfd -d <ścieżka>`); między VM: socat pty ↔ TCP (docs/PLANT_START.md).

Modbus TCP (dla `mb2hal`): rejestry holding/input z mapy (plant.yaml `vfd.modbus_map`), funkcje
3, 4, 6, 16. Wstrzykiwanie: utrata komunikacji (serwery milczą), błąd falownika, przeciążenie.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import contextlib
import math
import os
import select
import socket
import struct
import threading
from dataclasses import dataclass, field
from pathlib import Path

TWO_PI = 2.0 * math.pi
AT_SPEED_TOL = 0.02

# hy_vfd: bajt stanu (odpowiedź na 0x03)
ST_RUN, ST_JOG, ST_CMD_REV, ST_RUNNING, ST_JOGGING, ST_RUNNING_REV, ST_BRAKING = (
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40)
CMD_RUN_FWD, CMD_RUN_REV, CMD_STOP = 0x01, 0x11, 0x08

DEFAULT_MODBUS_MAP = {
    # holding (zapis z mastera)
    "command": 0,        # bit0 praca, bit1 wstecz, bit2 kasowanie błędu
    "speed_cmd": 1,      # [obr/min]
    # input / holding (odczyt)
    "speed_actual": 2,   # [obr/min]
    "status": 3,         # bit0 pracuje, bit1 at-speed, bit2 wstecz, bit3 błąd
    "current_x10": 4,    # [0,1 A]
    "load_pct": 5,       # [%] momentu znamionowego
    "fault_code": 6,     # 0 brak, 1 błąd falownika, 2 przeciążenie
}
FAULT_NONE, FAULT_DRIVE, FAULT_OVERLOAD = 0, 1, 2


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def seal(frame: bytes) -> bytes:
    """Ramka RTU + CRC (młodszy bajt pierwszy, jak w Modbus RTU)."""
    return frame + struct.pack("<H", crc16_modbus(frame))


@dataclass
class SpindleModel:
    max_rpm: float
    min_rpm: float = 0.0
    ramp_up_s: float = 2.0
    ramp_down_s: float = 2.0
    inertia: float = 8e-4                     # [kg·m²] wirnik + obciążenie
    curve: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 2.6), (2600.0, 0.0)])
    rated_torque: float = 1.75
    torque_constant: float = 0.175            # [N·m/A]
    friction_coulomb: float = 0.01
    friction_viscous: float = 2e-4
    peak_time_s: float = 5.0
    max_freq_hz: float = 400.0                # PD005
    load_torque: float = 0.0                  # [N·m] obciążenie z procesu (w locie)
    # stan
    command_rpm: float = 0.0                  # ze znakiem (kierunek)
    ramp_rpm: float = 0.0                     # wyjście rampy falownika
    omega: float = 0.0                        # [rad/s] wał
    torque: float = 0.0
    running: bool = False
    fault: int = FAULT_NONE
    i2t: float = 0.0

    @classmethod
    def from_machine(cls, cfg, template: dict | None) -> SpindleModel:
        sp = cfg.spindle
        model = cls(max_rpm=sp.max_rpm, min_rpm=sp.min_rpm, ramp_up_s=sp.ramp_up_s,
                    ramp_down_s=sp.ramp_down_s)
        if template:
            motor, mech = template.get("motor", {}), template.get("mechanics", {})
            model.inertia = float(motor.get("rotor_inertia", 6e-4)) + float(mech.get("load", 0.0))
            model.curve = [(float(o), float(t)) for o, t in motor.get("torque_curve", model.curve)]
            model.rated_torque = float(motor.get("rated_torque", model.rated_torque))
            model.torque_constant = float(motor.get("torque_constant", model.torque_constant))
            model.peak_time_s = float(motor.get("peak_time_s", model.peak_time_s))
            model.friction_coulomb = float(mech.get("friction_coulomb", model.friction_coulomb))
            model.friction_viscous = float(mech.get("friction_viscous", model.friction_viscous))
        return model

    @property
    def rpm(self) -> float:
        return self.omega * 60.0 / TWO_PI

    def available_torque(self, omega: float) -> float:
        w = abs(omega)
        pts = self.curve
        if w <= pts[0][0]:
            return pts[0][1]
        for (w0, t0), (w1, t1) in zip(pts, pts[1:], strict=False):
            if w <= w1:
                return t0 + (t1 - t0) * (w - w0) / (w1 - w0)
        return 0.0

    def set_speed(self, rpm: float, run: bool) -> None:
        """Polecenie falownika: prędkość ze znakiem (minus = wstecz) i praca/stop."""
        rpm = max(-self.max_rpm, min(self.max_rpm, rpm))
        if run and 0 < abs(rpm) < self.min_rpm:
            rpm = math.copysign(self.min_rpm, rpm)
        self.command_rpm = rpm if run else 0.0
        self.running = run and self.fault == FAULT_NONE

    def reset_fault(self) -> None:
        self.fault = FAULT_NONE
        self.i2t = 0.0

    def step(self, dt: float) -> None:
        goal = self.command_rpm if self.running and self.fault == FAULT_NONE else 0.0
        up = self.max_rpm / self.ramp_up_s * dt
        down = self.max_rpm / self.ramp_down_s * dt
        diff = goal - self.ramp_rpm
        rate = up if abs(goal) > abs(self.ramp_rpm) else down
        self.ramp_rpm += max(-rate, min(rate, diff))
        # regulator prędkości falownika: moment do śledzenia rampy, ograniczony krzywą
        target = self.ramp_rpm * TWO_PI / 60.0
        if self.fault != FAULT_NONE:
            drive = 0.0  # wybieg (falownik wyłączył wyjście)
        else:
            want = self.inertia * (target - self.omega) / max(dt, 1e-4) * 0.5
            want += self.friction_viscous * target + math.copysign(
                self.friction_coulomb, target) * (target != 0.0) + math.copysign(
                self.load_torque, target) * (target != 0.0)
            limit = self.available_torque(self.omega)
            drive = max(-limit, min(limit, want))
        sign = math.copysign(1.0, self.omega) if self.omega != 0.0 else 0.0
        resist = self.friction_viscous * self.omega + sign * (self.friction_coulomb
                                                              + self.load_torque)
        before = self.omega
        self.omega += (drive - resist) / self.inertia * dt
        # opór bierny (tarcie, obciążenie) zatrzymuje wał, ale nie odwraca kierunku
        if before * self.omega < 0 and abs(drive) <= self.friction_coulomb + self.load_torque:
            self.omega = 0.0
        if self.fault != FAULT_NONE and abs(self.omega) < 0.5:
            self.omega = 0.0
        self.torque = drive
        # przeciążenie I²t (jak napędy osi): ponad znamionowy przez peak_time_s
        if self.peak_time_s > 0:
            excess = (self.torque ** 2 - self.rated_torque ** 2) * dt
            self.i2t = max(0.0, self.i2t + excess)
            limit = (self.available_torque(0.0) ** 2 - self.rated_torque ** 2) * self.peak_time_s
            if self.fault == FAULT_NONE and limit > 0 and self.i2t > limit:
                self.fault = FAULT_OVERLOAD
                self.running = False

    @property
    def at_speed(self) -> bool:
        if not self.running or self.command_rpm == 0.0:
            return False
        return abs(self.rpm - self.command_rpm) <= AT_SPEED_TOL * abs(self.command_rpm)

    @property
    def current(self) -> float:
        return abs(self.torque) / self.torque_constant if self.torque_constant else 0.0

    @property
    def out_freq_hz(self) -> float:
        return abs(self.rpm) / self.max_rpm * self.max_freq_hz if self.max_rpm else 0.0


class HyVfdProtocol:
    """Odpowiedzi falownika na ramki hy_vfd (bez transportu; testowalne)."""

    QUERY_LEN = {0x01: 8, 0x02: 8, 0x03: 6, 0x04: 6, 0x05: 7}

    def __init__(self, spindle: SpindleModel, slave: int = 1):
        self.sp = spindle
        self.slave = slave
        rpm_at_50 = spindle.max_rpm / spindle.max_freq_hz * 50.0
        self.params = {4: 5000, 5: round(spindle.max_freq_hz * 100), 11: 0,
                       141: 220, 142: 100, 143: 2, 144: round(rpm_at_50)}
        self.set_freq = 0           # [0,01 Hz]
        self.cmd_state = 0          # ostatnie polecenie (bajt stanu)
        self.bad_crc = 0

    def _state_byte(self) -> int:
        st = 0
        if self.sp.running:
            st |= ST_RUN
        if self.sp.command_rpm < 0:
            st |= ST_CMD_REV
        if abs(self.sp.rpm) > 1.0:
            st |= ST_RUNNING
            if self.sp.rpm < 0:
                st |= ST_RUNNING_REV
        if self.sp.running is False and abs(self.sp.rpm) > 1.0:
            st |= ST_BRAKING
        return st

    @property
    def rpm_per_hz(self) -> float:
        """Jak hy_vfd: obroty silnika z PD144 (obr/min przy 50 Hz)."""
        return self.params.get(144, 0) / 50.0

    def _apply_speed(self) -> None:
        rpm = self.set_freq / 100.0 * self.rpm_per_hz
        run = self.cmd_state in (CMD_RUN_FWD, CMD_RUN_REV)
        self.sp.set_speed(-rpm if self.cmd_state == CMD_RUN_REV else rpm, run)

    def status(self, code: int) -> int:
        sp = self.sp
        out_f = abs(sp.rpm) / self.rpm_per_hz if self.rpm_per_hz else 0.0
        values = {0: self.set_freq, 1: round(out_f * 100), 2: round(sp.current * 10),
                  3: round(abs(sp.rpm)), 4: 540, 5: 380 if sp.running else 0, 6: 0, 7: 35}
        return values.get(code, 0) & 0xFFFF

    def handle(self, frame: bytes) -> bytes | None:
        """Jedna kompletna ramka zapytania (z CRC). Zwraca odpowiedź albo None."""
        if len(frame) < 4 or frame[0] != self.slave:
            return None
        if struct.unpack("<H", frame[-2:])[0] != crc16_modbus(frame[:-2]):
            self.bad_crc += 1
            return None
        fn = frame[1]
        if fn in (0x01, 0x02):
            param, data = frame[3], frame[4] << 8 | frame[5]
            if fn == 0x02:
                self.params[param] = data
                if param == 5 and data:
                    self.sp.max_freq_hz = data / 100.0
            value = self.params.get(param, 0)
            return seal(bytes([self.slave, fn, 3, param, value >> 8 & 0xFF, value & 0xFF]))
        if fn == 0x03:
            cmd = frame[3]
            if cmd in (CMD_RUN_FWD, CMD_RUN_REV, CMD_STOP):
                self.cmd_state = cmd
                self._apply_speed()
            return seal(bytes([self.slave, fn, 1, self._state_byte()]))
        if fn == 0x04:
            code = frame[3]
            value = self.status(code)
            return seal(bytes([self.slave, fn, 3, code, value >> 8, value & 0xFF]))
        if fn == 0x05:
            self.set_freq = frame[3] << 8 | frame[4]
            self._apply_speed()
            return seal(bytes([self.slave, fn, 2, frame[3], frame[4]]))
        return None


class ModbusMap:
    """Mapa rejestrów falownika dla Modbus TCP (mb2hal)."""

    def __init__(self, spindle: SpindleModel, mapping: dict[str, int] | None = None):
        self.sp = spindle
        self.map = dict(DEFAULT_MODBUS_MAP if mapping is None else mapping)
        self.command = 0
        self.speed_cmd = 0

    def read(self, addr: int) -> int:
        sp = self.sp
        values = {
            "command": self.command, "speed_cmd": self.speed_cmd,
            "speed_actual": round(abs(sp.rpm)),
            "status": (1 if abs(sp.rpm) > 1 else 0) | (2 if sp.at_speed else 0)
            | (4 if sp.command_rpm < 0 else 0) | (8 if sp.fault else 0),
            "current_x10": round(sp.current * 10),
            "load_pct": round(abs(sp.torque) / sp.rated_torque * 100) if sp.rated_torque else 0,
            "fault_code": sp.fault,
        }
        for name, reg in self.map.items():
            if reg == addr:
                return values.get(name, 0) & 0xFFFF
        return 0

    def write(self, addr: int, value: int) -> bool:
        name = next((n for n, r in self.map.items() if r == addr), None)
        if name == "command":
            self.command = value
            if value & 4:
                self.sp.reset_fault()
        elif name == "speed_cmd":
            self.speed_cmd = value
        else:
            return False
        run, rev = bool(self.command & 1), bool(self.command & 2)
        self.sp.set_speed(-self.speed_cmd if rev else self.speed_cmd, run)
        return True

    def handle_pdu(self, pdu: bytes) -> bytes:
        """PDU Modbus (bez nagłówka MBAP) → PDU odpowiedzi (wyjątki 01/02/03)."""
        fn = pdu[0]
        try:
            if fn in (3, 4):
                start, count = struct.unpack(">HH", pdu[1:5])
                if not 1 <= count <= 125:
                    return bytes([fn | 0x80, 3])
                regs = [self.read(start + i) for i in range(count)]
                return bytes([fn, 2 * count]) + struct.pack(f">{count}H", *regs)
            if fn == 6:
                addr, value = struct.unpack(">HH", pdu[1:5])
                return pdu[:5] if self.write(addr, value) else bytes([fn | 0x80, 2])
            if fn == 16:
                start, count, nbytes = struct.unpack(">HHB", pdu[1:6])
                values = struct.unpack(f">{count}H", pdu[6:6 + nbytes])
                ok = all(self.write(start + i, v) for i, v in enumerate(values))
                return pdu[:5] if ok else bytes([fn | 0x80, 2])
        except struct.error:
            return bytes([fn | 0x80, 3])
        return bytes([fn | 0x80, 1])


@dataclass
class VfdConfig:
    """Sekcja `vfd` w plant.yaml: transport falownika (co najmniej jeden)."""

    device: Path | None = None        # dowiązanie pty dla `hy_vfd -d` (RTU)
    modbus_listen: str = "127.0.0.1"
    modbus_port: int | None = None    # Modbus TCP dla mb2hal (0 = port wolny, testy)
    slave: int = 1
    modbus_map: dict[str, int] | None = None

    @classmethod
    def from_dict(cls, data: dict, base: Path) -> VfdConfig:
        device = data.get("device")
        port = data.get("modbus_port")
        mapping = data.get("modbus_map")
        return cls(device=None if device in (None, "") else base / str(device),
                   modbus_listen=str(data.get("modbus_listen", "127.0.0.1")),
                   modbus_port=None if port is None else int(port),
                   slave=int(data.get("slave", 1)),
                   modbus_map=None if mapping is None else {str(k): int(v)
                                                            for k, v in mapping.items()})

    def problems(self) -> list[str]:
        errors = []
        if self.device is None and self.modbus_port is None:
            errors.append("vfd: podaj device (hy_vfd) albo modbus_port (Modbus TCP)")
        if self.modbus_port is not None and not 0 <= self.modbus_port < 65536:
            errors.append(f"vfd.modbus_port: {self.modbus_port} poza 0–65535")
        if not 1 <= self.slave <= 247:
            errors.append(f"vfd.slave: {self.slave} poza 1–247")
        if self.modbus_map is not None:
            unknown = sorted(set(self.modbus_map) - set(DEFAULT_MODBUS_MAP))
            if unknown:
                errors.append(f"vfd.modbus_map: nieznane rejestry {', '.join(unknown)}")
            if len(set(self.modbus_map.values())) != len(self.modbus_map):
                errors.append("vfd.modbus_map: powtórzony adres rejestru")
        return errors


@dataclass
class VfdFaults:
    comm_lost: bool = False       # serwery nie odpowiadają (utrata komunikacji)


class HyVfdPty:
    """Pseudoterminal z protokołem hy_vfd; dowiązanie `link` → /dev/pts/N dla hy_vfd -d."""

    def __init__(self, protocol: HyVfdProtocol, link: str, lock: threading.Lock,
                 faults: VfdFaults):
        self.protocol, self.link, self.lock, self.faults = protocol, link, lock, faults
        self.master, slave = os.openpty()
        self.slave_name = os.ttyname(slave)
        self._slave_fd = slave  # trzymany otwarty: pty nie znika między połączeniami hy_vfd
        with contextlib.suppress(FileNotFoundError):
            os.unlink(link)
        os.symlink(self.slave_name, link)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name="hy_vfd-pty", daemon=True)

    def start(self) -> HyVfdPty:
        self.thread.start()
        return self

    def _run(self) -> None:
        buf = b""
        while not self._stop.is_set():
            ready, _, _ = select.select([self.master], [], [], 0.1)
            if not ready:
                buf = b""  # przerwa w transmisji = koniec ramki
                continue
            try:
                buf += os.read(self.master, 256)
            except OSError:
                continue
            while len(buf) >= 2:
                need = HyVfdProtocol.QUERY_LEN.get(buf[1])
                if need is None:
                    buf = buf[1:]
                    continue
                if len(buf) < need:
                    break
                frame, buf = buf[:need], buf[need:]
                with self.lock:
                    reply = None if self.faults.comm_lost else self.protocol.handle(frame)
                if reply is not None:
                    os.write(self.master, reply)

    def close(self) -> None:
        self._stop.set()
        self.thread.join(timeout=1)
        with contextlib.suppress(OSError):
            os.unlink(self.link)
        os.close(self.master)
        os.close(self._slave_fd)


def _recv_exact(conn: socket.socket, n: int) -> bytes | None:
    data = b""
    while len(data) < n:
        try:
            chunk = conn.recv(n - len(data))
        except TimeoutError:
            continue
        except OSError:
            return None
        if not chunk:
            return None
        data += chunk
    return data


class ModbusTcpServer:
    """Prosty serwer Modbus TCP (jedno połączenie naraz wystarcza dla mb2hal)."""

    def __init__(self, mapping: ModbusMap, host: str, port: int, lock: threading.Lock,
                 faults: VfdFaults, unit: int = 1):
        self.map, self.lock, self.faults, self.unit = mapping, lock, faults, unit
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(2)
        self.sock.settimeout(0.2)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name="modbus-tcp", daemon=True)

    def start(self) -> ModbusTcpServer:
        self.thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except (TimeoutError, OSError):
                continue
            with conn:
                conn.settimeout(0.2)
                while not self._stop.is_set():
                    try:
                        head = conn.recv(7)
                    except TimeoutError:
                        continue
                    except OSError:
                        break
                    if len(head) < 7:
                        break
                    tid, proto, length, unit = struct.unpack(">HHHB", head)
                    pdu = _recv_exact(conn, length - 1)
                    if pdu is None:
                        break
                    with self.lock:
                        if self.faults.comm_lost or proto != 0:
                            continue
                        resp = self.map.handle_pdu(pdu)
                    conn.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)

    def close(self) -> None:
        self._stop.set()
        self.thread.join(timeout=1)
        self.sock.close()


def start_servers(cfg: VfdConfig, spindle: SpindleModel, lock: threading.Lock,
                  faults: VfdFaults) -> list:
    """Uruchamia transporty z `cfg`; zwraca obiekty z `close()` (błąd: zamyka już otwarte)."""
    started: list = []
    try:
        if cfg.device is not None:
            started.append(HyVfdPty(HyVfdProtocol(spindle, cfg.slave), str(cfg.device), lock,
                                    faults).start())
        if cfg.modbus_port is not None:
            started.append(ModbusTcpServer(ModbusMap(spindle, cfg.modbus_map), cfg.modbus_listen,
                                           cfg.modbus_port, lock, faults, cfg.slave).start())
    except OSError:
        for srv in started:
            srv.close()
        raise
    return started
