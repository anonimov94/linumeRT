"""Łącze VM-A ↔ VM-B bez VirtualBoxa (sesja 025, docs/VM.md §5–6).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 025.

- Plant w trybie `--realtime` i `tools/vm/lrtnet_probe.py` jak dwie VM na localhost; opóźnienie
  i rozrzut sieci daje przekaźnik UDP (zamiast `tc netem`, które wymaga modułu jądra).
- Zawieszenie VM-A dłuższe niż `watchdog_ms` → watchdog E-4003 (REQ-QA-03).
- Most falownika: polecenia `socat` wzięte wprost z plików usług w post-install-*.sh
  (pty Plant ↔ TCP ↔ pty dla hy_vfd), ramka hy_vfd przechodzi tam i z powrotem.
Porty z zakresu sesji 025 (47830–47839) albo wybrane przez system.
"""

from __future__ import annotations

import os
import random
import re
import select
import shutil
import socket
import subprocess
import sys
import threading
import time
import tty
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VM = ROOT / "tools" / "vm"
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"
sys.path.insert(0, str(VM))

import lrtnet_probe  # noqa: E402


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(f"rdzeń C niedostępny: {exc}")
    return core_binding


@pytest.fixture
def plant(core):
    """Serwer Plant w trybie realtime (jak usługa linumert-plant w VM-B) na wolnym porcie."""
    from linumert_plant.build_machine import build_machine
    from linumert_plant.server import PlantConfig, PlantServer

    server = PlantServer(core.PlantMachine(build_machine(MACHINE, seed=1)),
                         PlantConfig(mode="realtime", watchdog_ms=50.0, seed=1))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve, args=(sock,), daemon=True)
    thread.start()
    yield server, sock.getsockname()[1]
    server.stop()
    thread.join(timeout=5)
    sock.close()


class Relay:
    """Przekaźnik UDP z opóźnieniem `delay_ms` ± `jitter_ms` w obie strony (sieć między VM)."""

    def __init__(self, target_port: int, delay_ms: float, jitter_ms: float, seed: int = 1):
        self.target = ("127.0.0.1", target_port)
        self.delay, self.jitter = delay_ms / 1000.0, jitter_ms / 1000.0
        self.rng = random.Random(seed)
        self.front = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.front.bind(("127.0.0.1", 0))
        self.back = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.back.connect(self.target)
        self.port = self.front.getsockname()[1]
        self.client = None
        self.queue: list[tuple[float, socket.socket, bytes, object]] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _due(self) -> float:
        return time.monotonic() + max(0.0, self.delay + self.rng.uniform(-self.jitter, self.jitter))

    def _run(self) -> None:
        while not self.stop.is_set():
            ready, _, _ = select.select([self.front, self.back], [], [], 0.0005)
            for s in ready:
                data, addr = s.recvfrom(2048)
                if s is self.front:
                    self.client = addr
                    self.queue.append((self._due(), self.back, data, None))
                elif self.client is not None:
                    self.queue.append((self._due(), self.front, data, self.client))
            now = time.monotonic()
            # Kolejność dostarczenia według czasu (rozrzut może zmienić kolejność, jak w sieci).
            self.queue.sort(key=lambda item: item[0])
            while self.queue and self.queue[0][0] <= now:
                _due, out, data, to = self.queue.pop(0)
                if to is None:
                    out.send(data)
                else:
                    out.sendto(data, to)

    def close(self) -> None:
        self.stop.set()
        self.thread.join(timeout=2)
        self.front.close()
        self.back.close()


def test_realtime_link_direct(plant) -> None:  # REQ-QA-03
    server, port = plant
    r = lrtnet_probe.probe("127.0.0.1", port, frames=2500, cycle_ms=1.0)
    assert lrtnet_probe.verdict(r) == 0, r
    assert r["enabled_at_frame"] is not None  # sekwencja CiA 402 przez łącze
    assert r["missing"] == 0 and r["rejected"] == 0 and not r["watchdog"]
    assert server.stats.received == 2500 and server.stats.rejected == 0
    assert not server.watchdog_tripped


def test_realtime_link_with_network_delay_and_jitter(plant) -> None:  # REQ-QA-03
    # 5 ms ± 2 ms w każdą stronę: dłużej niż cykl 1 ms, ale przerwy między ramkami < watchdog 50 ms.
    server, port = plant
    relay = Relay(port, delay_ms=5.0, jitter_ms=2.0)
    try:
        r = lrtnet_probe.probe("127.0.0.1", relay.port, frames=1500, cycle_ms=1.0, drain_s=0.3)
    finally:
        relay.close()
    assert not r["watchdog"] and not server.watchdog_tripped
    assert lrtnet_probe.verdict(r) == 0, r
    assert 6.0 <= r["rtt_ms"]["p50"] <= 30.0  # ok. 2 × 5 ms + obsługa w Pythonie
    # Rozrzut zmienia kolejność ramek: Plant liczy je jako spóźnione, nie przerywa pracy.
    assert server.stats.rejected == 0


