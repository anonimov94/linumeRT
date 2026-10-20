"""Podprogramy o<lrt_...> z generatorów (sesja 048): nagłówek NgcGui, eksport, zgodność ruchu.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Test z markerem `linuxcnc` porównuje wywołania kanoniczne rs274 (STRAIGHT_TRAVERSE/FEED)
podprogramu i programu z generatora Pythona dla tych samych parametrów.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from linumert.generators.basic import FaceMill
from linumert.generators.drilling import DrillHoles
from linumert.generators.subroutines import (
    DRILL_CIRCLE,
    DRILL_GRID,
    FACE_MILL,
    SUBROUTINES,
    export,
    main,
)
from linumert.programs.lexer import check

_NGCGUI_PARAM = re.compile(r"^#<([a-z_0-9]+)> = #(\d+) \(=(-?[0-9.]+) [^()]+\)$")


@pytest.mark.parametrize("sub", SUBROUTINES, ids=lambda s: s.name)
def test_ngcgui_header_and_syntax(sub):
    lines = sub.text().splitlines()
    assert lines[0].startswith("(info: ") and lines[1] == f"o<{sub.name}> sub"
    assert lines[-1] == f"o<{sub.name}> endsub"
    for i, p in enumerate(sub.params, start=1):
        m = _NGCGUI_PARAM.match(lines[1 + i])
        assert m and m.group(1) == p.name and int(m.group(2)) == i, lines[1 + i]
    assert len(sub.params) <= 30  # NgcGui: #1…#30
    sub.text().encode("ascii")
    assert check(sub.text() + sub.call() + "\nM2\n") == []
    assert not re.search(r"\bM(98|99|2|30)\b", sub.text())


def test_call_uses_header_order_and_rejects_unknown():
    assert FACE_MILL.call(x1=120, safe_z=10).startswith("o<lrt_face_mill> call [0] [0] [120]")
    assert FACE_MILL.call(x1=120, safe_z=10).endswith("[200] [10]")
    with pytest.raises(ValueError, match="nieznane"):
        DRILL_GRID.call(depthh=3)


def test_export(tmp_path, capsys):
    paths = export(tmp_path / "user_macros")
    assert [p.name for p in paths] == [f"{s.name}.ngc" for s in SUBROUTINES]
    assert paths[0].read_text(encoding="ascii") == FACE_MILL.text()
    assert main([str(tmp_path / "m")]) == 0 and "lrt_drill_grid.ngc" in capsys.readouterr().out


# ---- zgodność z generatorami w interpreterze LinuxCNC ------------------------------------

_MOVE = re.compile(r"(STRAIGHT_TRAVERSE|STRAIGHT_FEED)\(([^)]*)\)")


def _root() -> Path:
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "bin" / "rs274").exists():
        pytest.skip(f"brak rs274 w {root}")
    return root


def _moves(root: Path, tmp_path: Path, text: str) -> list[tuple]:
    ngc = tmp_path / "p.ngc"
    ngc.write_text("G21 G90 G17 G40 G49 G80 G94\n" + text + "\nM2\n", encoding="utf-8")
    run = subprocess.run(["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null "
                          f"&& rs274 -n 0 '{ngc}' </dev/null"], capture_output=True, text=True,
                         timeout=60, check=False)
    assert "PROGRAM_END" in run.stdout, run.stdout[-2000:] + run.stderr
    return [(m.group(1), *(round(float(v), 3) for v in m.group(2).split(",")[:3]))
            for m in _MOVE.finditer(run.stdout)]


def _generator(gen, params) -> str:
    values, issues = gen.normalize(params)
    assert not issues and not gen.check(values, 0)
    return "\n".join(gen.generate(values))


@pytest.mark.linuxcnc
@pytest.mark.parametrize("params", [
    {"x1": 100, "y1": 50, "depth": 2.5, "step_down": 1, "tool_d": 10},
    {"x0": -20, "y0": 5, "x1": 30, "y1": 33, "z_top": 2, "depth": 1, "step_down": 0.4,
     "tool_d": 12, "stepover": 55, "overrun": 1, "mode": "one_way", "safe_z": 8},
])
def test_face_mill_subroutine_matches_generator(tmp_path, params):
    root = _root()
    sub_params = {k: v for k, v in params.items() if k != "mode"}
    sub_params["one_way"] = 1 if params.get("mode") == "one_way" else 0
    expected = _moves(root, tmp_path, _generator(FaceMill(), params))
    got = _moves(root, tmp_path, FACE_MILL.text() + FACE_MILL.call(**sub_params))
    assert len(expected) > 10 and got == expected


@pytest.mark.linuxcnc
@pytest.mark.parametrize("cycle", ["G81", "G82", "G83", "G73"])
def test_drill_grid_subroutine_matches_generator(tmp_path, cycle):
    root = _root()
    common = {"z_top": 1, "depth": 6, "r_plane": 2, "peck": 2, "feed": 120}
    params = {"pattern": "grid", "x": 5, "y": 7, "count": 3, "rows": 2, "dx": 15, "dy": 12,
              "cycle": cycle, "retract": "G99", **common}
    expected = _moves(root, tmp_path, _generator(DrillHoles(), params))
    got = _moves(root, tmp_path, DRILL_GRID.text() + DRILL_GRID.call(
        x=5, y=7, count=3, rows=2, dx=15, dy=12, cycle=int(cycle[1:]), retract=99, **common))
    assert len(expected) >= 12 and got == expected


@pytest.mark.linuxcnc
@pytest.mark.parametrize("pattern, sweep", [("circle", 360), ("arc", 120)])
def test_drill_circle_subroutine_matches_generator(tmp_path, pattern, sweep):
    root = _root()
    params = {"pattern": pattern, "x": 40, "y": 30, "radius": 25, "count": 5, "angle": 15,
              "sweep": sweep, "cycle": "G81", "depth": 4}
    expected = _moves(root, tmp_path, _generator(DrillHoles(), params))
    got = _moves(root, tmp_path, DRILL_CIRCLE.text() + DRILL_CIRCLE.call(
        x=40, y=30, radius=25, count=5, angle=15, sweep=sweep, depth=4))
    assert got == expected


def test_user_doc_lists_every_parameter():
    doc = (Path(__file__).resolve().parents[1] / "docs/user/PODPROGRAMY.md").read_text()
    for sub in SUBROUTINES:
        assert f"## `{sub.name}`" in doc
        for i, p in enumerate(sub.params, start=1):
            assert f"| {i} | `{p.name}` | {p.default:g} | {p.label} |" in doc
