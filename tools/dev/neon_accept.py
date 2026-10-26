#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""N4: odbiór Classic × Neon na prawdziwym LinuxCNC sim (AUTO) + monitor skórek.

Model-Author: Claude · 2026-10-25. Uruchomienie w WSL pod rip-environment i Xvfb:
    xvfb-run -a bash tools/dev/neon_rip.sh python3 tools/dev/neon_accept.py OUT_DIR
Zajmuje blokadę `linuxcnc`. Monitor jest tylko do odczytu; sterowanie programem robi ten skrypt
(estop reset, ON, bazowanie, AUTO, start) przez `linuxcnc.command`, jak test D38 (bypass E-STOP
wyłącznie w uruchomieniu bez ekranu). Wynik: zrzuty PNG, neon_accept.json.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "screens/linumert"), str(ROOT / "core"),
                str(ROOT / "simulation")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import linuxcnc  # noqa: E402
from rip_support import rip_root, start_linuxcnc, stop_linuxcnc  # noqa: E402

DEMO = ROOT / "config/sim/nc_files/linumert_neon_demo.ngc"


def prepare(work: Path) -> Path:
    shutil.copytree(ROOT / "config/sim/linumert_xyz", work, symlinks=True)
    ini = work / "linumert_xyz.ini"
    text = ini.read_text().replace("DISPLAY = qtvcp linumert", "DISPLAY = neon_headless")
    # Bez ekranu nie ma postgui; potwierdzenie M6 (sim_toolchange) dajemy osobnym plikiem HAL.
    text = re.sub(r"^POSTGUI_HALFILE.*$", "HALFILE = neon_toolchange.hal", text, flags=re.M)
    (work / "neon_toolchange.hal").write_text(
        "net linumert.io.tool-change iocontrol.0.tool-change => sim_toolchange.in\n"
        "net linumert.io.tool-changed sim_toolchange.out => iocontrol.0.tool-changed\n")
    text = text.replace("HALFILE = ../../hal/", f"HALFILE = {ROOT / 'config/hal'}/")
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    text = text.replace("PORT = 47700", "PORT = 47831")
    text = re.sub(r"^TOOL_TABLE\s*=.*$", "TOOL_TABLE = neon.tbl", text, flags=re.M)
    text = re.sub(r"^PARAMETER_FILE\s*=.*$", "PARAMETER_FILE = neon.var", text, flags=re.M)
    ini.write_text(text)
    (work / "neon.tbl").write_text("T1 P1 Z0 D6 ; frez palcowy\n")
    shutil.copy(DEMO, work / DEMO.name)
    display = work / "neon_headless"
    display.write_text("#!/bin/sh\nexec sleep 3600\n")
    display.chmod(0o755)
    return ini