def test_stalled_master_trips_watchdog(plant) -> None:  # REQ-QA-03
    # Zawieszenie VM-A (np. przełączenie hosta) na 120 ms > watchdog_ms 50 → E-4003 w odpowiedziach.
    server, port = plant
    # Napędy szablonów startują do 2 s (boot_time_s), więc przerwa dopiero po ich włączeniu.
    r = lrtnet_probe.probe("127.0.0.1", port, frames=3000, cycle_ms=1.0,
                           stall_at=2700, stall_ms=120)
    assert r["enabled_at_frame"] is not None and r["enabled_at_frame"] < 2700
    assert server.watchdog_tripped
    assert r["watchdog"] and lrtnet_probe.verdict(r) == 1


def test_probe_without_plant_reports_no_reply() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()  # nikt nie słucha
    r = lrtnet_probe.probe("127.0.0.1", port, frames=50, cycle_ms=1.0, drain_s=0.1)
    assert r["replies"] == 0 and lrtnet_probe.verdict(r) == 2


# ---- most falownika (socat) -------------------------------------------------------------------

def _exec_start(script: str, unit: str) -> str:
    """Linia ExecStart= usługi `unit` z heredoc w skrypcie (polecenie 1:1 jak w VM)."""
    text = (VM / script).read_text(encoding="utf-8")
    block = text[text.index(f"/etc/systemd/system/{unit}"):]
    return re.search(r"^ExecStart=(.+)$", block, re.M).group(1)


def _expand(cmd: str, env: dict[str, str]) -> list[str]:
    for key, value in env.items():
        cmd = cmd.replace(f"${key}", value)
    assert "$" not in cmd, cmd
    return cmd.split()


def _free_tcp_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(path: Path, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while not path.exists():
        assert time.monotonic() < end, f"brak {path}"
        time.sleep(0.05)


@pytest.mark.skipif(shutil.which("socat") is None, reason="brak socat")
def test_vfd_bridge_commands_carry_hy_vfd_frames(tmp_path) -> None:  # REQ-VD-01
    from linumert_plant.vfd import HyVfdProtocol, HyVfdPty, VfdFaults, seal

    plant_pty, ctl_pty = tmp_path / "plant_hy_vfd", tmp_path / "ctl_hy_vfd"
    port = str(_free_tcp_port())
    socat = shutil.which("socat")
    vm_b = _expand(_exec_start("post-install-plant.sh", "linumert-vfd-bridge.service"),
                   {"VFD_BRIDGE_PORT": port, "LRTNET_PLANT_IP": "127.0.0.1",
                    "VFD_DEVICE": str(plant_pty)})
    vm_a = _expand(_exec_start("post-install-ctl.sh", "linumert-vfd-link.service"),
                   {"VFD_BRIDGE_PORT": port, "LRTNET_PLANT_IP": "127.0.0.1",
                    "VFD_DEVICE": str(ctl_pty)})
    assert vm_b[0] == vm_a[0] == "/usr/bin/socat"
    pty = HyVfdPty(HyVfdProtocol(_hy_spindle()), str(plant_pty), threading.Lock(),
                   VfdFaults()).start()
    procs = [subprocess.Popen([socat, *vm_b[1:]])]
    try:
        time.sleep(0.3)  # TCP-LISTEN gotowy
        procs.append(subprocess.Popen([socat, *vm_a[1:]]))
        _wait_for(ctl_pty)
        fd = os.open(ctl_pty, os.O_RDWR | os.O_NOCTTY)
        try:
            tty.setraw(fd)
            # Funkcja 0x05 (częstotliwość zadana 50,00 Hz), jak hy_comm.c; odpowiedź = echo danych.
            os.write(fd, seal(bytes([1, 0x05, 2, 0x13, 0x88])))
            data, end = b"", time.monotonic() + 3.0
            while len(data) < 7 and time.monotonic() < end:
                ready, _, _ = select.select([fd], [], [], 0.2)
                if ready:
                    data += os.read(fd, 7 - len(data))
        finally:
            os.close(fd)
        assert data == seal(bytes([1, 0x05, 2, 0x13, 0x88]))
    finally:
        for proc in reversed(procs):
            proc.terminate()
            proc.wait(timeout=5)
        pty.close()


def _hy_spindle():
    from linumert_plant.drive_library import load_library
    from linumert_plant.vfd import SpindleModel

    tpl = load_library()["spindle_vfd_22kw"]

    class Cfg:
        class spindle:  # noqa: N801 — atrapa MachineConfig.spindle
            max_rpm, min_rpm, ramp_up_s, ramp_down_s = 24000.0, 6000.0, 2.0, 2.0

    return SpindleModel.from_machine(Cfg, tpl)


def test_master_restart_with_running_plant(plant) -> None:  # REQ-QA-03
    # VM-B: usługa linumert-plant działa stale, LinuxCNC w VM-A startuje ponownie z seq = 1
    # (lrt_net.comp: frame_seq = 1). Po przerwie > watchdog_ms Plant przyjmuje nową numerację.
    server, port = plant
    first = lrtnet_probe.probe("127.0.0.1", port, frames=2500, cycle_ms=1.0)
    assert first["enabled_at_frame"] is not None
    time.sleep(0.2)
    late_before = server.stats.late
    second = lrtnet_probe.probe("127.0.0.1", port, frames=2500, cycle_ms=1.0)
    assert second["enabled_at_frame"] is not None, second
    assert server.stats.late - late_before == 0
