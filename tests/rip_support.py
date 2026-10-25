"""Wspólne narzędzia testów z LinuxCNC RIP i komponentami HAL linumeRT (sesje 017–018).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 018.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
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


# Procesy LinuxCNC/HAL, które po przerwanym zamknięciu blokują kolejny start (sesja 008).
LEFTOVERS = ("linuxcnc", "linuxcncsvr", "milltask", "io", "iov2", "halui", "hy_vfd", "rtapi_app")
LOCK_FILE = Path("/tmp/linuxcnc.lock")


def _source(root: Path | None) -> str:
    return f"source '{root}/scripts/rip-environment' >/dev/null; " if root else ""


def leftovers() -> list[str]:
    """Procesy LinuxCNC/HAL bieżącego użytkownika, które jeszcze żyją (`nazwa:pid`)."""
    found = subprocess.run(["pgrep", "-u", str(os.getuid()), "-l", "-x", "|".join(LEFTOVERS)],
                           capture_output=True, text=True, check=False).stdout
    return [":".join(line.split()[::-1]) for line in found.splitlines()
            if line.strip() and not _zombie(line.split()[0])]


def _zombie(pid: str) -> bool:
    """Proces zakończony, czekający na odebranie przez rodzica (stan Z). W kontenerze CI bez
    procesu init zombie nie znikają, a nic już nie blokują (sesja 024)."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return True  # już nie istnieje
    return stat.rsplit(")", 1)[-1].split()[0] == "Z"


def cleanup_linuxcnc(root: Path | None = None, cwd: Path | None = None) -> None:
    """Sprzątanie po LinuxCNC: `halrun -U`, zabicie pozostałych procesów, plik blokady.

    Bezpieczne do wywołania zawsze; gdy nic nie zostało, nie robi nic.
    """
    if not leftovers() and not LOCK_FILE.exists():
        return
    names = "|".join(LEFTOVERS)
    subprocess.run(["bash", "-c", f"{_source(root)}halrun -U >/dev/null 2>&1; "
                    f"pkill -KILL -u $(id -u) -x '{names}'; true"],
                   cwd=cwd, capture_output=True, text=True, timeout=60, check=False)
    deadline = time.monotonic() + 10
    while leftovers() and time.monotonic() < deadline:
        time.sleep(0.1)
    LOCK_FILE.unlink(missing_ok=True)
    left = leftovers()
    assert not left, f"po sprzątaniu LinuxCNC zostały procesy: {left}"


def start_linuxcnc(root: Path, ini: Path, env: dict | None = None, *,
                   console: bool = False) -> subprocess.Popen:
    """`linuxcnc <ini>` z RIP we własnej grupie procesów (zatrzymanie: `stop_linuxcnc`)."""
    cleanup_linuxcnc(root, ini.parent)  # resztki poprzedniego testu blokują start
    flags = "-r " if console else ""
    return subprocess.Popen(["bash", "-c", f"{_source(root)}exec linuxcnc {flags}'{ini}'"],
                            cwd=ini.parent, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)


def stop_linuxcnc(proc: subprocess.Popen, root: Path | None = None, cwd: Path | None = None,
                  timeout: float = 60) -> None:
    """Zamyka LinuxCNC uruchomiony w osobnej grupie procesów i sprząta resztki.

    SIGTERM idzie do całej grupy: sam skrypt `linuxcnc` czeka na proces ekranu (zastępczy
    `sleep`) i do jego końca nie obsłuży sygnału, więc samo `terminate()` kończyło się po
    limicie czasu `kill()` bez `Cleanup` i zostawiało `linuxcncsvr`/`milltask`/`rtapi_app`.
    """
    if proc.poll() is None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=10)
    cleanup_linuxcnc(root, cwd)


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
