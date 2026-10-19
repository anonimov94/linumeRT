"""Model nakładki linumeRT na QtDragon (bez Qt i LinuxCNC). Model-Author: Claude · HMI-PoC.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "screens" / "linumert"
sys.path.insert(0, str(SCREEN))

import linumert_shell_model as m  # noqa: E402


def ready(**kw) -> m.ShellState:
    base = dict(estop=False, machine_on=True, homed={"X", "Y", "Z"}, file="/nc/a.ngc")
    base.update(kw)
    return m.ShellState(**base)


# ---- tokeny i styl (CLAUDE.md §6a) --------------------------------------------------------------

def test_fallback_tokens_match_tokens_yaml() -> None:
    data = yaml.safe_load((ROOT / "docs/design/tokens.yaml").read_text(encoding="utf-8"))
    assert m.TOKENS_FALLBACK["kolory"] == data["kolory"]
    assert m.TOKENS_FALLBACK["rozmiary"] == data["rozmiary"]
    assert m.load_tokens()["kolory"] == data["kolory"]


def test_load_tokens_falls_back(tmp_path) -> None:
    assert m.load_tokens(str(tmp_path / "brak.yaml")) is m.TOKENS_FALLBACK


def test_qss_uses_only_token_colors() -> None:
    qss = m.shell_qss(m.TOKENS_FALLBACK)
    colors = set(re.findall(r"#[0-9a-fA-F]{6}\b", qss))
    assert colors and colors <= set(m.TOKENS_FALLBACK["kolory"].values())
    assert f"min-height: {m.TOKENS_FALLBACK['rozmiary']['cel_dotykowy_px']}px" in qss
    assert qss.count("{") == qss.count("}")


def test_icons_exist() -> None:
    import ast

    tree = ast.parse((SCREEN / "linumert_shell.py").read_text(encoding="utf-8"))
    names = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
             and isinstance(n.value, str) and Path(m.icon_path(n.value)).exists()}
    for name in ("maszyna", "program", "narzedzia", "zero", "sonda", "diagnostyka",
                 "konfiguracja", "wtyczka", "start", "pauza", "stop", "blok", "bazuj"):
        assert Path(m.icon_path(name)).exists(), name
        assert name in names, name


def test_repo_root_resolves_through_config_symlink() -> None:
    link = ROOT / "config/sim/linumert_xyz/qtvcp/screens/linumert"
    assert link.is_symlink()
    assert Path(m.repo_root(str(link / "linumert_shell_model.py"))) == ROOT


# ---- reguły dostępności ----------------------------------------------------------------------

def test_estop_blocks_everything_but_estop() -> None:
    g = m.gates(m.ShellState())
    assert g["estop"].enabled
    for key in ("power", "mode", "home", "jog", "mdi", "start", "stop", "step"):
        assert not g[key].enabled, key
    assert g["start"].reason == "E-STOP aktywny"
    assert g["power"].reason == "najpierw zwolnij E-STOP"


def test_machine_off() -> None:
    g = m.gates(m.ShellState(estop=False))
    assert g["power"].enabled and not g["home"].enabled
    assert g["home"].reason == "maszyna wyłączona"


@pytest.mark.parametrize(("state", "key", "reason"), [
    (dict(homed=set()), "start", "najpierw bazowanie"),
    (dict(homed=set()), "mdi", "najpierw bazowanie"),
    (dict(file=""), "start", "brak programu"),
    (dict(interp="run"), "start", "program w toku"),
    (dict(interp="run"), "mode", "program w toku"),
    (dict(interp="run"), "home", "program w toku"),
    (dict(mode="mdi"), "jog", "przełącz na JOG"),
    (dict(interp="run", mode="auto"), "jog", "program w toku"),
    (dict(), "pause", "brak programu w toku"),
])
def test_gate_reasons(state, key, reason) -> None:
    gate = m.gates(ready(**state))[key]
    assert not gate.enabled and gate.reason == reason


def test_ready_machine_enables_operator_actions() -> None:
    g = m.gates(ready())
    for key in ("power", "mode", "home", "jog", "mdi", "start", "stop", "step"):
        assert g[key].enabled, key
    paused = m.gates(ready(interp="paused", mode="auto"))
    assert paused["start"].enabled and paused["pause"].enabled and paused["stop"].enabled
    assert not paused["mode"].enabled


def test_gantry_axes_all_homed() -> None:
    s = ready(axes=("X", "Y", "Z"), homed={"X", "Z"})
    assert not s.all_homed
    s.homed.add("Y")
    assert s.all_homed


# ---- teksty i formatowanie --------------------------------------------------------------------

@pytest.mark.parametrize(("state", "expected"), [
    (m.ShellState(), ("E-STOP", "err")),
    (m.ShellState(estop=False), ("Maszyna wyłączona", "warn")),
    (ready(homed=set()), ("Niebazowana", "warn")),
    (ready(interp="run"), ("Program w toku", "ok")),
    (ready(interp="paused"), ("Wstrzymany", "warn")),
    (ready(), ("Gotowa", "ok")),
])
def test_machine_pill(state, expected) -> None:
    assert m.machine_pill(state) == expected


def test_plant_pill() -> None:
    assert m.plant_pill(m.ShellState()) == ("Symulator LinuxCNC", "info")
    assert m.plant_pill(m.ShellState(plant="ok"))[1] == "ok"
    assert m.plant_pill(m.ShellState(plant="lost")) == ("Plant · brak łącza", "err")


def test_formatting() -> None:
    assert m.fmt_pos(50) == "50.000" and m.fmt_pos(-4, metric=False) == "-4.0000"
    assert m.fmt_int(18000) == "18 000" and m.fmt_int(960.4) == "960"
    assert m.fmt_pct(0.8) == "80 %"


def test_error_level() -> None:
    kinds = {"NML_ERROR": 1, "NML_TEXT": 2, "OPERATOR_ERROR": 11, "OPERATOR_DISPLAY": 13}
    assert m.error_level(1, kinds) == "err" and m.error_level(11, kinds) == "err"
    assert m.error_level(13, kinds) == "info" and m.error_level(2, kinds) == "info"


def test_program_window() -> None:
    lines = [f"L{i}" for i in range(1, 11)]
    win = m.program_window(lines, 4)
    assert [n for n, _t, _c in win] == [3, 4, 5, 6, 7]
    assert [c for _n, _t, c in win] == [False, True, False, False, False]
    assert m.program_window(lines, 0)[0] == (1, "L1", True)
    assert m.program_window(lines, 99)[-1] == (10, "L10", True)
    assert m.program_window([], 3) == []


# ---- zasady nakładki (statycznie) ------------------------------------------------------------

def test_shell_uses_only_qtvcp_actions() -> None:
    src = (SCREEN / "linumert_shell.py").read_text(encoding="utf-8")
    assert "linuxcnc.command" not in src and ".cmd." not in src
    assert "self.w.takeCentralWidget()" in src  # QtDragon przeniesiony, nie skopiowany


def test_upstream_handler_unchanged_marker() -> None:
    handler = (SCREEN / "linumert_handler.py").read_text(encoding="utf-8")
    assert "LINUMERT_SHELL" in handler and "linumert_shell.install(self)" in handler
    upstream = (SCREEN / "linumert_upstream_handler.py").read_text(encoding="utf-8")
    assert "linumert_shell" not in upstream
