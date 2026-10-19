"""Komponenty HAL linumeRT w prawdziwym HAL LinuxCNC 2.9 (uspace, halrun). Sesja 015.

Model-Author: Claude
Wymaga zbudowanego LinuxCNC RIP (tools/ci/build-linuxcnc.sh, sesja 003): `LINUXCNC_DIR`
albo ~/.cache/linuxcnc-2.9. Marker `linuxcnc` (domyślnie pomijany; `make test-linuxcnc`).
rtapi_app ładuje moduły tylko z katalogu rtlib, więc test kopiuje skompilowany moduł do rtlib
na czas testu i zawsze go usuwa. Nie uruchamiaj równolegle z innym LinuxCNC.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "hal" / "lrt_hardstop_home.comp"

SCRIPT = """\
loadrt threads name1=t period1=1000000
loadrt lrt_hardstop_home
addf lrt-hardstop-home.0 t
setp lrt-hardstop-home.0.threshold 100
setp lrt-hardstop-home.0.detect-time 0.02
setp lrt-hardstop-home.0.value 150
start
loadusr -w sleep 0.05
getp lrt-hardstop-home.0.home-sw
getp lrt-hardstop-home.0.torque-limit
setp lrt-hardstop-home.0.enable 1
loadusr -w sleep 0.005
getp lrt-hardstop-home.0.home-sw
getp lrt-hardstop-home.0.torque-limit
loadusr -w sleep 0.06
getp lrt-hardstop-home.0.home-sw
setp lrt-hardstop-home.0.value -40
loadusr -w sleep 0.01
getp lrt-hardstop-home.0.home-sw
stop
"""


@pytest.fixture
def rip(tmp_path):
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "scripts" / "rip-environment").exists():
        pytest.skip(f"brak LinuxCNC RIP w {root}")
    return root


def _rip(root: Path, command: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null "
                           f"&& {command}"], cwd=cwd, capture_output=True, text=True,
                          timeout=120, check=False)


def test_hardstop_home_comp_in_halrun(rip, tmp_path):  # REQ-VM-07 (c): strona LinuxCNC
    shutil.copy(COMP, tmp_path)
    built = _rip(rip, "halcompile --compile lrt_hardstop_home.comp", tmp_path)
    assert built.returncode == 0, built.stdout + built.stderr
    target = rip / "rtlib" / "lrt_hardstop_home.so"
    assert not target.exists(), f"{target} już istnieje — nie nadpisuję cudzego modułu"
    (tmp_path / "test.hal").write_text(SCRIPT, encoding="utf-8")
    shutil.copy(tmp_path / "lrt_hardstop_home.so", target)
    try:
        run = _rip(rip, "halrun -f test.hal", tmp_path)
    finally:
        target.unlink(missing_ok=True)
        _rip(rip, "halrun -U", tmp_path)
    values = [line.strip() for line in run.stdout.splitlines()
              if line.strip() in {"TRUE", "FALSE"} or line.strip().replace(".", "").isdigit()]
    # poza bazowaniem: brak czujnika, limit normalny; w bazowaniu: limit zredukowany,
    # czujnik dopiero po 20 ms ponad progiem, znika po spadku poniżej progu
    assert values == ["FALSE", "1000", "FALSE", "300", "TRUE", "FALSE"], run.stdout + run.stderr


ESTOP2_SCRIPT = """\
loadrt threads name1=t period1=1000000
loadrt lrt_estop2
addf lrt-estop2.0 t
setp lrt-estop2.0.discrepancy-time 0.05
setp lrt-estop2.0.ch-a 1
setp lrt-estop2.0.ch-b 1
start
loadusr -w sleep 0.02
getp lrt-estop2.0.ok
setp lrt-estop2.0.ch-b 0
loadusr -w sleep 0.1
getp lrt-estop2.0.fault
setp lrt-estop2.0.ch-b 1
setp lrt-estop2.0.reset 1
loadusr -w sleep 0.01
getp lrt-estop2.0.ok
setp lrt-estop2.0.reset 0
setp lrt-estop2.0.ch-a 0
setp lrt-estop2.0.ch-b 0
loadusr -w sleep 0.01
setp lrt-estop2.0.ch-a 1
setp lrt-estop2.0.ch-b 1
loadusr -w sleep 0.01
setp lrt-estop2.0.reset 1
loadusr -w sleep 0.01
getp lrt-estop2.0.ok
stop
"""


def test_estop2_comp_in_halrun(rip, tmp_path):
    """Dwukanałowy E-STOP NC: rozbieżność → błąd; reset bez testu obwodu nieskuteczny."""
    shutil.copy(ROOT / "hal" / "lrt_estop2.comp", tmp_path)
    built = _rip(rip, "halcompile --compile lrt_estop2.comp", tmp_path)
    assert built.returncode == 0, built.stdout + built.stderr
    target = rip / "rtlib" / "lrt_estop2.so"
    assert not target.exists(), f"{target} już istnieje — nie nadpisuję cudzego modułu"
    (tmp_path / "test.hal").write_text(ESTOP2_SCRIPT, encoding="utf-8")
    shutil.copy(tmp_path / "lrt_estop2.so", target)
    try:
        run = _rip(rip, "halrun -f test.hal", tmp_path)
    finally:
        target.unlink(missing_ok=True)
        _rip(rip, "halrun -U", tmp_path)
    values = [line.strip() for line in run.stdout.splitlines()
              if line.strip() in {"TRUE", "FALSE"}]
    assert values == ["TRUE", "TRUE", "FALSE", "TRUE"], run.stdout + run.stderr
