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
CORE = ROOT / "plant" / "core"

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
