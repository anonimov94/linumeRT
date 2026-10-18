"""Wspólne narzędzia testów z LinuxCNC RIP i komponentami HAL linumeRT (sesje 017–018).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 018.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAL = ROOT / "hal"


def rip_root() -> Path:
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "scripts" / "rip-environment").exists():
        pytest.skip(f"brak LinuxCNC RIP w {root}")
    return root


def rip_run(root: Path, command: str, cwd: Path, timeout: float = 120,
            env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null "
                           f"&& {command}"], cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, check=False, env=env)


@contextlib.contextmanager
def installed_modules(root: Path, work: Path, comps: tuple[str, ...]) -> Iterator[None]:
    """Kompiluje komponenty z hal/ i kopiuje do rtlib RIP na czas bloku (stare przywraca)."""
    for f in HAL.glob("*.h"):
        shutil.copy(f, work)
    backups: list[tuple[Path, Path | None]] = []
    try:
        for comp in comps:
            shutil.copy(HAL / f"{comp}.comp", work)
            built = rip_run(root, f"halcompile --compile {comp}.comp", work)
            assert built.returncode == 0, built.stdout + built.stderr
            assert "warning" not in built.stderr.lower(), built.stderr
            target = root / "rtlib" / f"{comp}.so"
            backup = None
            if target.exists():
                backup = work / f"{comp}.so.orig"
                shutil.copy(target, backup)
            shutil.copy(work / f"{comp}.so", target)
            backups.append((target, backup))
        yield
    finally:
        for target, backup in backups:
            if backup is not None:
                shutil.copy(backup, target)
            else:
                target.unlink(missing_ok=True)
        rip_run(root, "halrun -U", work)


@contextlib.contextmanager
def plant_server(machine_or_plant: Path, port: int, *extra: str) -> Iterator[subprocess.Popen]:
    """Serwer Plant (lockstep) na localhost; gotowy, gdy port UDP jest zajęty."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(ROOT / "core"), str(ROOT / "plant" / "server"), os.environ.get("PYTHONPATH", "")])}
    target = (["--plant", str(machine_or_plant)] if machine_or_plant.name == "plant.yaml"
              else [str(machine_or_plant)])
    proc = subprocess.Popen([sys.executable, "-m", "linumert_plant", "serve", *target,
                             "--lockstep", "--port", str(port), *extra], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                break
            finally:
                probe.close()
            if proc.poll() is not None:
                pytest.fail(proc.stdout.read())
            time.sleep(0.1)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
