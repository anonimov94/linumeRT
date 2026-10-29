"""Klient testowy LRT-NET udający LinuxCNC (master): CiA 402 i profil trapezowy po UDP.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 016.

Lockstep: master wysyła ramkę i czeka na odpowiedź (jak wątek servo z hm2_eth, ale bez
zegara czasu rzeczywistego); `time_ns` rośnie o `cycle_ns` na ramkę.
Uruchomienie z serwerem na localhost:
    python -m linumert_plant serve config/machines/mill_servo_table.yaml --lockstep &
    python plant/server/test_master.py --axes 4 --move 0 --distance 50000
Nie jest testem pytest (testpaths = tests); testy używają klasy `Master`.
"""

from __future__ import annotations

import argparse
import math
import socket
import sys
from collections.abc import Callable

from linumert_plant.lrtnet import (
    PORT,
    AxisCommand,
    Command,
    FrameError,
    Reply,
    decode_reply,
    encode_command,
)

CW_SHUTDOWN, CW_SWITCH_ON, CW_ENABLE, CW_FAULT_RESET = 0x0006, 0x0007, 0x000F, 0x0080
MODE_CSP = 8


def drive_state(sw: int) -> str:
    """Stan CiA 402 ze słowa stanu (maski 0x4F / 0x6F)."""
    if sw & 0x4F == 0x08 or sw & 0x4F == 0x0F:
        return "FAULT"
    if sw & 0x4F == 0x40:
        return "SWITCH_ON_DISABLED"
    return {0x21: "READY_TO_SWITCH_ON", 0x23: "SWITCHED_ON", 0x27: "OPERATION_ENABLED",
            0x07: "QUICK_STOP_ACTIVE"}.get(sw & 0x6F, "NOT_READY")


def trapezoid(distance: float, vmax: float, amax: float, dt: float) -> list[float]:
    """Przyrosty położenia od startu dla każdego cyklu (profil trapezowy albo trójkątny)."""
    if distance == 0:
        return []
    sign = 1.0 if distance > 0 else -1.0
    dist = abs(distance)
    t_acc = vmax / amax
    if amax * t_acc * t_acc > dist:  # trójkąt
        t_acc = math.sqrt(dist / amax)
        vmax = amax * t_acc
    t_flat = (dist - amax * t_acc * t_acc) / vmax
    total = 2 * t_acc + t_flat
    out = []
    n = max(1, math.ceil(total / dt))
    for i in range(1, n + 1):
        t = min(i * dt, total)
        if t < t_acc:
            s = 0.5 * amax * t * t
        elif t < t_acc + t_flat:
            s = 0.5 * amax * t_acc * t_acc + vmax * (t - t_acc)
        else:
            r = total - t
            s = dist - 0.5 * amax * r * r
        out.append(sign * s)
    return out


class MasterError(RuntimeError):
    pass


