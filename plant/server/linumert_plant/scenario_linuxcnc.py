"""Scenariusze Plant z prawdziwym LinuxCNC (RIP) zamiast atrapy mastera (sesja 024).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 024.

Przebieg: kopia konfiguracji `config/plant/linumert_plant_xyz` (bez ekranu, port LRT-NET
z zakresu scenariusza), Plant `serve --lockstep --panel 0` w osobnym procesie, LinuxCNC RIP
(`LINUXCNC_DIR`, domyślnie ~/.cache/linuxcnc-2.9) z komponentami lrt_net i lrt_cia402.
Skrypt sterujący w Pythonie LinuxCNC (`linuxcnc.command`): E-STOP reset, włączenie, bazowanie
wszystkich osi, potem kroki scenariusza od chwili T0 (program w AUTO, MDI, oczekiwanie,
reset). Awarie i parametry live wstrzykuje runner przez REST panelu Plant (`/api/faults`,
`/api/live`) w czasie względem T0 albo po linii programu (`at_line`, z `motion_line`).
Wyniki: pozycje i błąd nadążania z `linuxcnc.stat`, alarmy z kanału błędów i stanu task,
stan napędów i zdarzenia z raportu Plant, przebiegi z telemetrii panelu.
Wymaga Linuksa z RIP; konfiguracja LinuxCNC istnieje dla maszyny mill_servo_table.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from .scenario import (
    ERROR_ALARMS,
    ROOT,
    Criterion,
    Scenario,
    ScenarioError,
    ScenarioResult,
    evaluate,
    versions,
)

CONFIG = ROOT / "config" / "plant" / "linumert_plant_xyz"
DEFAULT_PORT = 47820
DRIVER_ACTIONS = ("program", "mdi", "wait", "fault_reset")
HOST_ACTIONS = ("fault", "clear", "set_param")
JOINTS = {"X": [0], "Y": [1, 2], "Z": [3]}  # linumert_plant_xyz: drv_x, drv_y1, drv_y2, drv_z

DRIVER = r'''
import json, sys, time
import hal
import linuxcnc
plan = json.loads(sys.argv[1])
_comp = hal.component("lrt_scenariusz")  # hal.get_value wymaga komponentu
_comp.ready()
c, s, e = linuxcnc.command(), linuxcnc.stat(), linuxcnc.error_channel()
out = {"errors": [], "setup_errors": [], "alarms": {}, "line_max": 0}
T0 = None
driver_started = time.monotonic()
def now():
    return 0.0 if T0 is None else time.time() - T0
def poll():
    s.poll()
    while True:
        msg = e.poll()
        if not msg:
            break
        out["errors" if T0 is not None else "setup_errors"].append([round(now(), 3), msg[1]])
        if T0 is None and plan.get("diagnostics"):
            # Error-channel receipt time, not the servo cycle that caused the error.
            # NML and subsequent HAL reads are sequential, never an atomic RT trace.
            sample = {"elapsed": time.monotonic() - driver_started, "message": msg[1],
                      "task_state": s.task_state,
                      "joints": [dict(joint) for joint in s.joint]}
            try:
                sample["link"] = {name: hal.get_value("lrt-net.0." + name) for name in
                                  ("sent", "received", "missed", "reply-age", "plant-lost",
                                   "plant-late", "plant-jitter-us", "connected")}
            except Exception as exc:
                sample["hal_read_error"] = str(exc)
            sample["read_finished"] = time.monotonic() - driver_started
            out.setdefault("setup_samples", []).append(sample)
            print("SETUP_ERROR " + json.dumps(sample), flush=True)
def wait(cond, timeout):
    t = time.time()
    while time.time() - t < timeout:
        poll()
        if cond():
            return True
        time.sleep(0.02)
    return False
def machine_on():
    c.state(linuxcnc.STATE_ESTOP_RESET)
    wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET, 5)
    c.state(linuxcnc.STATE_ON)
    return wait(lambda: s.task_state == linuxcnc.STATE_ON, 5)
out["machine_on"] = machine_on()
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
c.teleop_enable(0); c.wait_complete()
for attempt in range(2):  # WSL bez RT: pojedynczy błąd nadążania przy bazowaniu — ponów raz
    c.home(-1)
    out["homed"] = wait(lambda: all(s.homed[:4]), 60)
    if out["homed"]:
        break
    out["machine_on"] = machine_on()
    c.mode(linuxcnc.MODE_MANUAL); c.wait_complete()
    c.teleop_enable(0); c.wait_complete()
c.teleop_enable(1); c.wait_complete()
time.sleep(0.5); poll()
out["start"] = [round(v, 4) for v in s.actual_position[:3]]
c.mode(linuxcnc.MODE_MDI); c.wait_complete()
T0 = time.time()
print("T0", flush=True)
steps = sorted(plan["steps"], key=lambda st: st["at"])
program = {"running": False, "aborted": False, "done": False, "started": False}
last_line = 0
estop_seen = False
out["states"] = []
state = None
ferr = [0.0] * 4
peaks = {}
while now() < plan["duration"]:
    poll()
    if (s.task_state, s.interp_state) != state:
        state = (s.task_state, s.interp_state)
        out["states"].append([round(now(), 3), s.task_state, s.interp_state])
    for j in range(4):
        value = abs(s.joint[j]["ferror_current"])
        if value > ferr[j]:
            ferr[j] = value
            if plan.get("diagnostics"):
                peak = {"t": now(), "joint": j, "ferror": value,
                        "line": s.motion_line, "joint_status": dict(s.joint[j])}
                peak["link"] = {name: hal.get_value("lrt-net.0." + name) for name in
                                ("sent", "received", "missed", "reply-age", "plant-lost",
                                 "plant-late", "plant-jitter-us", "connected")}
                peak["drive"] = {name: hal.get_value("lrt-net.0.axis.%d.%s" % (j, name))
                                 for name in ("pos-cmd", "pos-fb", "ferror", "torque")}
                peaks[str(j)] = peak
                print("PEAK " + json.dumps(peak), flush=True)
    if s.motion_line != last_line and program["running"]:
        last_line = s.motion_line
        out["line_max"] = max(out["line_max"], last_line)
        print("LINE", last_line, flush=True)
    for j in range(4):  # 603Fh napędu z lrt_net → alarm katalogu (jak ekran operatora)
        try:
            code = int(hal.get_value("lrt-net.0.axis.%d.error-code" % j))
        except Exception as exc:
            out.setdefault("hal_error", str(exc))
            code = 0
        if code:
            out.setdefault("codes", {})[str(j)] = code
        alarm = plan["error_alarms"].get(str(code))
        if alarm:
            out["alarms"].setdefault(alarm, round(now(), 3))
    if s.task_state == linuxcnc.STATE_ESTOP and not estop_seen and out["machine_on"]:
        estop_seen = True
        out["alarms"].setdefault("E-1100", round(now(), 3))
    if program["running"]:
        late_error = out["errors"] and out["errors"][-1][0] >= program["t"]
        if s.task_state != linuxcnc.STATE_ON or late_error:
            program["aborted"] = True
        if s.interp_state == linuxcnc.INTERP_IDLE and now() - program["t"] > 0.3:
            program["running"] = False
            program["done"] = not program["aborted"]
    while steps and steps[0]["at"] <= now():
        st = steps.pop(0)
        a = st["action"]
        if a == "program":
            c.mode(linuxcnc.MODE_AUTO); c.wait_complete()
            c.program_open(plan["program"]); c.wait_complete()
            c.auto(linuxcnc.AUTO_RUN, 0)
            program.update(running=True, started=True, aborted=False, t=now())
        elif a == "mdi":
            c.mode(linuxcnc.MODE_MDI); c.wait_complete()
            c.mdi(st["command"])
        elif a == "fault_reset":
            ok = machine_on()
            c.mode(linuxcnc.MODE_MDI); c.wait_complete()
            out.setdefault("resets", []).append([round(now(), 3), ok])
        elif a == "wait":
            until = st.get("until") or {}
            if "idle" in until:
                wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, st.get("timeout", 5))
            else:
                time.sleep(float(st.get("seconds", 0)))
    time.sleep(0.01)
time.sleep(0.2); poll()
out["program"] = program
out["pos"] = [round(v, 4) for v in s.actual_position[:3]]
out["ferr"] = ferr
out["peaks"] = peaks
out["task_state"] = s.task_state
print("RESULT " + json.dumps(out), flush=True)
'''


def _rip():
    sys.path.insert(0, str(ROOT / "tests"))
    import rip_support  # noqa: E402 - wspólne uruchamianie RIP z testami (sesja 008)

    return rip_support


@contextmanager
def _workspace():
    """Opt-in forensic artifacts survive both failed criteria and runner exceptions."""
    base = os.environ.get("LINUMERT_SCENARIO_DIAGNOSTICS")
    if base:
        directory = Path(base).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        yield Path(tempfile.mkdtemp(prefix="lrt_scen_", dir=directory))
    else:
        with tempfile.TemporaryDirectory(prefix="lrt_scen_") as tmp:
            yield Path(tmp)


def _capture(stream, path: Path) -> None:
    with path.open("w", encoding="utf-8") as output:
        for line in stream:
            output.write(line)
            output.flush()


def _prepare(work: Path, port: int) -> Path:
    cfg = work / "cfg"
    shutil.copytree(CONFIG, cfg, symlinks=True)
    ini = cfg / "linumert_plant_xyz.ini"
    text = ini.read_text(encoding="utf-8")
    text = text.replace("DISPLAY = qtvcp linumert", "DISPLAY = linumert_bez_ekranu")
    # Bez ekranu nie ma grzyba HMI ani sygnału życia (D35): jawne obejście tylko tutaj;
    # plik HAL grzyba z repozytorium (ścieżka względna nie działa w kopii konfiguracji).
    text = text.replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    text = text.replace("HALFILE = ../../hal/", f"HALFILE = {CONFIG.parent.parent / 'hal'}/")
    text = re.sub(r"^POSTGUI_HALFILE.*$", "", text, flags=re.M)
    text = text.replace("PORT = 47700", f"PORT = {port}")
    text = text.replace("PROGRAM_PREFIX = ../../sim/nc_files",
                        f"PROGRAM_PREFIX = {ROOT / 'config/sim/nc_files'}")
    text = text.replace("TOOL_TABLE = ../../sim/linumert_xyz/tool.tbl",
                        f"TOOL_TABLE = {ROOT / 'config/sim/linumert_xyz/tool.tbl'}")
    ini.write_text(text, encoding="utf-8")
    script = cfg / "linumert_bez_ekranu"
    script.write_text("#!/bin/sh\nexec sleep 3600\n")
    script.chmod(0o755)
    return ini


class _Plant:
    """Plant w osobnym procesie z panelem (REST awarii); wyjście czytane w wątku."""

    def __init__(self, scen: Scenario, port: int, report: Path):
        env = {**os.environ, "PYTHONPATH": os.pathsep.join(
            str(ROOT / p) for p in ("core", "simulation", "plant/server"))}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "linumert_plant", "serve", "--plant",
             str(CONFIG / "plant.yaml"), "--lockstep", "--port", str(port), "--seed",
             str(scen.linuxcnc.get("seed", 5)), "--panel", "0", "--report", str(report),
             "--state-dir",
             str(report.parent / "state")], env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.lines: list[str] = []
        self.url: str | None = None
        self._ready = threading.Event()
        threading.Thread(target=self._read, daemon=True).start()
        if not self._ready.wait(60) or self.url is None:
            self.close()
            raise ScenarioError("Plant nie wystartował: " + " | ".join(self.lines[-5:]))

    def _read(self) -> None:
        for line in self.proc.stdout:
            self.lines.append(line.rstrip())
            if "panel http://" in line:
                self.url = line.split("panel ", 1)[1].strip().rstrip("/")
                self._ready.set()
        self._ready.set()

    def call(self, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data=data, method="GET" if body is None
                                     else "POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raise ValueError(json.loads(exc.read() or b"{}").get("detail", str(exc))) from None

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def _host_step(plant: _Plant, step, res: ScenarioResult, t: float) -> None:
    p = dict(step.params)
    res.log.append(f"{t:7.3f} s  {step.action} {p}")
    try:
        if step.action == "fault":
            kind = p.pop("fault")
            plant.call(f"/api/faults/{kind}", p)
        elif step.action == "clear":
            kind = p.pop("fault")
            plant.call(f"/api/faults/{kind}/clear", p)
        elif step.action == "set_param":
            plant.call("/api/live", {"drive": p["drive"], "path": p["path"], "value": p["value"]})
    except (ValueError, OSError) as exc:
        res.criteria.append(Criterion(f"krok {step.action} ({t:.3f} s)", False, str(exc)))


def run_linuxcnc(scen: Scenario, port: int | None = None) -> ScenarioResult:
    """Scenariusz z LinuxCNC RIP; ScenarioError, gdy scenariusz nie pasuje do konfiguracji."""
    if scen.machine.resolve() != (ROOT / "config/machines/mill_servo_table.yaml").resolve():
        raise ScenarioError(f"{scen.name}: konfiguracja LinuxCNC dla Plant istnieje tylko dla "
                            "mill_servo_table (config/plant/linumert_plant_xyz)")
    unsupported = [s.action for s in scen.steps
                   if s.action not in DRIVER_ACTIONS + HOST_ACTIONS + ("enable", "home")]
    if unsupported:
        raise ScenarioError(f"{scen.name}: kroki {unsupported} tylko z atrapą mastera")
    rip = _rip()
    root = Path(os.environ.get("LINUXCNC_DIR", Path.home() / ".cache" / "linuxcnc-2.9"))
    if not (root / "scripts" / "rip-environment").exists():
        raise ScenarioError(f"brak LinuxCNC RIP w {root} (LINUXCNC_DIR)")
    port = port or int(scen.linuxcnc.get("port", DEFAULT_PORT))
    res = ScenarioResult(scen, "linuxcnc", versions=versions())
    driver_steps = [{"action": s.action, "at": s.at or 0.0, **s.params} for s in scen.steps
                    if s.action in DRIVER_ACTIONS and s.at_line is None]
    host_steps = sorted([s for s in scen.steps if s.action in HOST_ACTIONS],
                        key=lambda s: (s.at_line is not None, s.at or 0.0, s.at_line or 0))
    plan = {"duration": scen.duration, "steps": driver_steps,
            "diagnostics": bool(os.environ.get("LINUMERT_SCENARIO_DIAGNOSTICS")),
            "error_alarms": {str(k): v for k, v in ERROR_ALARMS.items()},
            "program": str(scen.program) if scen.program else ""}
    with _workspace() as work:
        (work / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        ini = _prepare(work, port)
        (work / "driver.py").write_text(DRIVER, encoding="utf-8")
        report = work / "plant_report.json"
        with rip.installed_modules(root, work, ("lrt_net", "lrt_cia402", "lrt_estop2")):
            plant = _Plant(scen, port, report)
            env = {**os.environ, "PATH": f"{ini.parent}:{os.environ.get('PATH', '')}"}
            cnc = rip.start_linuxcnc(root, ini, env, console=plan["diagnostics"])
            capture = None
            if plan["diagnostics"]:
                capture = threading.Thread(target=_capture,
                                           args=(cnc.stdout, work / "linuxcnc.log"), daemon=True)
                capture.start()
            driver = None
            lines = []
            try:
                for _ in range(120):
                    time.sleep(0.5)
                    probe = rip.rip_run(root, "halcmd getp lrt-net.0.connected", ini.parent,
                                        env=env)
                    if probe.stdout.strip() == "TRUE" or cnc.poll() is not None:
                        break
                if cnc.poll() is not None:
                    if capture is not None:
                        capture.join(timeout=5)
                    output = ((work / "linuxcnc.log").read_text(encoding="utf-8")
                              if capture is not None else cnc.stdout.read())
                    raise ScenarioError("LinuxCNC nie wystartował: " + (output or ""))
                driver = subprocess.Popen(
                    ["bash", "-c", f"source '{root}/scripts/rip-environment' >/dev/null && "
                     f"exec python3 {work / 'driver.py'} '{json.dumps(plan)}'"],
                    cwd=ini.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True)
                t0 = None
                result_line = None
                pending = list(host_steps)
                lines = []
                for line in driver.stdout:
                    line = line.rstrip()
                    lines.append(line)
                    if line == "T0":
                        t0 = time.monotonic()
                        threading.Thread(target=_timed, args=(plant, pending, res, t0),
                                         daemon=True).start()
                    elif line.startswith("LINE "):
                        n = int(line.split()[1])
                        for st in [s for s in pending if s.at_line is not None and s.at_line <= n]:
                            pending.remove(st)
                            _host_step(plant, st, res, time.monotonic() - (t0 or 0))
                    elif line.startswith("RESULT "):
                        result_line = line[len("RESULT "):]
                driver.wait(timeout=60)
                tele = plant.call("/api/telemetry")
                live_states = plant.call("/api/faults")["drives"]  # przed zamknięciem LinuxCNC
                if plan["diagnostics"]:
                    (work / "telemetry.json").write_text(json.dumps(tele), encoding="utf-8")
            finally:
                if driver is not None and driver.poll() is None:
                    driver.kill()
                rip.stop_linuxcnc(cnc, root, ini.parent)
                plant.close()
                if capture is not None:
                    capture.join(timeout=5)
                    (work / "driver.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
                    (work / "plant.log").write_text("\n".join(plant.lines) + "\n", encoding="utf-8")
        if result_line is None:
            raise ScenarioError("skrypt LinuxCNC bez wyniku: " + " | ".join(lines[-8:]))
        out = json.loads(result_line)
        plant_report = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    for left in pending:
        res.criteria.append(Criterion(f"krok {left.action} wykonany", False,
                                      "nie wykonano przed końcem scenariusza"))
    plant_report["drive_states"] = live_states
    for _t, text in out.get("setup_errors", []):  # bazowanie przed T0: nie są alarmami
        res.log.append(f"{0:7.3f} s  LinuxCNC (przed T0): {text}")
    if out.get("codes"):
        res.log.append(f"{0:7.3f} s  603Fh z HAL: {out['codes']}")
    if out.get("hal_error"):
        res.log.append(f"{0:7.3f} s  odczyt HAL: {out['hal_error']}")
    _collect(res, out, plant_report, tele)
    if not out.get("machine_on") or not out.get("homed"):
        res.criteria.append(Criterion("LinuxCNC włączony i zbazowany", False,
                                      f"on={out.get('machine_on')} homed={out.get('homed')}"))
    evaluate(res)
    return res


def _timed(plant: _Plant, pending: list, res: ScenarioResult, t0: float) -> None:
    for st in [s for s in list(pending) if s.at_line is None]:
        delay = (st.at or 0.0) - (time.monotonic() - t0)
        if delay > 0:
            time.sleep(delay)
        if st in pending:
            pending.remove(st)
            _host_step(plant, st, res, time.monotonic() - t0)


def _collect(res: ScenarioResult, out: dict, plant: dict, tele: dict) -> None:
    letters = ("X", "Y", "Z")
    res.positions = {k: out["pos"][i] for i, k in enumerate(letters)}
    res.start_positions = {k: out["start"][i] for i, k in enumerate(letters)}
    res.ferr_max = {k: max(out["ferr"][j] for j in js) for k, js in JOINTS.items()}
    drives = list((plant.get("drive_states") or {}).keys())
    res.axis_drives = {k: [drives[j] for j in js if j < len(drives)] for k, js in JOINTS.items()}
    res.drive_states = dict(plant.get("drive_states") or {})
    for k, ds in res.axis_drives.items():
        if ds:
            res.drive_states[k] = res.drive_states.get(ds[0], "")
    res.lost_steps = {k: 0 for k in letters}  # serwa z mill_servo_table
    res.alarms = dict(out.get("alarms") or {})
    names = {1: "ESTOP", 2: "ESTOP_RESET", 3: "OFF", 4: "ON"}
    for t, task, interp in out.get("states", []):
        res.log.append(f"{t:7.3f} s  LinuxCNC: task {names.get(task, task)}, interp {interp}")
    for t, ok in out.get("resets", []):
        res.log.append(f"{t:7.3f} s  LinuxCNC: reset → {'ON' if ok else 'nie włączono'}")
    for t, text in out.get("errors", []):
        code = "E-4200" if "amplifier fault" in text.lower() else "E-1000"
        res.alarms.setdefault(code, t)
        res.log.append(f"{t:7.3f} s  LinuxCNC: {text}")
    if plant.get("watchdog_tripped"):
        res.alarms.setdefault("E-4003", 0.0)
    prog = out.get("program") or {}
    res.completed = bool(prog.get("done")) if prog.get("started") else True
    res.events = sorted(set(plant.get("machine_events") or []) |
                        {e.get("kind", "") for e in plant.get("events") or []})
    res.oracle = plant.get("oracle") or {}
    res.stats = {"frames": plant.get("frames", 0), "lost": plant.get("lost", 0),
                 "late": plant.get("late", 0), "digest": plant.get("digest", "")}
    res.telemetry = tele
    res.log.sort(key=lambda line: float(line.split()[0]))
