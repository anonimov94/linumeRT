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


# ---- diagnostyka ----------------------------------------------------------------------------

@pytest.mark.parametrize(("sw", "name", "level"), [
    (0x0000, "Rozruch (not ready)", "info"), (0x0250, "Wyłączony (switch on disabled)", "warn"),
    (0x0231, "Gotowy do załączenia", "warn"), (0x0233, "Załączony", "warn"),
    (0x1237, "Praca", "ok"), (0x0218, "Błąd", "err"), (0x021F, "Reakcja na błąd", "err"),
    (0x0217, "Szybki stop", "err"),
])
def test_cia402_state(sw, name, level) -> None:
    assert m.cia402_state(sw) == (name, level)


def test_drive_faults_map_to_catalog() -> None:
    faults = m.drive_fault_codes((ROOT / "plant/core/drive.h").read_text(encoding="utf-8"))
    texts = m.catalog_texts(yaml.safe_load(
        (ROOT / "core/linumert/alarms/catalog.yaml").read_text(encoding="utf-8")))
    assert faults[0x8130] == "E-4003" and faults[0x8611] == "E-4201" and len(faults) == 11
    assert all(code in texts for code in faults.values())
    assert m.drive_error_text(0, faults, texts) == "—"
    assert m.drive_error_text(0x8130, faults, texts, "X").startswith("E-4003 · Brak ramek")
    assert "?" not in m.drive_error_text(0xFF00, faults, texts, "Z")
    assert m.drive_error_text(0x1234, faults, texts) == "603Fh = 0x1234"


def test_link_counters_are_lrt_net_pins() -> None:
    comp = (ROOT / "hal/lrt_net.comp").read_text(encoding="utf-8")
    for pin, _label in m.LINK_COUNTERS:
        assert re.search(rf"^pin out \w+\s+{re.escape(pin)}\b", comp, re.M), pin


# ---- produkcja --------------------------------------------------------------------------------

def test_run_clock_counts_only_run() -> None:
    clock = m.RunClock()
    clock.update("run", 10.0)
    clock.update("paused", 15.0)  # 5 s pracy
    clock.update("paused", 40.0)
    clock.update("run", 40.0)
    assert clock.value(42.0) == pytest.approx(7.0)
    clock.update("idle", 43.0)
    assert clock.value(100.0) == pytest.approx(8.0)
    clock.reset()
    assert clock.value(100.0) == 0.0


def test_fmt_duration() -> None:
    assert m.fmt_duration(0) == "00:00" and m.fmt_duration(161) == "02:41"
    assert m.fmt_duration(3725) == "1:02:05" and m.fmt_duration(-3) == "00:00"


def test_run_from_line_gate() -> None:
    s = ready(total_lines=12)
    assert m.run_from_line_gate(s, 6).enabled
    assert m.run_from_line_gate(s, 13).reason == "linia poza zakresem 1–12"
    paused, unhomed = ready(total_lines=12, interp="paused"), ready(total_lines=12, homed=set())
    assert m.run_from_line_gate(paused, 6).reason == "program w toku"
    assert m.run_from_line_gate(unhomed, 6).reason == "najpierw bazowanie"
    assert "pomija wcześniejsze bloki" in m.RUN_FROM_LINE_WARNING.format(line=6)


# ---- start i przyczyny E-STOP -------------------------------------------------------------------

def test_checklist_fresh_machine() -> None:
    items = {i.key: i for i in m.checklist(m.ShellState())}
    assert items["estop"].level == "err" and items["estop"].action == "estop"
    assert items["power"].action == ""  # najpierw E-STOP
    assert items["homed"].detail == "niebazowane: X, Y, Z" and items["homed"].action == ""
    assert items["plant"].level == "info" and "drives" not in items
    assert items["program"].action == "program"
    assert not m.ready_to_run(list(items.values()))


def test_checklist_ready_and_plant() -> None:
    s = ready(plant="ok", tool=3)
    items = m.checklist(s, drive_fault=False)
    assert all(i.level == "ok" for i in items) and m.ready_to_run(items)
    s.feed_override = 0.8
    items = {i.key: i for i in m.checklist(s, drive_fault=True)}
    assert items["overrides"].detail == "F 80 %" and items["overrides"].level == "warn"
    assert items["drives"].action == "diag"
    assert not m.ready_to_run(list(items.values()))
    lost = {i.key: i for i in m.checklist(ready(plant="lost"))}
    assert lost["plant"].level == "err"


def test_checklist_actions_have_labels() -> None:
    for s in (m.ShellState(), m.ShellState(estop=False), ready(homed=set()), ready(file=""),
              ready(feed_override=0.5), ready(plant="ok")):
        for item in m.checklist(s, drive_fault=True):
            assert not item.action or item.action in m.ACTION_LABEL


@pytest.mark.parametrize(("args", "text"), [
    ((None, None, None, True), "E-STOP z ekranu (programowy)"),
    ((False, True, 0), "pętla E-STOP otwarta"),
    ((True, False, 3), "przerwa łącza LRT-NET z Plant, 3 cykli"),
    ((True, True, 25), "przerwa łącza LRT-NET z Plant, 25 cykli"),
    ((None, None, None), "emc-enable-in"),
    ((True, True, 2), "przyczyna przejściowa"),
])
def test_estop_reason(args, text) -> None:
    assert text in m.estop_reason(*args)
