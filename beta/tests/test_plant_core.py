"""Testy rdzenia C Plant (plant/core): uruchamia `make -C plant/core test` i pilnuje zasad RT.

Model-Author: Claude
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plant_core"

HAS_TOOLCHAIN = shutil.which("make") is not None and (
    shutil.which("cc") is not None or shutil.which("gcc") is not None
)

# Wywolania niedozwolone w rdzeniu (CLAUDE.md §5: bez alokacji i I/O po inicjalizacji).
FORBIDDEN_CALLS = re.compile(
    r"\b(malloc|calloc|realloc|free|printf|fprintf|puts|fopen|fwrite|fread|socket|sleep)\s*\("
)


def _core_sources() -> list[Path]:
    return sorted(p for p in CORE.glob("*.[ch]"))


def test_core_sources_exist_with_license_header() -> None:
    sources = _core_sources()
    assert [p.name for p in sources if p.suffix == ".c"], "brak plikow .c w plant/core"
    for path in sources:
        head = path.read_text(encoding="utf-8")[:200]
        assert "SPDX-License-Identifier: GPL-2.0-or-later" in head, path.name


def test_core_has_no_alloc_or_io_calls() -> None:
    for path in _core_sources():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            code = line.split("/*", 1)[0].split("//", 1)[0]
            assert not FORBIDDEN_CALLS.search(code), f"{path.name}:{number}: {line.strip()}"


@pytest.mark.skipif(not HAS_TOOLCHAIN, reason="brak make i kompilatora C")
def test_c_unit_tests_pass() -> None:
    result = subprocess.run(
        ["make", "-C", str(CORE), "test"],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    passed = re.findall(r"^ok \d+ - ", result.stdout, flags=re.MULTILINE)
    failed = re.findall(r"^not ok ", result.stdout, flags=re.MULTILINE)
    assert not failed, result.stdout
    assert len(passed) >= 10, result.stdout  # kryterium sesji 011: >= 10 testow C


@pytest.mark.skipif(not HAS_TOOLCHAIN, reason="brak make i kompilatora C")
def test_make_test_c_target_runs_core_tests() -> None:
    result = subprocess.run(
        ["make", "-s", "test-c"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# testy:" in result.stdout


# ---- Napęd (drive.h): awarie ↔ katalog alarmów (sesja 012) -------------------------------

DRIVE_FAULT_ROW = re.compile(
    r'X\(\s*([A-Z_]+)\s*,\s*(\d+)\s*,\s*(0x[0-9A-Fa-f]+)\s*,\s*"(E-4[02]\d\d)"\s*\)'
)


def _drive_fault_rows() -> list[tuple[str, int, int, str]]:
    text = (CORE / "drive.h").read_text(encoding="utf-8")
    return [
        (name, int(num), int(cia, 16), alarm)
        for name, num, cia, alarm in DRIVE_FAULT_ROW.findall(text)
    ]


def test_drive_fault_table_is_consistent() -> None:
    rows = _drive_fault_rows()
    assert len(rows) >= 9, rows
    assert [r[1] for r in rows] == list(range(1, len(rows) + 1))  # numery ciągłe od 1
    assert len({r[2] for r in rows}) == len(rows), "powtórzony kod 603Fh"
    assert len({r[3] for r in rows}) == len(rows), "powtórzony alarm"


def test_every_drive_fault_has_alarm_in_catalog() -> None:  # kryterium sesji 012
    # W bliźniaku pakiet leży w src/ (upstream miał core/linumert) — katalog jest
    # częścią tego drzewa, więc jego brak to błąd, nie powód do pominięcia testu.
    catalog = ROOT / "src" / "linumert" / "alarms" / "catalog.yaml"
    assert catalog.exists(), f"brak katalogu alarmów pod {catalog}"
    codes = set(re.findall(r"^- code: (E-4[02]\d\d)\s*$", catalog.read_text("utf-8"), flags=re.M))
    for name, _num, _cia, alarm in _drive_fault_rows():
        assert alarm in codes, f"awaria {name}: brak {alarm} w catalog.yaml"
