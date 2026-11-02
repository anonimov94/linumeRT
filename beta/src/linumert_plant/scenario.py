"""Scenariusze Plant: format, atrapa mastera i kryteria (sesja 024, REQ-QA-01…04).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 024.

Scenariusz (`plant/scenarios/*.yaml`, opis: docs/PLANT.md §7) to maszyna z `machine.yaml`,
opcjonalny program `.ngc`, oś czasu kroków i kryteria. Ten moduł wykonuje go z atrapą mastera
(LRT-NET bez gniazd, lockstep: czas tylko z ramek, deterministyczny — REQ-QA-04), tak jak
LinuxCNC widzi Plant: CiA 402, pozycje w impulsach, wejścia, flagi ramki. Ten sam scenariusz
z prawdziwym LinuxCNC uruchamia `tools/run_scenario.py --master linuxcnc`.

Atrapa interpretuje tylko ruch liniowy: G0/G1 (G90/G91, F [mm/min]), M3/M4/M5 S, M2/M30;
pozostałe kody modalne bez ruchu są pomijane, łuki i cykle → błąd (wymagają LinuxCNC).
Ruch skoordynowany: profil trapezowy po drodze z limitami prędkości i przyspieszenia osi.
Awaria napędu albo E-STOP przerywa program jak w LinuxCNC (alarm, ruch zatrzymany).
"""

from __future__ import annotations

import math
import platform
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .lrtnet import FLAG_ESTOP_OPEN, FLAG_FAULT
from .server import DEFAULT_SUBSTEPS

ROOT = Path(__file__).resolve().parents[2]
ACTIONS = ("enable", "home", "move", "mdi", "program", "wait", "fault", "clear", "set_param",
           "fault_reset", "spindle", "edit_machine", "reload", "capture")
CRITERIA = ("max_following_error", "lost_steps", "alarm", "no_alarm", "position",
            "drive_state", "event", "oracle", "completed", "frames", "machine", "reloaded",
            "probed", "probe_repeat", "probe_tripped")
# 603Fh → alarm katalogu (drive.h: LRT_DRIVE_FAULT_LIST)
ERROR_ALARMS = {0xFF00: "E-4200", 0x8611: "E-4201", 0x2350: "E-4202", 0x2310: "E-4203",
                0x4310: "E-4204", 0x3200: "E-4205", 0x7305: "E-4206", 0xFF01: "E-4207",
                0xFF02: "E-4208", 0xFF03: "E-4211", 0x8130: "E-4003"}
ESTOP_ALARM = "E-1100"
WORD = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


class ScenarioError(ValueError):
    """Błędny scenariusz albo program niewykonalny przez atrapę (komunikat po polsku)."""


@dataclass
class Step:
    action: str
    at: float | None = None  # [s] od startu
    at_line: int | None = None  # numer linii programu (atrapa: po rozpoczęciu tej linii)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    name: str
    path: Path | None
    machine: Path
    requirements: list[str] = field(default_factory=list)
    description: str = ""
    duration: float = 5.0
    seed: int = 1
    substeps: int = DEFAULT_SUBSTEPS
    cycle_ns: int = 1_000_000
    program: Path | None = None
    master: str = "mock"
    steps: list[Step] = field(default_factory=list)
    expect: list[dict[str, Any]] = field(default_factory=list)
    linuxcnc: dict[str, Any] = field(default_factory=dict)


