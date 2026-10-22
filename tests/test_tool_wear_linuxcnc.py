# SPDX-License-Identifier: GPL-2.0-or-later
"""Actual G41/G42 use the corrected table radius. Model-Author: Codex."""

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest
from linumert.tools.db import Tool, ToolDB


@pytest.mark.linuxcnc
@pytest.mark.parametrize("code,sign", [("G41", 1), ("G42", -1)])
@pytest.mark.parametrize("wear", [-0.02, 0.02])
def test_cutter_compensation_uses_effective_diameter(tmp_path, code, sign, wear):
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache/linuxcnc-2.9"))
    if not (root / "bin/rs274").exists():
        pytest.skip(f"brak rs274 w {root}")
    with ToolDB(":memory:") as db:
        db.add(Tool(1, 1, type="flat", params={"d":6, "l":30, "flute_length":15,
                                             "d_wear":wear}))
        table = db.export_tbl(tmp_path / "tool.tbl")
    program = tmp_path / "wear.ngc"
    program.write_text(
        "G21 G17 G90 G94 G40\nT1 M6\nG0 X-10 Y0 Z5\nG1 Z0 F100\n"
        f"{code} D1\nG1 X0 Y0\nG1 X20 Y0\nG1 X30 Y0\nG40\nG1 X40 Y0\nM2\n",
        encoding="utf-8")
    private_home = tmp_path / "home"
    private_home.mkdir()
    command = (f"source {shlex.quote(str(root / 'scripts/rip-environment'))} >/dev/null && "
               f"rs274 -i {shlex.quote(str(root / 'configs/sim/axis/axis_mm.ini'))} "
               f"-t {shlex.quote(str(table))} "
               f"-n 0 {shlex.quote(str(program))}")
    result = subprocess.run(
        ["bash", "-c", command], cwd=tmp_path, stdin=subprocess.DEVNULL,
        env=dict(os.environ, HOME=str(private_home), LC_ALL="C"),
        capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    points = [tuple(float(word) for word in args.split(",")[:3])
              for args in re.findall(r"STRAIGHT_FEED\(([^)]*)\)", result.stdout)]
    expected_y = sign * (6 + wear) / 2
    assert any(abs(x - 20) < 1e-6 and abs(y - expected_y) < 1e-4
               for x, y, _z in points), result.stdout + result.stderr