def main(out: Path, skin="classic-digital", installed=False) -> int:
    from linumert_neon_render import PRESETS
    from linumert_neon_view import NeonPathView
    from linumert_skin_contract import PresentationPreferences
    from linumert_skin_monitor import SkinMonitor
    from PyQt5 import QtWidgets

    out.mkdir(parents=True, exist_ok=True)
    root = None if installed else rip_root()
    work = Path(tempfile.mkdtemp(prefix="neon-accept-")) / "cfg"
    ini = prepare(work)
    env = {**os.environ, "INI_FILE_NAME": str(ini), "CONFIG_DIR": str(work),
           "PATH": str(work) + os.pathsep + os.environ.get("PATH", "")}
    os.environ.update({k: env[k] for k in ("INI_FILE_NAME", "CONFIG_DIR")})
    program = work / DEMO.name
    cnc = start_linuxcnc(root, ini, env)
    result: dict = {"program": DEMO.name, "shots": {}, "samples": [], "frame_ms": {}}
    try:
        s = None
        for _ in range(120):
            if cnc.poll() is not None:
                raise RuntimeError("LinuxCNC zakończył się przy starcie")
            # stat() mapuje dane narzędzi (~/.tool.mmap) tylko, gdy LinuxCNC już je utworzył
            if (Path.home() / ".tool.mmap").exists():
                try:
                    s = linuxcnc.stat()
                    s.poll()
                    break
                except (linuxcnc.error, SystemError):
                    s = None
            time.sleep(0.5)
        if s is None:
            raise RuntimeError("brak NML")
        c = linuxcnc.command()
        if os.environ.get("NEON_PROBE_LOADER"):
            loader = ROOT / "screens/linumert/linumert_neon_loader.py"
            for label, cwd, drop in (("ini+cfg", work, ()), ("ini+root", ROOT, ()),
                                     ("noini+cfg", work, ("INI_FILE_NAME",))):
                penv = {k: v for k, v in os.environ.items() if k not in drop}
                r = subprocess.run([sys.executable, str(loader), str(program)], cwd=cwd,
                                   env=penv, capture_output=True, text=True, check=False)
                result.setdefault("probe", {})[label] = [r.returncode, r.stdout[:200],
                                                         r.stderr[-300:]]
            if shutil.which("gdb"):
                r = subprocess.run(["gdb", "-batch", "-ex", "run", "-ex", "bt 12", "--args",
                                    sys.executable, str(loader), str(program)], cwd=work,
                                   capture_output=True, text=True, check=False)
                result["probe"]["gdb"] = r.stdout[-1800:]
            return 0
        app = QtWidgets.QApplication([])
        window = SkinMonitor(PresentationPreferences(skin, "neon-punk", "pl"))
        window.resize(1280, 800)
        window.show()

        def pump(seconds, cond=None):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                app.processEvents()
                s.poll()
                if cond and cond():
                    return True
                time.sleep(0.02)
            return cond is None

        def shot(name):
            pump(0.6)
            path = out / f"{name}.png"
            window.grab().save(str(path))
            result["shots"][name] = path.name

        c.state(linuxcnc.STATE_ESTOP_RESET)
        pump(5, lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET)
        c.state(linuxcnc.STATE_ON)
        pump(5, lambda: s.task_state == linuxcnc.STATE_ON)
        c.mode(linuxcnc.MODE_MANUAL)
        c.wait_complete()
        c.home(-1)
        assert pump(60, lambda: all(s.homed[:3])), "bazowanie nie zakończone"
        c.mode(linuxcnc.MODE_MDI)
        c.wait_complete()
        c.mdi("G21 G90 G10 L2 P1 X100 Y100 Z-50")   # G54: detal wewnątrz zakresu osi sim
        c.wait_complete()
        c.mode(linuxcnc.MODE_AUTO)
        c.wait_complete()
        c.program_open(str(program))
        c.wait_complete()
        pump(4)                                       # monitor wczytuje ścieżkę (osobny proces)
        scene = window.shared.get("path_scene")
        result["scene_loaded"] = scene is not None
        result["program_note"] = window.shared.get("program_note")
        result["nml_file"] = s.file
        result["monitor_file"] = window.sample.file if window.sample else None
        result["monitor_reason"] = window.reason
        shot("01-start")
        c.auto(linuxcnc.AUTO_RUN, 0)
        c.wait_complete()
        total = len(scene.toolpath.moves) if scene else 0
        mid_line = scene.toolpath.moves[total // 2].line if scene else 0
        shot_mid = False
        t0 = time.monotonic()
        last_line, last_move = -1, time.monotonic()
        while time.monotonic() - t0 < 300:
            pump(0.1)
            if s.motion_line != last_line:
                last_line, last_move = s.motion_line, time.monotonic()
            elif time.monotonic() - last_move > 40:
                result["stalled_at"] = [s.motion_line, s.interp_state, s.state, s.paused]
                break
            sample = window.sample
            running = s.interp_state != linuxcnc.INTERP_IDLE
            if sample and scene and running:
                mv = scene.toolpath.moves[min(scene.index, total - 1)]
                result["samples"].append({
                    "t": round(time.monotonic() - t0, 2), "line": s.motion_line,
                    "monitor_line": sample.motion_line,
                    "dtg_nml": s.distance_to_go, "dtg_monitor": sample.distance_to_go,
                    "dtg_scene": scene.toolpath.dtg(scene.index, scene.s),
                    "scene_line": mv.line,
                    "actual": [round(v, 4) for v in s.actual_position[:3]],
                    "dro": [round(v, 4) for v in sample.positions[:3]]})
            if not shot_mid and running and s.motion_line >= mid_line:
                # Porównanie na stojącej maszynie (próbka monitora jest starsza o 0,1–0,3 s).
                c.auto(linuxcnc.AUTO_PAUSE)
                pump(2.5)
                sample = window.sample
                result["paused_compare"] = {
                    "line": [s.motion_line, sample.motion_line],
                    "dtg_nml_vs_monitor": [s.distance_to_go, sample.distance_to_go],
                    "dtg_scene": scene.toolpath.dtg(scene.index, scene.s),
                    "dro_nml": [round(v, 4) for v in s.actual_position[:3]],
                    "dro_monitor": [round(v, 4) for v in sample.positions[:3]]}
                from linumert_skin_readouts import FeedReadout, ProgramView, ToolReadout
                feed = window.workspace.findChild(FeedReadout)
                tool = window.workspace.findChild(ToolReadout)
                program_view = window.workspace.findChild(ProgramView)
                result["instruments"] = {
                    "feed_mm_min": feed.feed, "spindle_setpoint_rpm": feed.spindle,
                    "tool": tool.number, "diameter_mm": tool.diameter,
                    "table_z_mm": tool.length,
                    "source_visible": bool(program_view.findChild(
                        QtWidgets.QPlainTextEdit).toPlainText())}
                shot("02-srodek")
                shot_mid = True
                c.auto(linuxcnc.AUTO_RESUME)
            if shot_mid and not running:
                break
        pump(1.5)
        shot("03-koniec")
        result["completed"] = s.interp_state == linuxcnc.INTERP_IDLE
        # Czas klatki dla 3 presetów (detal + maszyna); program zakończony, scena stoi.
        for name, preset in PRESETS.items():
            views = window.findChildren(NeonPathView)
            for v in views:
                v.set_settings(preset, persist=False)
            pump(0.5)
            for v in views:
                v.frame_ms = 0.0
            pump(4)
            result["frame_ms"][name] = {v.mode: round(v.frame_ms, 2) for v in views}
            shot(f"04-preset-{name}")
    finally:
        stop_linuxcnc(cnc, root, work)
        (out / "linuxcnc.log").write_text(cnc.stdout.read() if cnc.stdout else "")
        (out / "neon_accept.json").write_text(json.dumps(result, indent=1))
    assert result.get("scene_loaded") and result.get("completed"), result
    compare = result["paused_compare"]
    assert compare["line"][0] == compare["line"][1], compare
    assert abs(compare["dtg_nml_vs_monitor"][0] - compare["dtg_nml_vs_monitor"][1]) < 0.01
    assert result["instruments"]["tool"] == 1 and result["instruments"]["source_visible"]
    assert result["instruments"]["spindle_setpoint_rpm"] is not None
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=Path("neon-out"))
    parser.add_argument("--skin", choices=("classic-digital", "cyberdeck"),
                        default="classic-digital")
    parser.add_argument("--installed", action="store_true",
                        help="Use installed LinuxCNC instead of RIP")
    parser.add_argument("--model", choices=("Claude", "Codex"), default="Claude")
    args = parser.parse_args()
    lock = subprocess.run([sys.executable, str(ROOT / "tools/lock.py"), "acquire", "linuxcnc",
                           "--model", args.model, "--note", "neon live acceptance"], check=False)
    if lock.returncode:
        raise SystemExit(75)
    try:
        raise SystemExit(main(args.output, args.skin, args.installed))
    finally:
        subprocess.run([sys.executable, str(ROOT / "tools/lock.py"), "release", "linuxcnc",
                        "--model", args.model], check=False)