class Master:
    """Master LRT-NET w trybie lockstep (jedna ramka w locie)."""

    def __init__(self, n_axes: int, host: str = "127.0.0.1", port: int = PORT,
                 cycle_ns: int = 1_000_000, timeout: float = 1.0, seq: int = 1,
                 time_ns: int = 0, transport: Callable[[bytes], bytes | None] | None = None):
        """`transport` zamiast UDP: funkcja ramka → odpowiedź (np. `PlantServer.handle`)."""
        self.addr = (host, port)
        self.cycle_ns = cycle_ns
        self.seq = seq
        self.time_ns = time_ns
        self.axes = [AxisCommand(controlword=0, mode=MODE_CSP, target_pos=0)
                     for _ in range(n_axes)]
        self.digital_out = 0
        self.spindle_cmd = 0.0  # [obr/min], znak = kierunek
        self.timeouts = 0
        self.last: Reply | None = None
        self.transport = transport
        self.sock = None
        if transport is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(timeout)

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()

    def exchange(self, flags: int = 0, advance_ns: int | None = None) -> Reply:
        """Wysyła jedną ramkę i czeka na odpowiedź z tym samym `seq`."""
        cmd = Command(seq=self.seq, time_ns=self.time_ns, axes=self.axes,
                      digital_out=self.digital_out, spindle_cmd=self.spindle_cmd,
                      flags=flags)
        frame = encode_command(cmd)
        if self.transport is not None:
            data = self.transport(frame)
            if data is None:
                raise MasterError(f"ramka {self.seq} odrzucona przez Plant")
            return self._accept(decode_reply(data), advance_ns)
        self.sock.sendto(frame, self.addr)
        while True:
            try:
                data, _ = self.sock.recvfrom(2048)
            except TimeoutError:
                self.timeouts += 1
                raise MasterError(f"brak odpowiedzi na ramkę {self.seq}") from None
            try:
                reply = decode_reply(data)
            except FrameError as exc:
                raise MasterError(f"zła odpowiedź: {exc}") from None
            if reply.seq == cmd.seq:
                return self._accept(reply, advance_ns)

    def _accept(self, reply: Reply, advance_ns: int | None) -> Reply:
        self.seq = (self.seq + 1) & 0xFFFFFFFF
        self.time_ns += self.cycle_ns if advance_ns is None else advance_ns
        self.last = reply
        return reply

    def states(self) -> list[str]:
        return [drive_state(a.statusword) for a in self.last.axes] if self.last else []

    def hold(self) -> None:
        """Pozycja zadana = rzeczywista (przed włączeniem, jak LinuxCNC przy enable)."""
        if self.last is not None:
            for cmd, rep in zip(self.axes, self.last.axes, strict=True):
                cmd.target_pos = rep.actual_pos

    def enable(self, max_cycles: int = 5000) -> int:
        """Sekwencja CiA 402 dla wszystkich osi (z kasowaniem faultu). Zwraca liczbę cykli."""
        if self.last is None:
            self.exchange()
        for cycle in range(max_cycles):
            states = self.states()
            if all(s == "OPERATION_ENABLED" for s in states):
                return cycle
            self.hold()
            for cmd, state in zip(self.axes, states, strict=True):
                if state == "FAULT":
                    cmd.controlword = 0 if cmd.controlword == CW_FAULT_RESET else CW_FAULT_RESET
                elif state in ("SWITCH_ON_DISABLED", "NOT_READY"):
                    cmd.controlword = CW_SHUTDOWN
                elif state == "READY_TO_SWITCH_ON":
                    cmd.controlword = CW_SWITCH_ON
                elif state in ("SWITCHED_ON", "OPERATION_ENABLED"):
                    cmd.controlword = CW_ENABLE
            self.exchange()
        raise MasterError(f"napędy nie włączone po {max_cycles} cyklach: {self.states()}")

    def move(self, axis: int, distance: int, vmax: float, amax: float) -> int:
        """Ruch osi profilem trapezowym [impulsy, impulsy/s, impulsy/s²]; zwraca liczbę ramek."""
        start = self.axes[axis].target_pos
        profile = trapezoid(distance, vmax, amax, self.cycle_ns / 1e9)
        for ds in profile:
            self.axes[axis].target_pos = start + round(ds)
            self.exchange()
        return len(profile)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Master testowy LRT-NET (lockstep)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--axes", type=int, required=True, help="liczba osi (napędów) maszyny")
    p.add_argument("--move", type=int, default=0, help="indeks osi do ruchu")
    p.add_argument("--distance", type=int, default=10000, help="droga [impulsy]")
    p.add_argument("--vmax", type=float, default=100000.0, help="[impulsy/s]")
    p.add_argument("--amax", type=float, default=1000000.0, help="[impulsy/s²]")
    args = p.parse_args(argv)
    master = Master(args.axes, args.host, args.port)
    try:
        cycles = master.enable()
        frames = master.move(args.move, args.distance, args.vmax, args.amax)
        for _ in range(200):
            master.exchange()
    except MasterError as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1
    finally:
        master.close()
    rep = master.last
    axis = rep.axes[args.move]
    print(f"włączenie: {cycles} cykli, ruch: {frames} ramek; oś {args.move}: "
          f"pozycja {axis.actual_pos}, błąd nadążania {axis.following_error}, "
          f"utracone {rep.frames_lost}, spóźnione {rep.frames_late}, jitter {rep.jitter_us} µs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
