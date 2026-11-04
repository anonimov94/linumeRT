"""lrt_net + lrt_cia402 w prawdziwym HAL LinuxCNC 2.9 z serwerem Plant na localhost (sesja 017).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 017.
Wymaga LinuxCNC RIP (tools/ci/build-linuxcnc.sh): `LINUXCNC_DIR` albo ~/.cache/linuxcnc-2.9,
oraz rdzenia Plant (`make -C plant/core shared`). Marker `linuxcnc`. Moduły trafiają do rtlib
RIP tylko na czas testu. Nie uruchamiaj równolegle z innym LinuxCNC ani serwerem Plant.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest
from rip_support import installed_modules, plant_server, rip_root, rip_run

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"
AXES = 4  # napędy mill_servo_table bez wrzeciona
PORT = 47791
SCALE = 13107.195  # impulsy/mm napędów mill_servo_table (MachineModel.counts_per_unit)


def _script(enable: bool = True) -> str:
    lines = [
        "loadrt threads name1=servo period1=1000000",
        f"loadrt lrt_net personality={AXES} ip=127.0.0.1 port={PORT}",
        f"loadrt lrt_cia402 count={AXES}",
        "loadrt limit3 count=1",
        "addf lrt-net.0 servo",
    ]
    for i in range(AXES):
        lines += [
            f"addf lrt-cia402.{i} servo",
            f"net cw{i} lrt-cia402.{i}.controlword => lrt-net.0.axis.{i}.controlword",
            f"net sw{i} lrt-net.0.axis.{i}.statusword => lrt-cia402.{i}.statusword",
            f"net md{i} lrt-net.0.axis.{i}.mode-display => lrt-cia402.{i}.mode-display",
            f"net mo{i} lrt-cia402.{i}.mode => lrt-net.0.axis.{i}.mode",
            f"setp lrt-net.0.axis.{i}.scale {SCALE}",
        ]
    lines += [
        "addf limit3.0 servo",
        "setp limit3.0.maxv 20",
        "setp limit3.0.maxa 200",
        "net x-cmd limit3.0.out => lrt-net.0.axis.0.pos-cmd",
        "start",
        "loadusr -w sleep 0.3",
        "getp lrt-net.0.connected",
    ]
    if enable:
        lines += [f"setp lrt-cia402.{i}.enable 1" for i in range(AXES)]
        lines += ["loadusr -w sleep 2.0"]
        lines += [f"getp lrt-cia402.{i}.enabled" for i in range(AXES)]
        lines += [
            "setp limit3.0.in 2.0",
            "loadusr -w sleep 1.0",
            "getp lrt-net.0.axis.0.pos-fb",
            "getp lrt-net.0.plant-lost",
            "getp lrt-net.0.bad-frames",
            "getp lrt-net.0.reply-age",
            "getp lrt-cia402.0.fault",
        ]
    lines += ["stop"]
    return "\n".join(lines) + "\n"


@pytest.fixture
def rip():
    return rip_root()


@pytest.fixture
def modules(rip, tmp_path):
    with installed_modules(rip, tmp_path, ("lrt_net", "lrt_cia402")):
        yield tmp_path


@pytest.fixture
def plant():
    with plant_server(MACHINE, PORT) as proc:
        yield proc


def _values(out: str) -> list[str]:
    return [line.strip() for line in out.splitlines()
            if line.strip() in {"TRUE", "FALSE"}
            or line.strip().lstrip("-").replace(".", "", 1).isdigit()]


def test_lrt_net_enables_drives_and_moves_axis(rip, modules, plant):  # REQ-VM-02
    (modules / "test.hal").write_text(_script(), encoding="utf-8")
    run = rip_run(rip, "halrun -f test.hal", modules)
    vals = _values(run.stdout)
    assert len(vals) == 1 + AXES + 5, run.stdout + run.stderr
    connected, enabled = vals[0], vals[1:1 + AXES]
    pos, lost, bad, age, fault = vals[1 + AXES:]
    assert connected == "TRUE"
    assert enabled == ["TRUE"] * AXES  # sekwencja CiA 402 przez UDP
    assert float(pos) == pytest.approx(2.0, abs=0.01)  # oś X dojechała rampą limit3
    assert (lost, bad, fault) == ("0", "0", "FALSE")
    assert int(age) in (1, 2)  # odpowiedź z poprzedniego cyklu


def test_lrt_net_without_plant_is_disconnected(rip, modules):
    (modules / "test.hal").write_text(_script(enable=False), encoding="utf-8")
    run = rip_run(rip, "halrun -f test.hal", modules)
    assert _values(run.stdout) == ["FALSE"], run.stdout + run.stderr


# Zatrzask (estop_latch) pamięta każde opadnięcie `connected` po starcie.
LINK_LATCH = f"""loadrt threads name1=servo period1=1000000
loadrt lrt_net personality={AXES} ip=127.0.0.1 port={PORT}
loadrt estop_latch names=link
addf lrt-net.0 servo
addf link servo
net up lrt-net.0.connected => link.ok-in
start
loadusr -w sleep 0.5
setp link.reset 1
loadusr -w sleep 0.05
setp link.reset 0
loadusr -w sleep 2.5
getp link.fault-out
stop
"""
STALL = 0.06  # [s] wstrzymanie procesu: 60 okresów, 3× próg 20 ms


def _link_dropped(rip, work: Path, pid_of_victim) -> str:
    """Uruchamia LINK_LATCH, w trakcie wstrzymuje proces na STALL; zwraca link.fault-out."""
    (work / "link.hal").write_text(LINK_LATCH, encoding="utf-8")
    run = subprocess.Popen(["bash", "-c", f"source '{rip}/scripts/rip-environment' >/dev/null "
                            "&& halrun -f link.hal"], cwd=work, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
    time.sleep(1.5)                                   # po resecie zatrzasku, łącze zestawione
    pid = pid_of_victim()
    os.kill(pid, signal.SIGSTOP)
    time.sleep(STALL)
    os.kill(pid, signal.SIGCONT)
    out, _ = run.communicate(timeout=60)
    vals = _values(out)
    assert len(vals) == 1, out
    return vals[0]


def _rtapi_app() -> int:
    pids = subprocess.run(["pgrep", "-x", "rtapi_app"], capture_output=True,
                          text=True).stdout.split()
    assert len(pids) == 1, f"oczekiwany jeden rtapi_app, są: {pids}"
    return int(pids[0])


# REQ-QA-03
def test_master_stall_does_not_drop_link(rip, modules, plant):
    # uspace bez RT: po wstrzymaniu wątku servo zaległe cykle idą serią bez przerw; Plant nie
    # zdąży odpowiedzieć na ramki co kilka µs, ale nie milczał (2026-11-03, sondowanie z Plant).
    assert _link_dropped(rip, modules, _rtapi_app) == "FALSE"


# REQ-QA-03
def test_plant_stall_drops_link(rip, modules, plant):
    # Ten sam próg dla prawdziwej ciszy Plant: 60 ms bez odpowiedzi → connected = 0.
    assert _link_dropped(rip, modules, lambda: plant.pid) == "TRUE"