def load_scenario(path: Path | str, machine: Path | None = None) -> Scenario:
    """Wczytuje i sprawdza scenariusz; ścieżki względne od katalogu pliku.

    `machine` zastępuje maszynę scenariusza (macierz maszyn, REQ-QA-02)."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ScenarioError(f"{path}: nie można wczytać ({exc})") from None
    if not isinstance(data, dict):
        raise ScenarioError(f"{path}: oczekiwano mapy")
    errors: list[str] = []
    known = {"name", "description", "requirements", "machine", "duration", "seed", "timing",
             "program", "master", "steps", "expect", "linuxcnc"}
    errors += [f"nieznane pole {k}" for k in sorted(set(data) - known)]
    base = path.parent

    def rel(value: Any) -> Path | None:
        return None if value in (None, "") else (base / str(value)).resolve()

    timing = data.get("timing") or {}
    scen = Scenario(name=str(data.get("name") or path.stem), path=path,
                    machine=machine or rel(data.get("machine")) or Path(),
                    requirements=[str(r) for r in data.get("requirements") or []],
                    description=str(data.get("description", "")),
                    duration=float(data.get("duration", 5.0)), seed=int(data.get("seed", 1)),
                    substeps=int(timing.get("substeps", DEFAULT_SUBSTEPS)),
                    cycle_ns=int(timing.get("cycle_ns", 1_000_000)),
                    program=rel(data.get("program")), master=str(data.get("master", "mock")),
                    linuxcnc=dict(data.get("linuxcnc") or {}))
    if not data.get("machine") and machine is None:
        errors.append("brak pola machine")
    elif not scen.machine.is_file():
        errors.append(f"machine: brak pliku {scen.machine}")
    if scen.program is not None and not scen.program.is_file():
        errors.append(f"program: brak pliku {scen.program}")
    if scen.master not in ("mock", "linuxcnc", "both"):
        errors.append(f"master: {scen.master!r} — dozwolone mock, linuxcnc, both")
    for r in scen.requirements:
        if not re.fullmatch(r"REQ-[A-Z]{2}-\d{2}", r):
            errors.append(f"requirements: {r!r} nie jest identyfikatorem REQ-XX-NN")
    if not 0 < scen.duration <= 600:
        errors.append(f"duration: {scen.duration} poza (0; 600] s")
    for i, raw in enumerate(data.get("steps") or []):
        if not isinstance(raw, dict) or raw.get("action") not in ACTIONS:
            errors.append(f"steps[{i}]: action — dozwolone {', '.join(ACTIONS)}")
            continue
        params = {k: v for k, v in raw.items() if k not in ("action", "at", "at_line")}
        step = Step(raw["action"], None if raw.get("at") is None else float(raw["at"]),
                    None if raw.get("at_line") is None else int(raw["at_line"]), params)
        if step.at is not None and step.at_line is not None:
            errors.append(f"steps[{i}]: at albo at_line, nie oba")
        if step.at_line is not None and scen.program is None:
            errors.append(f"steps[{i}]: at_line wymaga pola program")
        scen.steps.append(step)
    for i, crit in enumerate(data.get("expect") or []):
        if not isinstance(crit, dict) or len(crit) != 1 or next(iter(crit)) not in CRITERIA:
            errors.append(f"expect[{i}]: jedno kryterium z {', '.join(CRITERIA)}")
        else:
            scen.expect.append(crit)
    if not scen.expect:
        errors.append("expect: co najmniej jedno kryterium")
    if errors:
        raise ScenarioError(f"{path}: " + "; ".join(errors))
    return scen


# ---- program G-code dla atrapy -----------------------------------------------------------

@dataclass
class Block:
    line: int
    text: str
    motion: str | None = None  # G0 / G1
    target: dict[str, float] = field(default_factory=dict)  # współrzędne podane w bloku
    feed: float | None = None
    incremental: bool | None = None
    spindle: float | None = None  # [obr/min], znak = kierunek; 0 = stop
    end: bool = False


IGNORED_G = {"17", "21", "40", "49", "54", "64", "80", "94", "61"}


def parse_program(text: str) -> list[Block]:
    """Bloki programu (podzbiór LinuxCNC dla atrapy)."""
    blocks = []
    motion = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"\([^)]*\)", "", raw).split(";", 1)[0].strip().upper()
        if not line or line.startswith("%"):
            continue
        block = Block(n, raw.strip())
        words = WORD.findall(line)
        s_word = next((float(v) for k, v in words if k == "S"), None)
        for k, v in words:
            num = v.lstrip("+")
            code = num.rstrip("0").rstrip(".") if "." in num else str(int(float(num)))
            if k == "G":
                if code in ("0", "1"):
                    motion = block.motion = f"G{code}"
                elif code in ("90", "91"):
                    block.incremental = code == "91"
                elif code not in IGNORED_G:
                    raise ScenarioError(f"linia {n}: G{code} nieobsługiwane przez atrapę "
                                        "mastera (uruchom scenariusz z LinuxCNC)")
            elif k == "M":
                if code in ("2", "30"):
                    block.end = True
                elif code in ("3", "4"):
                    block.spindle = (s_word or 0.0) * (1 if code == "3" else -1)
                elif code == "5":
                    block.spindle = 0.0
            elif k == "F":
                block.feed = float(v)
            elif k in "XYZABC":
                block.target[k] = float(v)
            elif k not in ("N", "S", "T"):
                raise ScenarioError(f"linia {n}: słowo {k} nieobsługiwane przez atrapę")
        if block.target and block.motion is None:
            if motion is None:
                raise ScenarioError(f"linia {n}: ruch bez G0/G1")
            block.motion = motion
        blocks.append(block)
    return blocks


# ---- wynik --------------------------------------------------------------------------------

@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str


@dataclass
class ScenarioResult:
    scenario: Scenario
    master: str
    criteria: list[Criterion] = field(default_factory=list)
    alarms: dict[str, float] = field(default_factory=dict)  # kod → pierwszy czas [s]
    events: list[str] = field(default_factory=list)
    positions: dict[str, float] = field(default_factory=dict)
    axis_drives: dict[str, list[str]] = field(default_factory=dict)
    start_positions: dict[str, float] = field(default_factory=dict)  # przy pierwszym ruchu
    ferr_max: dict[str, float] = field(default_factory=dict)  # oś → maks. |błąd| [mm]
    lost_steps: dict[str, int] = field(default_factory=dict)
    completed: bool = False
    drive_states: dict[str, str] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    oracle: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    machine_data: dict[str, Any] = field(default_factory=dict)  # machine.yaml na końcu przebiegu
    reloads: int = 0
    # Zrzuty sondowania (akcja `capture`, tylko master linuxcnc): nazwa → {tripped, pos: X Y Z}
    probes: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return bool(self.criteria) and all(c.passed for c in self.criteria)


def versions() -> dict[str, str]:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        sha = ""
    return {"linumeRT": sha or "nieznana", "python": platform.python_version(),
            "system": platform.system()}


def evaluate(result: ScenarioResult) -> None:
    """Kryteria scenariusza na zebranym wyniku (wspólne dla atrapy i LinuxCNC)."""
    res = result
    for crit in res.scenario.expect:
        (kind, arg), = crit.items()
        arg = arg if isinstance(arg, dict) else {"value": arg}
        axis = str(arg.get("axis", "")).upper()
        if kind == "max_following_error":
            got = res.ferr_max.get(axis)
            ok = got is not None and got <= float(arg["mm"])
            res.criteria.append(Criterion(f"błąd nadążania {axis} ≤ {arg['mm']} mm", ok,
                                          f"maks. {got if got is None else round(got, 4)} mm"))
        elif kind == "lost_steps":
            got = res.lost_steps.get(axis, 0)
            ok = got <= int(arg.get("max", 1 << 30)) and got >= int(arg.get("min", 0))
            want = (f"≥ {arg['min']}" if "min" in arg else "") + \
                   (f" ≤ {arg['max']}" if "max" in arg else "")
            res.criteria.append(Criterion(f"zgubione kroki {axis} {want.strip()}", ok,
                                          f"{got} kroków"))
        elif kind == "alarm":
            code = str(arg["value"] if "value" in arg else arg["code"])
            within = arg.get("within_s")
            t = res.alarms.get(code)
            ok = t is not None and (within is None or t <= float(within))
            res.criteria.append(Criterion(f"alarm {code}" + (f" do {within} s" if within else ""),
                                          ok, f"t = {t:.3f} s" if t is not None else "brak"))
        elif kind == "no_alarm":
            allowed = set(arg.get("allowed", []))
            extra = sorted(set(res.alarms) - allowed)
            res.criteria.append(Criterion("brak alarmów" + (f" poza {sorted(allowed)}"
                                                            if allowed else ""),
                                          not extra, ", ".join(extra) or "brak"))
        elif kind == "position":
            got = res.positions.get(axis)
            relative = bool(arg.get("relative"))
            if relative and got is not None:  # względem pozycji przy pierwszym ruchu
                got -= res.start_positions.get(axis, 0.0)
            ok = got is not None and abs(got - float(arg["value"])) <= float(arg.get("tol", 0.01))
            res.criteria.append(Criterion(f"pozycja {axis} {'względna ' if relative else ''}= "
                                          f"{arg['value']} ± {arg.get('tol', 0.01)}", ok,
                                          f"{got if got is None else round(got, 4)}"))
        elif kind == "drive_state":
            target = str(arg.get("drive") or axis)
            got = res.drive_states.get(target)
            res.criteria.append(Criterion(f"stan napędu {target} = {arg['is']}",
                                          got == arg["is"], str(got)))
        elif kind == "event":
            present = arg.get("present", True)
            got = arg["name"] in res.events
            res.criteria.append(Criterion(f"zdarzenie {arg['name']} "
                                          f"{'wystąpiło' if present else 'nie wystąpiło'}",
                                          got == present, ", ".join(res.events) or "brak"))
        elif kind == "oracle":
            got = res.oracle.get("result", "brak")
            res.criteria.append(Criterion(f"wyrocznia {arg['value']}",
                                          got == str(arg["value"]).upper(), str(got)))
        elif kind == "completed":
            want = bool(arg["value"])
            res.criteria.append(Criterion("program ukończony" if want else "program przerwany",
                                          res.completed == want,
                                          "ukończony" if res.completed else "przerwany"))
        elif kind == "machine":
            from .panel.editor import get_path

            try:
                got = get_path(res.machine_data, arg["path"])
            except (KeyError, IndexError, ValueError, TypeError):
                got = None
            res.criteria.append(Criterion(f"machine.yaml {arg['path']} = {arg['value']}",
                                          got == arg["value"], str(got)))
        elif kind == "reloaded":
            want = int(arg.get("count", arg.get("value", 1)))
            res.criteria.append(Criterion(f"przeładowania modelu = {want}", res.reloads == want,
                                          str(res.reloads)))
        elif kind == "frames":
            lost = res.stats.get("lost", 0)
            ok = lost <= int(arg.get("lost_max", 0))
            res.criteria.append(Criterion(f"utracone ramki ≤ {arg.get('lost_max', 0)}", ok,
                                          str(lost)))
        elif kind in ("probed", "probe_repeat", "probe_tripped"):
            _evaluate_probe(res, kind, arg, axis)


def _probe_axis_value(res: ScenarioResult, name: str, axis: str) -> float | None:
    """Pozycja osi w chwili zadziałania sondy w zrzucie `name`; None gdy brak zrzutu albo
    sonda nie zadziałała (pozycja sprzed próby nie jest wynikiem pomiaru)."""
    shot = res.probes.get(name)
    if not shot or not shot.get("tripped") or axis not in "XYZ" or len(axis) != 1:
        return None
    return float(shot["pos"]["XYZ".index(axis)])


def _evaluate_probe(res: ScenarioResult, kind: str, arg: dict[str, Any], axis: str) -> None:
    """Kryteria sondowania (sesja 033): wartości z `probed_position` LinuxCNC po G38.x."""
    if kind == "probe_tripped":
        name, want = str(arg["capture"]), bool(arg.get("value", True))
        shot = res.probes.get(name)
        got = None if shot is None else bool(shot.get("tripped"))
        res.criteria.append(Criterion(f"sonda {name} {'zadziałała' if want else 'nie zadziałała'}",
                                      got == want, "brak zrzutu" if got is None else str(got)))
    elif kind == "probe_repeat":
        names = [str(n) for n in arg["captures"]]
        tol = float(arg.get("tol", 0.002))
        values = [_probe_axis_value(res, n, axis) for n in names]
        ok = None not in values and max(values) - min(values) <= tol  # type: ignore[type-var]
        detail = "brak pomiaru" if None in values else \
            f"rozrzut {max(values) - min(values):.4f} mm"  # type: ignore[type-var]
        res.criteria.append(Criterion(f"powtarzalność {axis} ({', '.join(names)}) ≤ {tol} mm",
                                      ok, detail))
    else:
        name, tol = str(arg["capture"]), float(arg.get("tol", 0.01))
        got = _probe_axis_value(res, name, axis)
        label = f"sonda {axis} {name} = {arg['value']} ± {tol}"
        cal = arg.get("calibrate")
        if cal is not None and got is not None:
            ref = _probe_axis_value(res, str(cal["capture"]), axis)
            if ref is None:
                got = None
            else:  # stała poprawka z wzorca (jak core/linumert/programs/probe_calibration.py)
                got -= ref - float(cal["value"])
                label += f" po kalibracji na {cal['capture']}"
        ok = got is not None and abs(got - float(arg["value"])) <= tol
        res.criteria.append(Criterion(label, ok,
                                      "brak pomiaru" if got is None else
                                      f"{got:.4f} (błąd {got - float(arg['value']):+.4f} mm)"))


# ---- atrapa mastera -----------------------------------------------------------------------

def _trapezoid_s(dist: float, vmax: float, amax: float, dt: float) -> list[float]:
    """Droga od startu w kolejnych cyklach (profil trapezowy albo trójkątny)."""
    if dist <= 0:
        return []
    t_acc = vmax / amax
    if amax * t_acc * t_acc > dist:
        t_acc = math.sqrt(dist / amax)
        vmax = amax * t_acc
    t_flat = (dist - amax * t_acc * t_acc) / vmax
    total = 2 * t_acc + t_flat
    out = []
    for i in range(1, max(1, math.ceil(total / dt)) + 1):
        t = min(i * dt, total)
        if t < t_acc:
            s = 0.5 * amax * t * t
        elif t < t_acc + t_flat:
            s = 0.5 * amax * t_acc * t_acc + vmax * (t - t_acc)
        else:
            s = dist - 0.5 * amax * (total - t) ** 2
        out.append(s)
    return out


class MockRun:
    """Wykonanie scenariusza z atrapą mastera na serwerze Plant w tym samym procesie."""

    def __init__(self, scen: Scenario):
        from test_master import Master

        from .build_machine import build_model
        from .core_binding import PlantMachine
        from .machine_drives import load_machine_drives
        from .panel.telemetry import Telemetry
        from .server import PlantConfig, PlantServer

        self.scen = scen
        self.workdir = None
        machine_path = scen.machine
        if any(s.action in ("edit_machine", "reload") for s in scen.steps):
            import shutil
            import tempfile

            # edycja na kopii: plik scenariusza i maszyny w repozytorium się nie zmienia
            self.workdir = Path(tempfile.mkdtemp(prefix="lrt_edit_"))
            machine_path = self.workdir / scen.machine.name
            shutil.copy(scen.machine, machine_path)
        self.machine_path = machine_path
        mcfg, drives = load_machine_drives(machine_path)
        self.cfg = mcfg
        machine = PlantMachine(build_model(mcfg, drives, seed=scen.seed))
        self.server = PlantServer(machine, PlantConfig(seed=scen.seed, substeps=scen.substeps,
                                                       cycle_ns=scen.cycle_ns,
                                                       machine=machine_path),
                                  drive_params={n: i.params for n, i in drives.items()})
        self.server.telemetry = Telemetry(self.server.drives, window_s=scen.duration + 2.0,
                                          period_s=0.005)
        self.master = Master(len(self.server.drives), transport=self.server.handle,
                             cycle_ns=scen.cycle_ns)
        self.dt = scen.cycle_ns / 1e9
        model = machine.model
        self.axes = {a.letter: a for a in mcfg.axes}
        self.idx = {d: i for i, d in enumerate(self.server.drives)}
        self.scale = model.counts_per_unit
        self.zero = {d: 0 for d in self.server.drives}
        self.joint_drives = {k: [d for d in v if d in self.idx]
                             for k, v in model.joint_drives.items()}
        self.result = ScenarioResult(scen, "mock", versions=versions())
        self.t = 0.0
        self.segment: tuple[dict[str, float], dict[str, float], list[float]] | None = None
        self.seg_i = 0
        self.blocks: list[Block] = []
        self.block_i = 0
        self.program_running = False
        self.aborted = False
        self.incremental = False
        self.feed = 1000.0
        self.line = 0
        self.enabled = False

    # ---- pozycje mastera --------------------------------------------------------------
    def position(self, letter: str) -> float:
        drives = self.joint_drives[letter]
        last = self.master.last
        vals = [(last.axes[self.idx[d]].actual_pos - self.zero[d]) / self.scale[d]
                for d in drives]
        return sum(vals) / len(vals)

    def command(self, letter: str) -> float:
        d = self.joint_drives[letter][0]
        return (self.master.axes[self.idx[d]].target_pos - self.zero[d]) / self.scale[d]

    def _set(self, letter: str, value: float) -> None:
        for d in self.joint_drives[letter]:
            self.master.axes[self.idx[d]].target_pos = self.zero[d] + round(value * self.scale[d])

    # ---- ruch ---------------------------------------------------------------------------
    def start_move(self, target: dict[str, float], rapid: bool, feed: float | None,
                   accel: float | None = None) -> None:
        """Ruch skoordynowany; `accel` [mm/s²] po drodze pomija limity osi (zła konfiguracja
        INI w scenariuszu, np. za duże przyspieszenie krokowca)."""
        start = {k: self.command(k) for k in target}
        delta = {k: target[k] - start[k] for k in target}
        length = math.sqrt(sum(d * d for d in delta.values()))
        if length < 1e-9:
            return
        vmax = math.inf if rapid else (feed or self.feed) / 60.0
        amax = math.inf
        for k, d in delta.items():
            if abs(d) < 1e-12:
                continue
            axis = self.axes[k]
            vmax = min(vmax, axis.max_velocity * length / abs(d))
            amax = min(amax, axis.max_acceleration * length / abs(d))
        if accel is not None:
            amax = float(accel)
            vmax = (feed or self.feed) / 60.0
        profile = [s / length for s in _trapezoid_s(length, vmax, amax, self.dt)]
        self.segment = (start, delta, profile)
        self.seg_i = 0

    def _advance_motion(self) -> None:
        if self.segment is None:
            return
        start, delta, profile = self.segment
        frac = profile[self.seg_i]
        for k in start:
            self._set(k, start[k] + delta[k] * frac)
        self.seg_i += 1
        if self.seg_i >= len(profile):
            self.segment = None

    def _next_block(self) -> None:
        while self.program_running and self.segment is None:
            if self.block_i >= len(self.blocks):
                self.program_running = False
                self.result.completed = not self.aborted
                return
            block = self.blocks[self.block_i]
            self.block_i += 1
            self.line = block.line
            self._fire_line(block.line)
            self.exec_block(block)
            if block.end:
                self.program_running = False
                self.result.completed = not self.aborted
                return

    def exec_block(self, block: Block) -> None:
        if block.incremental is not None:
            self.incremental = block.incremental
        if block.feed is not None:
            self.feed = block.feed
        if block.spindle is not None:
            self.master.spindle_cmd = block.spindle
        if block.target:
            unknown = sorted(set(block.target) - set(self.joint_drives))
            if unknown:
                raise ScenarioError(f"linia {block.line}: maszyna nie ma osi {', '.join(unknown)}")
            target = {k: (self.command(k) + v if self.incremental else v)
                      for k, v in block.target.items()}
            self.start_move(target, block.motion == "G0", block.feed)

    # ---- kroki ------------------------------------------------------------------------
    def _fire_line(self, line: int) -> None:
        for step in [s for s in self.pending if s.at_line is not None and s.at_line <= line]:
            self.pending.remove(step)
            self.do(step)

    def do(self, step: Step) -> None:
        """Wykonuje krok; błąd danych kroku (np. zdjęcie nieaktywnej awarii) = kryterium FAIL."""
        from .drive_template import TemplateError
        from .faults import FaultError
        from .homing_master import HomingError

        try:
            self._do(step)
        except (FaultError, TemplateError, HomingError, KeyError, ValueError) as exc:
            if isinstance(exc, ScenarioError):
                raise
            text = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
            self.result.criteria.append(Criterion(f"krok {step.action} ({self.t:.3f} s)",
                                                  False, str(text)))

    def _do(self, step: Step) -> None:
        p = step.params
        a = step.action
        if a in ("move", "mdi", "program") and not self.result.start_positions:
            self.result.start_positions = {k: round(self.position(k), 4)
                                           for k, d in self.joint_drives.items() if d}
        self.result.log.append(f"{self.t:7.3f} s  {a} {p if p else ''}".rstrip())
        srv = self.server
        if a == "enable":
            self.master.enable()
            self.enabled = True
            # bez bazowania: położenie przy włączeniu = 0 (jak niezbazowany LinuxCNC)
            self.zero = {d: self.master.last.axes[i].actual_pos for d, i in self.idx.items()}
        elif a == "home":
            self.home(p.get("axes"))
        elif a == "move":
            target = {str(k).upper(): float(v) for k, v in p.items() if k.upper() in "XYZABC"}
            self.start_move(target, bool(p.get("rapid")), p.get("feed"), p.get("accel"))
        elif a == "mdi":
            for block in parse_program(str(p["command"])):
                self.exec_block(block)
        elif a == "program":
            self.run_program()
        elif a == "fault":
            params = {k: v for k, v in p.items() if k != "fault"}
            srv.faults.inject(p["fault"], **params)
        elif a == "clear":
            params = {k: v for k, v in p.items() if k != "fault"}
            srv.faults.clear(p["fault"], **params)
        elif a == "set_param":
            srv.set_live(p["drive"], p["path"], p["value"])
        elif a == "fault_reset":
            self.master.enable()
            self.aborted = False
        elif a == "spindle":
            self.master.spindle_cmd = float(p.get("rpm", 0))
        elif a == "wait":
            self.waiting = step
        elif a == "edit_machine":
            self._edit(p.get("set") or {}, str(p.get("comment", "")))
        elif a == "reload":
            from .panel.editor import MachineEditor

            MachineEditor(srv, self.workdir / "state").reload()
            self.result.reloads += 1
            model = srv.machine.model
            self.cfg = model.config
            self.axes = {ax.letter: ax for ax in self.cfg.axes}
            self.scale = model.counts_per_unit

    def _edit(self, changes: dict[str, Any], comment: str) -> None:
        """Zapis machine.yaml przez edytor panelu (walidacja REQ-VM-11, historia wersji)."""
        from .panel.editor import EditorError, MachineEditor, set_path

        editor = MachineEditor(self.server, self.workdir / "state")
        data = editor.load()
        for path, value in changes.items():
            set_path(data, path, value)
        try:
            editor.save(data, comment)
        except EditorError as exc:
            raise ValueError("edycja odrzucona: " + "; ".join(exc.errors)) from None

    def run_program(self) -> None:
        if self.scen.program is None:
            raise ScenarioError("akcja program bez pola program")
        self.blocks = parse_program(self.scen.program.read_text(encoding="utf-8"))
        self.block_i = 0
        self.program_running = True
        self.result.completed = False

    def home(self, axes: list[str] | None) -> None:
        from .homing_master import HomingMaster

        homer = HomingMaster(self.server.machine)
        letters = [str(a).upper() for a in axes] if axes else None
        with self.server._lock:
            if letters is None:
                results = homer.home_all()
            else:
                results = {k: homer.home_axis(k) for k in letters}
        for res in results.values():
            for d, r in res.drives.items():
                if d in self.zero:
                    self.zero[d] = r.zero_counts
        for d, i in self.idx.items():  # cele = pozycja po bazowaniu (nie z ramki sprzed niej)
            self.master.axes[i].target_pos = self.server.machine.position_actual(d)
        self._exchange()

    def _exchange(self) -> None:
        """Ramka mastera; brak odpowiedzi (awaria frame_loss) — master idzie dalej jak servo."""
        from test_master import MasterError

        try:
            self.master.exchange()
        except MasterError:
            self.master.seq = (self.master.seq + 1) & 0xFFFFFFFF
            self.master.time_ns += self.master.cycle_ns

    def _wait_done(self, step: Step) -> bool:
        p = step.params
        until = p.get("until")
        if until is None:
            return self.t >= self.wait_start + float(p.get("seconds", 0))
        if "idle" in until:
            return self.segment is None and not self.program_running
        if "alarm" in until:
            return str(until["alarm"]) in self.result.alarms
        if "drive_state" in until:
            cond = until["drive_state"]
            drive = cond.get("drive") or self.joint_drives[str(cond["axis"]).upper()][0]
            return self.master.states()[self.idx[drive]] == cond["is"]
        raise ScenarioError(f"wait.until: nieznany warunek {until}")

    # ---- pętla ---------------------------------------------------------------------------
    def _observe(self) -> None:
        last = self.master.last
        for axis_rep in last.axes:
            code = ERROR_ALARMS.get(axis_rep.error_code)
            if code and code not in self.result.alarms:
                self.result.alarms[code] = round(self.t, 4)
        if last.flags & FLAG_ESTOP_OPEN and ESTOP_ALARM not in self.result.alarms:
            self.result.alarms[ESTOP_ALARM] = round(self.t, 4)
        if (last.flags & (FLAG_FAULT | FLAG_ESTOP_OPEN)) and self.enabled and \
                (self.segment is not None or self.program_running):
            self.segment = None  # LinuxCNC: awaria napędu / E-STOP przerywa ruch i program
            self.program_running = False
            self.aborted = True
            self.result.log.append(f"{self.t:7.3f} s  ruch przerwany (awaria/E-STOP)")

    def run(self) -> ScenarioResult:
        scen = self.scen
        self.pending = [s for s in scen.steps]
        self.waiting: Step | None = None
        self.wait_start = 0.0
        frames = round(scen.duration / self.dt)
        self.master.exchange()
        timed = [s for s in self.pending if s.at_line is None]
        for k in range(frames):
            self.t = k * self.dt
            if self.waiting is not None:
                if self._wait_done(self.waiting):
                    self.waiting = None
                elif self.t > self.wait_start + float(self.waiting.params.get("timeout", 5.0)):
                    self.result.criteria.append(Criterion(
                        f"oczekiwanie {self.waiting.params}", False, "przekroczony czas"))
                    self.waiting = None
            while self.waiting is None and timed and (timed[0].at or 0.0) <= self.t + 1e-9:
                step = timed.pop(0)
                self.pending.remove(step)
                self.do(step)
                if step.action == "wait":
                    self.wait_start = self.t
            self._next_block()
            self._advance_motion()
            self._exchange()
            self._observe()
        return self.finish()

    def finish(self) -> ScenarioResult:
        res = self.result
        srv = self.server
        for leftover in self.pending:
            res.criteria.append(Criterion(f"krok {leftover.action} wykonany", False,
                                          "nie wykonano przed końcem scenariusza"))
        if not self.scen.program and not self.aborted:
            res.completed = self.segment is None
        tele = srv.telemetry.columns()
        res.telemetry = tele
        for letter, drives in self.joint_drives.items():
            if not drives:
                continue
            res.positions[letter] = round(self.position(letter), 4)
            res.axis_drives[letter] = list(drives)
            ferr = [abs(v) for d in drives for v in tele["drives"][d]["ferr"]]
            res.ferr_max[letter] = max(ferr) if ferr else 0.0
            res.lost_steps[letter] = max(int(srv.machine.lost_steps(d)) for d in drives)
            for d in drives:
                res.drive_states[d] = self.master.states()[self.idx[d]]
            res.drive_states[letter] = res.drive_states[drives[0]]
        res.events = sorted(srv.machine.events() | {e.kind for e in srv.events})
        s = srv.stats
        res.stats = {"frames": s.received, "lost": s.lost, "late": s.late,
                     "dropped": srv.fault_state.dropped, "digest": srv.digest,
                     "time_s": round(self.t + self.dt, 4)}
        res.oracle = srv.oracle.report()
        res.machine_data = yaml.safe_load(self.machine_path.read_text(encoding="utf-8")) or {}
        evaluate(res)
        return res


def run_mock(scen: Scenario) -> ScenarioResult:
    return MockRun(scen).run()
