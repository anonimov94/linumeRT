"""lrt_net + lrt_cia402 w prawdziwym HAL LinuxCNC 2.9 z serwerem Plant na localhost (sesja 017).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 017.
Wymaga LinuxCNC RIP (tools/ci/build-linuxcnc.sh): `LINUXCNC_DIR` albo ~/.cache/linuxcnc-2.9,
oraz rdzenia Plant (`make -C plant/core shared`). Marker `linuxcnc`. Moduły trafiają do rtlib
RIP tylko na czas testu. Nie uruchamiaj równolegle z innym LinuxCNC ani serwerem Plant.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
HAL = ROOT / "hal"
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
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "scripts" / "rip-environment").exists():
        pytest.skip(f"brak LinuxCNC RIP w {root}")
    return root


def _rip(root: Path, command: str, cwd: Path, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null "
                           f"&& {command}"], cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, check=False)


@pytest.fixture
def modules(rip, tmp_path):
    """Kompiluje lrt_net i lrt_cia402, kopiuje do rtlib na czas testu."""
    for name in ("lrt_net.comp", "lrt_net_proto.h", "lrt_cia402.comp"):
        shutil.copy(HAL / name, tmp_path)
    installed = []
    try:
        for comp in ("lrt_net", "lrt_cia402"):
            built = _rip(rip, f"halcompile --compile {comp}.comp", tmp_path)
            assert built.returncode == 0, built.stdout + built.stderr
            assert "warning" not in built.stderr.lower(), built.stderr
            target = rip / "rtlib" / f"{comp}.so"
            assert not target.exists(), f"{target} już istnieje — nie nadpisuję cudzego modułu"
            shutil.copy(tmp_path / f"{comp}.so", target)
            installed.append(target)
        yield tmp_path
    finally:
        for target in installed:
            target.unlink(missing_ok=True)
        _rip(rip, "halrun -U", tmp_path)


@pytest.fixture
def plant_server():
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(ROOT / "core"), str(ROOT / "plant" / "server"), os.environ.get("PYTHONPATH", "")])}
    proc = subprocess.Popen([sys.executable, "-m", "linumert_plant", "serve", str(MACHINE),
                             "--lockstep", "--port", str(PORT)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:  # gotowość: port UDP zajęty
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.bind(("127.0.0.1", PORT))
        except OSError:
            break
        finally:
            probe.close()
        if proc.poll() is not None:
            pytest.fail(proc.stdout.read())
        time.sleep(0.1)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _values(out: str) -> list[str]:
    return [line.strip() for line in out.splitlines()
            if line.strip() in {"TRUE", "FALSE"}
            or line.strip().lstrip("-").replace(".", "", 1).isdigit()]


def test_lrt_net_enables_drives_and_moves_axis(rip, modules, plant_server):  # REQ-VM-02
    (modules / "test.hal").write_text(_script(), encoding="utf-8")
    run = _rip(rip, "halrun -f test.hal", modules)
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
    run = _rip(rip, "halrun -f test.hal", modules)
    assert _values(run.stdout) == ["FALSE"], run.stdout + run.stderr
