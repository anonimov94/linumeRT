"""Programy .ngc z kompilatora .lnx w prawdziwym interpreterze LinuxCNC 2.9 (`rs274`). Sesja 039.

Model-Author: Claude
Wymaga LinuxCNC RIP (`LINUXCNC_DIR` albo ~/.cache/linuxcnc-2.9); marker `linuxcnc`.
Interpreter czyta plik do końca i wypisuje wywołania kanoniczne; błąd składni albo
niedozwolony kod kończy przebieg komunikatem błędu przed PROGRAM_END.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.linuxcnc

GOLDEN_DIR = Path(__file__).with_name("golden")


_CANON = re.compile(r"^\s*\d+ N\.+ ")
_MENU = ("enter a number:", "1 = ", "2 = ", "3 = ", "4 = ", "5 = ", "enter choice")


def _root() -> Path:
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "bin" / "rs274").exists():
        pytest.skip(f"brak rs274 w {root}")
    return root


def _errors(root: Path, ngc: Path) -> tuple[list[str], str]:
    """Linie błędów interpretera (rs274 zawsze kończy się kodem 0 i drukuje menu)."""
    sim = root / "configs" / "sim" / "axis"
    run = subprocess.run(
        ["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null && "
                       f"rs274 -i axis.ini -t sim.tbl -n 0 '{ngc}' </dev/null"],
        cwd=sim, capture_output=True, text=True, timeout=60, check=False)
    output = run.stdout + run.stderr
    errors = []
    for line in output.splitlines():
        text = line.replace("enter choice => executing", "").strip()
        if text and not _CANON.match(line) and not text.startswith(_MENU):
            errors.append(text)
    return errors, output


@pytest.mark.parametrize("ngc", sorted(GOLDEN_DIR.glob("*.ngc")), ids=lambda p: p.stem)
def test_golden_programs_parse_in_linuxcnc(ngc):
    errors, output = _errors(_root(), ngc)
    assert errors == [], output
    assert "PROGRAM_END()" in output, output


def test_interpreter_errors_are_detected(tmp_path):
    bad = tmp_path / "zly.ngc"
    bad.write_text("G21\nG1 X2\nM2\n", encoding="utf-8")  # G1 bez posuwu
    errors, _ = _errors(_root(), bad)
    assert any("feed rate" in e for e in errors)
