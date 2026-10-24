"""Generator konfiguracji LinuxCNC z machine.yaml: INI i HAL (sesja 062, krok 2).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

Jedno źródło prawdy (REQ-VM-01): osie, zakresy, bazowanie, krańcówki, wejścia/wyjścia i skala
napędów pochodzą z `machine.yaml` i szablonów napędów; generator nie przyjmuje drugiej kopii
tych liczb. Wyjścia (`render(cfg, target)` → {nazwa pliku: treść}):

- `plant` — LinuxCNC + wirtualna obrabiarka przez `lrt_net` (wzorzec:
  config/plant/linumert_plant_xyz, sprawdzony w LinuxCNC; test golden porównuje wynik z nim),
- `sim` — LinuxCNC sim: napędy jako idealne nadążanie, czujniki bazy z porównania pozycji,
- `hardware` — step/dir: port równoległy albo Mesa 7i96S/7i76E (`configgen_hw.py`, z kontraktem
  bezpieczeństwa; odmawia bez pinu E-STOP).

Kontrakt sygnałów D05 (`linumert.jN.*`, `linumert.spindle.*`, `linumert.io.*`) jest ten sam
dla każdego wyjścia; zmienia się tylko blok „napędy” i źródło wejść. DISPLAY = ekran linumert.
Jointy = napędy osi w kolejności `drives:` bez wrzeciona (ramka LRT-NET, `joint_drives`).
Zapis z kopią zapasową i diffem: `config_build.py` (CLI). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schema import Axis, MachineConfig

TARGETS = ("plant", "sim", "hardware")
HOME_INSET = 4.0          # [mm|°] HOME: tyle do środka od programowej granicy po stronie bazy
FERROR, MIN_FERROR = 2.0, 0.5


@dataclass
class Joint:
    index: int
    axis: Axis
    drive: str
    scale: float
    gantry: bool          # oś ma dwa napędy (bazowane synchronicznie)
    first: int            # pierwszy joint tej osi (nazwa sieci linumert.jN.*)


@dataclass
class Options:
    """Ścieżki względne katalogu konfiguracji (domyślnie: config/<cel>/<maszyna>/)."""

    ip: str = "127.0.0.1"
    port: int = 47700
    hal_dir: str = "../../hal"
    program_prefix: str = "../../sim/nc_files"
    tool_table: str = "../../sim/linumert_xyz/tool.tbl"
    postgui: str = "../../sim/linumert_xyz/linumert_postgui.hal"
    subroutine_path: str = "macros"
    extra: dict[str, Any] = field(default_factory=dict)


def joint_drives(cfg: MachineConfig) -> list[tuple[Axis, str]]:
    owner = {name: axis for axis in cfg.axes for name in axis.drives}
    return [(owner[d.name], d.name) for d in cfg.drives if d.name in owner]


def plant_scales(cfg: MachineConfig) -> dict[str, float]:
    """Impulsy na mm/° napędów z modelu Plant (ten sam rachunek co wirtualna obrabiarka)."""
    # plant/server na PYTHONPATH; rozwiązanie napędów z biblioteki szablonów (REQ-VD-02)
    from linumert_plant.build_machine import build_model
    from linumert_plant.drive_library import load_library
    from linumert_plant.machine_drives import resolve_machine_drives

    drives = resolve_machine_drives(cfg, load_library())
    return dict(build_model(cfg, drives).counts_per_unit)


def joints(cfg: MachineConfig, scales: dict[str, float]) -> list[Joint]:
    out: list[Joint] = []
    first: dict[str, int] = {}
    for index, (axis, name) in enumerate(joint_drives(cfg)):
        first.setdefault(axis.letter, index)
        out.append(Joint(index, axis, name, scales.get(name, 1.0), len(axis.drives) > 1,
                         first[axis.letter]))
    return out


# --------------------------------------------------------------------------- wartości

def _f(value: float) -> str:
    return str(float(value))


def _g(value: float) -> str:
    return f"{float(value):g}"


def home_side(axis: Axis) -> str:
    return "min" if axis.homing.direction < 0 else "max"


def home_position(axis: Axis) -> float:
    lo, hi = axis.soft_limits
    return lo + HOME_INSET if home_side(axis) == "min" else hi - HOME_INSET


def home_offset(axis: Axis) -> float:
    """Pozycja czujnika bazy: współdzielona krańcówka albo własny czujnik."""
    sensor = axis.home_sensor
    if sensor is not None and sensor.shared_with:
        switch = getattr(axis.limits, "min" if sensor.shared_with == "limit_min" else "max")
        if switch is not None:
            return switch.position
    if sensor is not None and sensor.position is not None:
        return sensor.position
    lo, hi = axis.travel
    return lo if home_side(axis) == "min" else hi


def _joint_section(j: Joint, target: str) -> list[str]:
    a, h = j.axis, j.axis.homing
    latch = 1 if h.latch == "approach" else -1
    shared = a.home_sensor is not None and a.home_sensor.shared_with is not None
    # Indeks: LRT-NET v1 (Plant) go nie przenosi (DECYZJE, sesja 017), sim i stepgen go nie mają;
    # bazowanie na indeksie enkodera wróci z napędami EtherCAT (063).
    use_index = False
    sequence = -h.order if j.gantry and h.order > 0 else h.order
    lines = [f"[JOINT_{j.index}]", f"AXIS = {a.letter}",
             f"TYPE = {'ANGULAR' if a.rotary else 'LINEAR'}"]
    if target in ("plant", "hardware"):
        lines.append(f"SCALE = {j.scale:.6f}")
    if target == "hardware":
        lines.append(f"STEPGEN_MAXACCEL = {_f(round(a.max_acceleration * 1.25, 3))}")
    lines += [
        f"MIN_LIMIT = {_f(a.travel[0])}", f"MAX_LIMIT = {_f(a.travel[1])}",
        f"MAX_VELOCITY = {_f(a.max_velocity)}", f"MAX_ACCELERATION = {_f(a.max_acceleration)}",
        f"FERROR = {FERROR}", f"MIN_FERROR = {MIN_FERROR}",
        f"HOME_SEARCH_VEL = {_f(h.direction * h.search_speed)}",
        f"HOME_LATCH_VEL = {_f(latch * h.direction * h.latch_speed)}",
        f"HOME_OFFSET = {_f(home_offset(a))}", f"HOME = {_f(home_position(a))}",
        f"HOME_SEQUENCE = {sequence}", f"HOME_USE_INDEX = {'YES' if use_index else 'NO'}",
        f"HOME_IGNORE_LIMITS = {'YES' if shared else 'NO'}", "",
    ]
    return lines


def render_ini(cfg: MachineConfig, js: list[Joint], target: str, opt: Options,
               extra: dict[str, list[str]] | None = None) -> str:
    coords = "".join(j.axis.letter for j in js)
    duplicated = len(set(coords)) != len(coords)
    vmax = max(a.max_velocity for a in cfg.axes if not a.rotary)
    sp = cfg.spindle
    xs = {a.letter: a for a in cfg.axes}
    safe_z = cfg.positions.safe_z
    centre = " ".join(f"{k}{_g((xs[k].travel[0] + xs[k].travel[1]) / 2)}" for k in "XY" if k in xs)
    home = " ".join(f"{k}{_g(home_position(xs[k]))}" for k in "XY" if k in xs)
    title = {"plant": "Plant", "sim": "sim", "hardware": "maszyna"}[target]
    hw = cfg.hardware
    # Wątek bazowy tylko dla programowego stepgen na porcie równoległym.
    parport = target == "hardware" and hw is not None and hw.interface == "parport"
    base_period = hw.base_period_ns if parport else 0
    kins = f"trivkins coordinates={coords}" + (" kinstype=BOTH" if duplicated else "")
    out = [
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        f"# linumeRT · konfiguracja z machine.yaml ({cfg.machine.name}), cel: {target}.",
        "# Nie edytuj ręcznie: zmień machine.yaml i uruchom",
        "# `python -m linumert.machine.config_build`. Jointy = napędy osi w kolejności drives:",
        "# bez wrzeciona. Kontrakt sygnałów: docs/HAL_KONTRAKT.md.",
        "# Model-Author: Claude · generator sesji 062. NIEZWERYFIKOWANE NA SPRZĘCIE.",
        "",
        "[EMC]", "VERSION = 1.1", f"MACHINE = linumeRT {title} {cfg.machine.name}",
        "DEBUG = 0x00000000", "",
        "[DISPLAY]", "DISPLAY = qtvcp linumert", f"TITLE = linumeRT {title} {coords}",
        "PREFERENCE_FILE_PATH = WORKINGFOLDER/linumert.pref",
        "MAX_FEED_OVERRIDE = 1.2", "MIN_SPINDLE_0_OVERRIDE = 0.5", "MAX_SPINDLE_0_OVERRIDE = 1.2",
        f"DEFAULT_SPINDLE_0_SPEED = {_g(round(sp.max_rpm * 0.75))}",
        "SPINDLE_INCREMENT = 200",
        f"MIN_SPINDLE_0_SPEED = {_g(sp.min_rpm)}", f"MAX_SPINDLE_0_SPEED = {_g(sp.max_rpm)}",
        "MAX_SPINDLE_POWER = 2200",
        "MIN_LINEAR_VELOCITY = 0", f"MAX_LINEAR_VELOCITY = {_f(vmax)}",
        f"DEFAULT_LINEAR_VELOCITY = {_f(vmax / 4)}",
        "INCREMENTS = 10 mm, 1.0 mm, 0.10 mm, 0.01 mm", "CYCLE_TIME = 100",
        f"PROGRAM_PREFIX = {opt.program_prefix}", "MDI_HISTORY_FILE = mdi_history.dat",
        "LOG_FILE = linumert.log", "",
        "[MDI_COMMAND_LIST]",
        f"MDI_COMMAND = G53 G0 Z{_g(safe_z)};G53 G0 {centre}, Goto\\nCenter",
        f"MDI_COMMAND = G53 G0 Z{_g(safe_z)};G53 G0 {home},Goto\\nHome", "",
        "[FILTER]", "PROGRAM_EXTENSION = .ngc,.nc,.tap G-Code File (*.ngc,*.nc,*.tap)", "",
    ]
    if target == "plant":
        out += ["[PLANT]", f"IP = {opt.ip}", f"PORT = {opt.port}", f"AXES = {len(js)}", ""]
    out += ["[KINS]", f"KINEMATICS = {kins}", f"JOINTS = {len(js)}", "",
            "[LINUMERT]", f"MACHINE_PROFILE = {target}"]
    if target == "sim":
        out.append("VIRTUAL_MODE = 1")
    if target == "hardware":
        out.append("VIRTUAL_MODE = 0")
    out += ["HMI_HEARTBEAT_TIMEOUT = 2.0", "HMI_ESTOP_BYPASS = 0", ""]
    for section, lines in (extra or {}).items():
        out += [f"[{section}]", *lines, ""]
    out += [
        "[EMCIO]", "EMCIO = io", "CYCLE_TIME = 0.100", f"TOOL_TABLE = {opt.tool_table}", "",
        "[RS274NGC]", "PARAMETER_FILE = linumert.var",
        "RS274NGC_STARTUP_CODE = G17 G21 G40 G43H0 G54 G64P0.01 G80 G90 G94 G97 M5 M9",
        f"SUBROUTINE_PATH = {opt.subroutine_path}", "REMAP = M6 modalgroup=6 ngc=lrt_m6", "",
        "[EMCMOT]", "EMCMOT = motmod", "SERVO_PERIOD = 1000000", "COMM_TIMEOUT = 1.0",
        f"BASE_PERIOD = {base_period}",
        "",
        "[TASK]", "TASK = milltask", "CYCLE_TIME = 0.010", "",
        "[TRAJ]", f"COORDINATES = {coords}", "LINEAR_UNITS = mm", "ANGULAR_UNITS = degree",
        f"MAX_LINEAR_VELOCITY = {_f(vmax)}", f"DEFAULT_LINEAR_VELOCITY = {_f(vmax / 4)}",
        "SPINDLES = 1", "",
        "[HAL]", "HALUI = halui",
    ]
    if target == "plant":
        out += ["HALFILE = linumert_plant.hal", "HALFILE = spindle_sim.hal"]
    elif target == "hardware":
        out += ["HALFILE = linumert_hw.hal", "HALFILE = spindle_vfd.hal"]
    else:
        out += ["HALFILE = linumert_sim.hal"]
    out += [f"HALFILE = {opt.hal_dir}/linumert_hmi_estop.hal",
            f"HALFILE = {opt.hal_dir}/linumert_pause_retract.hal"]
    if target == "hardware":
        out.append("POSTGUI_HALFILE = linumert_hw_postgui.hal")
    elif opt.postgui:
        out.append(f"POSTGUI_HALFILE = {opt.postgui}")
    out += ["", "[HALUI]", "",
            "# Osie: zakres = soft_limits z machine.yaml"]
    for a in cfg.axes:
        out += [f"[AXIS_{a.letter}]", f"MIN_LIMIT = {_f(a.soft_limits[0])}",
                f"MAX_LIMIT = {_f(a.soft_limits[1])}", f"MAX_VELOCITY = {_f(a.max_velocity)}",
                f"MAX_ACCELERATION = {_f(a.max_acceleration)}"]
        if a.letter == "Z":
            out.append("OFFSET_AV_RATIO = 0.2")      # D38: wycofanie Z w pauzie
        out.append("")
    out.append("# Jointy: zakres = travel, bazowanie jak homing w machine.yaml")
    for j in js:
        out += _joint_section(j, target)
    return "\n".join(out).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- HAL

@dataclass
class Switch:
    axis: Axis
    side: str             # min | max
    name: str             # wejście io.inputs
    din: int
    nc: bool

    @property
    def comp(self) -> str:
        return f"nc_{self.axis.letter.lower()}_{self.side}"

    @property
    def signal(self) -> str:
        return "lrt.in." + self.name.replace("_", "-")


def switches(cfg: MachineConfig) -> list[Switch]:
    out = []
    for a in cfg.axes:
        for side in ("min", "max"):
            sw = getattr(a.limits, side)
            if sw is not None:
                out.append(Switch(a, side, sw.input, cfg.io.inputs[sw.input], sw.contact == "NC"))
    return out


def _switch_nets(cfg: MachineConfig, js: list[Joint], source) -> list[str]:
    """Sieci krańcówek i czujników bazy; `source(sw)` → pin źródłowy stanu logicznego."""
    lines = []
    for sw in switches(cfg):
        members = [j for j in js if j.axis is sw.axis]
        shared = (sw.axis.home_sensor is not None
                  and sw.axis.home_sensor.shared_with == f"limit_{sw.side}")
        pins = []
        for j in members:
            pins.append(f"joint.{j.index}.{'neg' if sw.side == 'min' else 'pos'}-lim-sw-in")
            if shared:
                pins.append(f"joint.{j.index}.home-sw-in")
        kind = "home-sw" if shared else ("neg-lim" if sw.side == "min" else "pos-lim")
        lines.append(f"net linumert.j{members[0].index}.{kind}   {source(sw)} => {' '.join(pins)}")
    return lines


def render_plant_hal(cfg: MachineConfig, js: list[Joint]) -> str:
    n = len(js)
    sws = switches(cfg)
    inv = [sw for sw in sws if sw.nc]
    inputs = cfg.io.inputs
    estop_a = inputs[cfg.io.estop.input]
    estop_b = inputs.get("estop_b")
    out = [
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        f"# linumeRT · LinuxCNC <-> Plant (LRT-NET), z machine.yaml ({cfg.machine.name}).",
        "# Kontrakt D05 (docs/HAL_KONTRAKT.md); wejścia Plant = stan elektryczny",
        "# (1 = obwód zamknięty).",
        "# Model-Author: Claude · generator sesji 062. NIEZWERYFIKOWANE NA SPRZĘCIE.",
        "",
        "loadrt [KINS]KINEMATICS",
        "loadrt [EMCMOT]EMCMOT servo_period_nsec=[EMCMOT]SERVO_PERIOD num_joints=[KINS]JOINTS",
        "loadrt lrt_net personality=[PLANT]AXES ip=[PLANT]IP port=[PLANT]PORT",
        f"loadrt lrt_cia402 count={n}",
        "# Shared postgui expects this virtual M6 acknowledgement, also used by sim.",
        "loadrt timedelay names=sim_toolchange",
    ]
    if inv:
        out.append(f"loadrt not names={','.join(sw.comp for sw in inv)}")
    out += ["loadrt and2 names=estop_chain,estop_chain_hmi", "loadrt estop_latch names=estop_latch",
            "loadrt lrt_estop2", "",
            "addf motion-command-handler servo-thread", "addf motion-controller servo-thread"]
    out += [f"addf lrt-cia402.{j.index} servo-thread" for j in js]
    out += ["addf lrt-net.0 servo-thread", "addf sim_toolchange servo-thread"]
    out += [f"addf {sw.comp} servo-thread" for sw in inv]
    out += ["addf lrt-estop2.0 servo-thread", "addf estop_chain servo-thread",
            "addf estop_chain_hmi servo-thread", "addf estop_latch servo-thread", "",
            "# ---- napędy (Plant przez LRT-NET) ----"]
    out += [f"setp lrt-net.0.axis.{j.index}.scale [JOINT_{j.index}]SCALE" for j in js]
    out.append("")
    for j in js:
        i = j.index
        out += [f"net linumert.j{i}.pos-cmd   joint.{i}.motor-pos-cmd => "
                f"lrt-net.0.axis.{i}.pos-cmd",
                f"net linumert.j{i}.pos-fb    lrt-net.0.axis.{i}.pos-fb => joint.{i}.motor-pos-fb"]
    for j in js:
        out.append(f"net linumert.j{j.index}.enable    joint.{j.index}.amp-enable-out => "
                   f"lrt-cia402.{j.index}.enable")
    for j in js:
        out.append(f"net linumert.j{j.index}.fault     lrt-cia402.{j.index}.fault => "
                   f"joint.{j.index}.amp-fault-in")
    for sig, src, dst in (("cw", "lrt-cia402.{i}.controlword", "lrt-net.0.axis.{i}.controlword"),
                          ("sw", "lrt-net.0.axis.{i}.statusword", "lrt-cia402.{i}.statusword"),
                          ("mode", "lrt-cia402.{i}.mode", "lrt-net.0.axis.{i}.mode"),
                          ("md", "lrt-net.0.axis.{i}.mode-display", "lrt-cia402.{i}.mode-display")):
        out += [f"net lrt.j{j.index}.{sig}   {src.format(i=j.index)} => {dst.format(i=j.index)}"
                for j in js]
    out += ["", "# ---- krańcówki i czujniki bazy (NC: zadziałanie = obwód otwarty = din 0) ----"]
    for sw in sws:
        if sw.nc:
            out.append(f"net {sw.signal} lrt-net.0.din-{sw.din:02d} => {sw.comp}.in")
    out += _switch_nets(cfg, js, lambda sw: f"{sw.comp}.out" if sw.nc
                        else f"lrt-net.0.din-{sw.din:02d}")
    out += ["", "# ---- sonda ----"]
    if cfg.probe is not None:
        out.append(f"net linumert.io.probe        lrt-net.0.din-{inputs[cfg.probe.input]:02d} "
                   "=> motion.probe-input")
    if cfg.positions.tool_setter is not None:
        out.append(f"net linumert.io.toolsetter   "
                   f"lrt-net.0.din-{inputs[cfg.positions.tool_setter.input]:02d}")
    out += ["", "# ---- E-STOP: obwód NC z Plant (kanały A/B), łączność, grzyb HMI ----"]
    if estop_b is None:
        out += ["# Jeden kanał w machine.yaml: ten sam sygnał na oba wejścia lrt_estop2.",
                f"net linumert.io.estop-button lrt-net.0.din-{estop_a:02d} => lrt-estop2.0.ch-a "
                "lrt-estop2.0.ch-b"]
    else:
        out += [f"net linumert.io.estop-button lrt-net.0.din-{estop_a:02d} => lrt-estop2.0.ch-a",
                f"net linumert.io.estop-b      lrt-net.0.din-{estop_b:02d} => lrt-estop2.0.ch-b"]
    out += [
        "setp lrt-estop2.0.discrepancy-time 0.1",
        "net linumert.io.estop-2ch    lrt-estop2.0.ok => estop_chain.in0",
        "net linumert.io.estop-fault  lrt-estop2.0.fault",
        "net lrt.connected            lrt-net.0.connected => estop_chain.in1",
        "net lrt.estop-hw-ok          estop_chain.out => estop_chain_hmi.in0",
        "net linumert.hmi.estop-ok    => estop_chain_hmi.in1",
        "net lrt.estop-ok-in          estop_chain_hmi.out => estop_latch.ok-in",
        "net lrt.drive-fault          lrt-net.0.drive-fault",
        "net lrt.estop-reset          iocontrol.0.user-request-enable => estop_latch.reset "
        "lrt-estop2.0.reset",
        "net linumert.io.estop-ok     estop_latch.ok-out => iocontrol.0.emc-enable-in", "",
        "# ---- wyrocznia Plant (REQ-VM-06): uzbrojona po bazowaniu wszystkich osi ----",
        "net linumert.homed           motion.is-all-homed => lrt-net.0.dout-31", "",
        "# ---- narzędzia i chłodzenie ----",
        "net linumert.io.tool-prepare   iocontrol.0.tool-prepare => iocontrol.0.tool-prepared",
    ]
    coolant = cfg.io.outputs.get("coolant")
    out.append("net linumert.io.coolant-flood  iocontrol.0.coolant-flood"
               + (f" => lrt-net.0.dout-{coolant:02d}" if coolant is not None else ""))
    out.append("net linumert.io.coolant-mist   iocontrol.0.coolant-mist")
    return "\n".join(out) + "\n"


def render_spindle_sim_hal(cfg: MachineConfig, plant: bool) -> list[str]:
    on = cfg.io.outputs.get("spindle_on")
    dest = f" => lrt-net.0.dout-{on:02d}" if plant and on is not None else ""
    lines = [
        "loadrt sim_spindle names=sim_spindle", "loadrt ddt names=spindle_rps",
        "addf sim_spindle servo-thread", "addf spindle_rps servo-thread", "",
        f"net linumert.spindle.on        spindle.0.on{dest}",
        "net linumert.spindle.cw        spindle.0.forward",
        "net linumert.spindle.ccw       spindle.0.reverse",
        "net linumert.spindle.speed-cmd spindle.0.speed-out-rps => sim_spindle.velocity-cmd",
        "net linumert.spindle.revs      sim_spindle.position-fb => spindle.0.revs spindle_rps.in",
        "net linumert.spindle.speed-fb  spindle_rps.out => spindle.0.speed-in",
        "net linumert.spindle.index     spindle.0.index-enable <=> sim_spindle.index-enable",
        "net linumert.spindle.at-speed  => spindle.0.at-speed",
        "sets linumert.spindle.at-speed 1",
    ]
    if plant:
        lines.append("net linumert.spindle.rpm-cmd   spindle.0.speed-out => "
                     "lrt-net.0.spindle-speed-cmd")
    return lines


def render_sim_hal(cfg: MachineConfig, js: list[Joint]) -> str:
    """LinuxCNC sim: napęd = idealne nadążanie; czujnik bazy = porównanie pozycji (comp)."""
    names = ",".join(f"sim_j{j.index}" for j in js)
    homes = [(j, sw) for j in js for sw in switches(cfg)
             if sw.axis is j.axis and j.axis.home_sensor is not None
             and j.axis.home_sensor.shared_with == f"limit_{sw.side}"]
    out = [
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        f"# linumeRT · LinuxCNC sim, wygenerowane z machine.yaml ({cfg.machine.name}).",
        "# Kontrakt D05; napędy symulowane (wyjście = wejście), czujniki bazy z pozycji.",
        "# Model-Author: Claude · generator sesji 062.",
        "",
        "loadrt [KINS]KINEMATICS",
        "loadrt [EMCMOT]EMCMOT servo_period_nsec=[EMCMOT]SERVO_PERIOD num_joints=[KINS]JOINTS",
        f"loadrt scale names={names}", "loadrt timedelay names=sim_toolchange",
        "loadrt estop_latch names=estop_latch",
    ]
    if homes:
        out.append(f"loadrt comp names={','.join(f'home_j{j.index}' for j, _ in homes)}")
    out += ["", "addf motion-command-handler servo-thread", "addf motion-controller servo-thread"]
    out += [f"addf sim_j{j.index} servo-thread" for j in js]
    out += ["addf sim_toolchange servo-thread", "addf estop_latch servo-thread"]
    out += [f"addf home_j{j.index} servo-thread" for j, _ in homes]
    out += ["", "# ---- napędy (sim) ----"]
    for j in js:
        i = j.index
        out += [f"setp sim_j{i}.gain 1.0",
                f"net linumert.j{i}.pos-cmd   joint.{i}.motor-pos-cmd => sim_j{i}.in",
                f"net linumert.j{i}.pos-fb    sim_j{i}.out => joint.{i}.motor-pos-fb",
                f"net linumert.j{i}.enable    joint.{i}.amp-enable-out",
                f"net linumert.j{i}.fault     => joint.{i}.amp-fault-in"]
    out += ["", "# ---- czujniki bazy: comp out = in1 > in0, pozycja krańcówki z machine.yaml ----"]
    for j, sw in homes:
        i, pos = j.index, getattr(j.axis.limits, sw.side).position
        out.append(f"setp home_j{i}.hyst 0.02")
        if sw.side == "min":
            out += [f"setp home_j{i}.in1 {_f(pos)}", f"net linumert.j{i}.pos-fb => home_j{i}.in0"]
        else:
            out += [f"setp home_j{i}.in0 {_f(pos)}", f"net linumert.j{i}.pos-fb => home_j{i}.in1"]
        out.append(f"net linumert.j{i}.home-sw   home_j{i}.out => joint.{i}.home-sw-in")
    out += ["", "# ---- wrzeciono ----"] + render_spindle_sim_hal(cfg, plant=False)
    out += ["", "# ---- E-STOP (D35): w symulacji tylko grzyb HMI z sygnałem życia ----",
            "net linumert.hmi.estop-ok      => estop_latch.ok-in",
            "net linumert.io.estop-reset    iocontrol.0.user-request-enable => estop_latch.reset",
            "net linumert.io.estop-ok       estop_latch.ok-out => iocontrol.0.emc-enable-in",
            "net linumert.io.tool-prepare   iocontrol.0.tool-prepare => iocontrol.0.tool-prepared",
            "net linumert.io.coolant-flood  iocontrol.0.coolant-flood",
            "net linumert.io.coolant-mist   iocontrol.0.coolant-mist"]
    return "\n".join(out) + "\n"


def render(cfg: MachineConfig, target: str, opt: Options | None = None,
           scales: dict[str, float] | None = None) -> dict[str, str]:
    """Pliki konfiguracji dla celu `target`; nazwa INI = `<maszyna>.ini`."""
    if target not in TARGETS:
        raise ValueError(f"nieznany cel {target}; dozwolone: {', '.join(TARGETS)}")
    opt = opt or Options()
    if target == "hardware":
        from . import configgen_hw as hwgen

        if cfg.target != "hardware" or cfg.hardware is None:
            raise hwgen.HardwareConfigError(["cel hardware wymaga target: hardware i sekcji "
                                             "hardware: w machine.yaml"])
        if cfg.hardware.interface == "ethercat":
            raise hwgen.HardwareConfigError(["hardware.interface ethercat: generator EtherCAT "
                                             "to sesja 063"])
        plan = hwgen.hardware_plan(cfg)
        errors = hwgen.check(cfg, plan)
        if errors:
            raise hwgen.HardwareConfigError(errors)
        js = joints(cfg, {e["drive"]: e["scale"] for e in plan if e["axis"] != "S"})
        return {f"{cfg.machine.name}.ini": render_ini(cfg, js, target, opt,
                                                      hwgen.ini_extra(cfg, plan)),
                "linumert_hw.hal": hwgen.render_hal(cfg, js, plan),
                "spindle_vfd.hal": hwgen.render_spindle(cfg),
                "linumert_hw_postgui.hal": hwgen.render_postgui(cfg)}
    if scales is None:
        scales = plant_scales(cfg) if target == "plant" else {}
    js = joints(cfg, scales)
    ini = render_ini(cfg, js, target, opt)
    files = {f"{cfg.machine.name}.ini": ini}
    if target == "plant":
        head = ["# SPDX-License-Identifier: GPL-2.0-or-later",
                "# linumeRT · wrzeciono symulowane lokalnie (sim_spindle); Plant dostaje "
                "spindle_cmd przez LRT-NET.",
                "# Wygenerowane z machine.yaml · Model-Author: Claude · generator sesji 062.", ""]
        files["linumert_plant.hal"] = render_plant_hal(cfg, js)
        files["spindle_sim.hal"] = "\n".join(head + render_spindle_sim_hal(cfg, True)) + "\n"
    else:
        files["linumert_sim.hal"] = render_sim_hal(cfg, js)
    return files
