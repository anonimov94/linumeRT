"""Budowa wirtualnej obrabiarki z `machine.yaml` (REQ-VM-01 … VM-05).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 014.

`machine.yaml` jest jedynym źródłem prawdy (bez osobnego plant.yaml). Ten moduł zamienia
konfigurację (mm, stopnie) i instancje napędów z biblioteki na listę kluczy rdzenia C
(`plant/core/machine.h`, jednostki SI): napędy, osie maszyny (gantry: dwa napędy i dopuszczalny
rozjazd), łańcuch kinematyczny z presetu albo z `kinematics.chain`, twarde zderzaki, krańcówki,
czujniki bazowe, pętlę E-STOP, sondę i mapę wejść/wyjść (32 bity jak w LRT-NET v1).

Model uruchamia `core_binding.PlantMachine`; bez kompilatora C można go zbudować i obejrzeć
(`python -m plant machine build <machine.yaml>`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linumert.machine.schema import Axis, Link, MachineConfig, MachineConfigError

from .drive_template import to_c_params
from .machine_drives import load_machine_drives

MAX_IO = 32          # digital_in / digital_out w LRT-NET v1 (u32)
FAR_STOP_M = 1.0e3   # zderzak "brak" po jednej stronie [m albo rad]
MM = 1.0e-3
DEG = math.pi / 180.0

# Presety łańcucha (REQ-VM-02). Osie liniowe stołu mają wektor przeciwny, żeby dodatni ruch osi
# oznaczał ruch narzędzia względem detalu w dodatnim kierunku (jak trivkins w LinuxCNC).
# Środki obrotu stołów domyślnie w zerze maszyny; inne położenie: `kinematics.chain`.
PRESET_CHAINS: dict[str, list[dict[str, Any]]] = {
    "router_gantry_xyz": [
        {"id": "Y", "kind": "linear", "axis": (0, 1, 0)},
        {"id": "X", "kind": "linear", "axis": (1, 0, 0), "parent": "Y"},
        {"id": "Z", "kind": "linear", "axis": (0, 0, 1), "parent": "X"},
    ],
    "mill_table_xyz": [
        {"id": "Y", "kind": "linear", "axis": (0, -1, 0), "branch": "workpiece"},
        {"id": "X", "kind": "linear", "axis": (-1, 0, 0), "parent": "Y", "branch": "workpiece"},
        {"id": "Z", "kind": "linear", "axis": (0, 0, 1)},
    ],
    "xyza_rotary": [
        {"id": "Y", "kind": "linear", "axis": (0, 1, 0)},
        {"id": "X", "kind": "linear", "axis": (1, 0, 0), "parent": "Y"},
        {"id": "Z", "kind": "linear", "axis": (0, 0, 1), "parent": "X"},
        {"id": "A", "kind": "rotary", "axis": (1, 0, 0), "branch": "workpiece"},
    ],
    "xyzac_trunnion": [
        {"id": "X", "kind": "linear", "axis": (1, 0, 0)},
        {"id": "Z", "kind": "linear", "axis": (0, 0, 1), "parent": "X"},
        {"id": "Y", "kind": "linear", "axis": (0, -1, 0), "branch": "workpiece"},
        {"id": "A", "kind": "rotary", "axis": (1, 0, 0), "parent": "Y", "branch": "workpiece"},
        {"id": "C", "kind": "rotary", "axis": (0, 0, 1), "parent": "A", "branch": "workpiece"},
    ],
    "xyzbc_trunnion": [
        {"id": "X", "kind": "linear", "axis": (1, 0, 0)},
        {"id": "Z", "kind": "linear", "axis": (0, 0, 1), "parent": "X"},
        {"id": "Y", "kind": "linear", "axis": (0, -1, 0), "branch": "workpiece"},
        {"id": "B", "kind": "rotary", "axis": (0, 1, 0), "parent": "Y", "branch": "workpiece"},
        {"id": "C", "kind": "rotary", "axis": (0, 0, 1), "parent": "B", "branch": "workpiece"},
    ],
}

# Mapowanie presetu na kinematykę LinuxCNC 2.9 (dla generatora konfiguracji). Moduły trt-kins
# wymagają parametrów osi obrotu (HAL) — wartości z łańcucha. NIEZWERYFIKOWANE z LinuxCNC:
# zgodność znaków obrotu z modułami trt-kins sprawdzi test integracyjny (sesja z LinuxCNC).
LINUXCNC_KINEMATICS: dict[str, dict[str, str]] = {
    "router_gantry_xyz": {"module": "trivkins", "coordinates": "XYYZ", "kinstype": "BOTH"},
    "mill_table_xyz": {"module": "trivkins", "coordinates": "XYZ", "kinstype": "IDENTITY"},
    "xyza_rotary": {"module": "trivkins", "coordinates": "XYZA", "kinstype": "IDENTITY"},
    "xyzac_trunnion": {"module": "xyzac-trt-kins", "coordinates": "XYZAC", "kinstype": "BOTH"},
    "xyzbc_trunnion": {"module": "xyzbc-trt-kins", "coordinates": "XYZBC", "kinstype": "BOTH"},
}

ESTOP_ACTIONS = {"sto": 0, "quick_stop": 1}
# Przetwornik napędu osi (drive.h: lrt_drive_encoder); krokowiec bez sprzężenia nie ma enkodera.
ENC_IDEAL, ENC_INCREMENTAL, ENC_ABSOLUTE = 0, 1, 2
STEPPER_OPEN = 1
START_MODES = ("random", "center")
PROBE_TYPES = {"box": 1, "plate": 2}


@dataclass
class MachineModel:
    """Model maszyny gotowy dla rdzenia C: klucze konfiguracji i nazwy elementów."""

    name: str
    settings: list[tuple[str, float]] = field(default_factory=list)
    curves: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    joints: list[str] = field(default_factory=list)          # litery osi w kolejności indeksów
    rotary: set[str] = field(default_factory=set)
    drives: list[str] = field(default_factory=list)          # id napędów w kolejności indeksów
    joint_drives: dict[str, list[str]] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    inputs: dict[str, int] = field(default_factory=dict)
    outputs: dict[str, int] = field(default_factory=dict)
    home_inputs: dict[str, str] = field(default_factory=dict)  # oś → wejście czujnika bazy
    # Sesja 015 (REQ-VM-07): wejście czujnika bazy każdego napędu (gantry: osobne strony; ""
    # = styk tylko na wejściu napędu), impulsy na jednostkę osi (jak SCALE w INI LinuxCNC)
    # i rodzaj przetwornika napędu.
    drive_home_inputs: dict[str, str] = field(default_factory=dict)
    counts_per_unit: dict[str, float] = field(default_factory=dict)
    encoders: dict[str, int] = field(default_factory=dict)
    spindle: str | None = None
    kinematics: dict[str, str] = field(default_factory=dict)
    config: MachineConfig | None = field(default=None, repr=False)

    def unit(self, letter: str) -> float:
        """Mnożnik jednostki machine.yaml → SI dla osi (mm → m albo stopnie → rad)."""
        return DEG if letter in self.rotary else MM

    def to_text(self) -> str:
        """Model jako tekst `klucz wartość` (do podglądu i diagnostyki)."""
        lines = [f"# linumeRT Plant: maszyna {self.name}"]
        lines += [f"{key} {value!r}" for key, value in self.settings]
        for drive, points in self.curves.items():
            lines += [f"curve.{drive} {omega!r} {torque!r}" for omega, torque in points]
        return "\n".join(lines) + "\n"


def _chain(cfg: MachineConfig) -> list[Link]:
    if cfg.kinematics.chain is not None:
        return list(cfg.kinematics.chain)
    return [Link(**link) for link in PRESET_CHAINS[cfg.kinematics.preset or ""]]


def _ordered(chain: list[Link]) -> list[Link]:
    """Kolejność topologiczna (rodzic przed dzieckiem); cykl → błąd."""
    by_id = {link.id: link for link in chain}
    done: list[Link] = []
    seen: set[str] = set()

    def visit(link: Link, stack: tuple[str, ...]) -> None:
        if link.id in seen:
            return
        if link.id in stack:
            raise MachineConfigError([f"kinematics.chain: cykl w łańcuchu ({' → '.join(stack)})"])
        if link.parent is not None:
            visit(by_id[link.parent], (*stack, link.id))
        seen.add(link.id)
        done.append(link)

    for link in chain:
        visit(link, ())
    return done


def _stops(axis: Axis, index: int, unit: float) -> tuple[list[tuple[str, float]], list[str]]:
    low, high = axis.hardstops.min, axis.hardstops.max
    if low is None and high is None:
        return [], []
    present = [s for s in (low, high) if s is not None]
    errors: list[str] = []
    if len({(s.stiffness_n_mm, s.damping_ns_mm) for s in present}) > 1:
        errors.append(f"axes[{index}].hardstops: różna sztywność albo tłumienie zderzaków min i "
                      "max nie jest obsługiwane przez model osi")
    stop = present[0]
    # N/mm → N/m (oś liniowa); oś obrotowa: N·m/° → N·m/rad (ta sama liczba w polu schematu)
    scale = 1.0 / unit
    out = [
        ("use_stops", 1.0),
        ("stop_min", low.position * unit if low is not None else -FAR_STOP_M),
        ("stop_max", high.position * unit if high is not None else FAR_STOP_M),
        ("stop_k", stop.stiffness_n_mm * scale),
        ("stop_c", stop.damping_ns_mm * scale),
        ("stop_fault", 1.0 if axis.hardstops.drive_fault else 0.0),
    ]
    return out, errors


def collision_free_start(cfg: MachineConfig, seed: int) -> dict[str, float] | None:
    """Pozycja startowa poza bryłami kolizyjnymi, gdy losowanie rdzenia C w nie trafia (REQ-VM-07).

    Odtwarza generator rdzenia (xorshift32 z ziarna); jeśli wylosowana pozycja nie koliduje,
    zwraca None i zostaje losowanie C. Inaczej losuje dalej z tego samego strumienia,
    aż pozycja nosa nie przecina stałych brył (maszyna nie może stanąć we wnętrzu magazynu).
    """
    if not cfg.collision_bodies:
        return None
    from .collisions import CollisionModel

    state = (seed & 0xFFFFFFFF) or 0x2545F491

    def draw() -> dict[str, float]:
        nonlocal state
        pose = {}
        for axis in cfg.axes:
            state ^= (state << 13) & 0xFFFFFFFF
            state ^= state >> 17
            state ^= (state << 5) & 0xFFFFFFFF
            lo, hi = axis.soft_limits
            pose[axis.letter] = lo + (state >> 8) / 16777216.0 * (hi - lo)
        return pose

    model = CollisionModel.from_config(cfg)

    def free(pose: dict[str, float]) -> bool:
        return not model.check(0.0, [pose.get(letter, 0.0) for letter in "XYZ"])

    first = draw()
    if free(first):
        return None
    for _ in range(1000):
        pose = draw()
        if free(pose):
            return pose
    raise ValueError("start: brak pozycji poza bryłami kolizyjnymi w zakresie soft limits")


def build_model(cfg: MachineConfig, drives: dict[str, Any], seed: int = 1,
                start: str = "random") -> MachineModel:
    """Zamienia konfigurację i rozwiązane napędy na model rdzenia C (zbiera wszystkie błędy).

    `start`: "random" — pozycja po włączeniu losowa w soft limits z ziarna `seed` (REQ-VM-07);
    "center" — środek soft limits (testy kinematyki). Pozycję z pliku stanu nakłada
    `plant_state.apply_state()` przed pierwszym krokiem.
    """
    if start not in START_MODES:
        raise ValueError(f"start: {start!r} (dozwolone: {', '.join(START_MODES)})")
    errors: list[str] = []
    model = MachineModel(name=cfg.machine.name, config=cfg)
    model.inputs = dict(cfg.io.inputs)
    model.outputs = dict(cfg.io.outputs)
    for kind, mapping in (("inputs", cfg.io.inputs), ("outputs", cfg.io.outputs)):
        for name, pin in mapping.items():
            if pin >= MAX_IO:
                errors.append(f"io.{kind}.{name}: numer {pin} poza zakresem 0..{MAX_IO - 1} "
                              "(32 bity LRT-NET)")
    put = model.settings.append

    # Napędy: kolejność z listy drives:
    model.drives = [d.name for d in cfg.drives]
    index_of = {name: i for i, name in enumerate(model.drives)}
    mapped_of: dict[str, dict[str, Any]] = {}
    for i, name in enumerate(model.drives):
        mapped = to_c_params(drives[name].params)
        mapped_of[name] = mapped
        put((f"drive.{i}.type", float(mapped["type"])))
        for key, value in mapped["drive"].items():
            put((f"drive.{i}.{key}", float(value)))
        for key, value in mapped["axis"].items():
            put((f"mech.{i}.{key}", float(value)))
        model.curves[i] = [(float(o), float(t)) for o, t in mapped["curve"]]

    safe_start = collision_free_start(cfg, seed) if start == "random" else None

    # Osie maszyny
    for j, axis in enumerate(cfg.axes):
        model.joints.append(axis.letter)
        if axis.rotary:
            model.rotary.add(axis.letter)
        unit = model.unit(axis.letter)
        model.joint_drives[axis.letter] = list(axis.drives)
        put((f"joint.{j}.kind", 1.0 if axis.rotary else 0.0))
        for k, name in enumerate(axis.drives[:2]):
            put((f"joint.{j}.drive{k}", float(index_of[name])))
        if len(axis.drives) > 2:
            errors.append(f"axes[{j}].drives: model obsługuje najwyżej 2 napędy na oś")
        if axis.gantry_max_skew is not None:
            put((f"joint.{j}.max_skew", axis.gantry_max_skew * unit))
        put((f"joint.{j}.initial", 0.5 * (axis.soft_limits[0] + axis.soft_limits[1]) * unit))
        if start == "random" and safe_start is not None:
            put((f"joint.{j}.initial", safe_start[axis.letter] * unit))
        elif start == "random":
            put((f"joint.{j}.initial_random", 1.0))
            put((f"joint.{j}.initial_min", axis.soft_limits[0] * unit))
            put((f"joint.{j}.initial_max", axis.soft_limits[1] * unit))
        for name in axis.drives[:2]:
            mapped = mapped_of[name]
            ratio = mapped["axis"]["ratio"]
            cpr = mapped["drive"]["counts_per_rev"]
            model.counts_per_unit[name] = unit / ratio * cpr / (2.0 * math.pi)
            if mapped["type"] == STEPPER_OPEN:
                encoder = ENC_IDEAL
            elif axis.homing.method == "absolute":
                encoder = ENC_ABSOLUTE
            else:
                encoder = ENC_INCREMENTAL
            model.encoders[name] = encoder
            put((f"drive.{index_of[name]}.encoder", float(encoder)))
        stops, stop_errors = _stops(axis, j, unit)
        errors += stop_errors
        for key, value in stops:
            put((f"joint.{j}.{key}", value))
    if cfg.spindle.drive in index_of:
        model.spindle = cfg.spindle.drive
        put(("spindle.drive", float(index_of[cfg.spindle.drive])))

    # Łańcuch kinematyczny
    joint_of = {letter: j for j, letter in enumerate(model.joints)}
    try:
        chain = _ordered(_chain(cfg))
    except MachineConfigError as exc:
        errors += exc.errors
        chain = []
    link_index = {link.id: n for n, link in enumerate(chain)}
    for n, link in enumerate(chain):
        model.links.append(link.id)
        put((f"link.{n}.kind", 1.0 if link.kind == "rotary" else 0.0))
        put((f"link.{n}.joint", float(joint_of.get(link.id, -1))))
        put((f"link.{n}.parent", float(link_index[link.parent]) if link.parent else -1.0))
        put((f"link.{n}.branch", 1.0 if link.branch == "workpiece" else 0.0))
        for name, value in zip(("ax", "ay", "az"), link.axis, strict=True):
            put((f"link.{n}.{name}", float(value)))
        for name, value in zip(("ox", "oy", "oz"), link.offset, strict=True):
            put((f"link.{n}.{name}", value * MM))

    # Krańcówki i czujniki bazowe. Gantry z `gantry_square`: styk bazy (własny czujnik albo
    # krańcówka wspólna) ma kopię na każdym napędzie (`switch.S.drive`), bo każda strona belki
    # bazuje na własnym czujniku; druga strona używa wejścia `<nazwa>_2`, jeśli jest w io.inputs,
    # inaczej styk jest tylko na wejściu napędu.
    switches: list[dict[str, float]] = []
    for j, axis in enumerate(cfg.axes):
        _axis_switches(model, cfg, axis, j, index_of, switches, put)
    for s, sw in enumerate(switches):
        for key, value in sw.items():
            put((f"switch.{s}.{key}", float(value)))

    # E-STOP, sonda, ziarno
    put(("estop.input", float(cfg.io.inputs.get(cfg.io.estop.input, -1))))
    put(("estop.nc", 1.0 if cfg.io.estop.contact == "NC" else 0.0))
    put(("estop.action", float(ESTOP_ACTIONS[cfg.io.estop.action])))
    if cfg.probe is not None:
        probe = cfg.probe
        put(("probe.type", float(PROBE_TYPES[probe.target.type])))
        put(("probe.input", float(cfg.io.inputs.get(probe.input, -1))))
        put(("probe.nc", 1.0 if probe.contact == "NC" else 0.0))
        put(("probe.tip_length", probe.tip_length * MM))
        for axis_name, lo, hi in zip("xyz", probe.target.min, probe.target.max, strict=True):
            put((f"probe.min_{axis_name}", lo * MM))
            put((f"probe.max_{axis_name}", hi * MM))
    put(("machine.seed", float(seed)))

    if cfg.kinematics.preset is not None:
        model.kinematics = dict(LINUXCNC_KINEMATICS[cfg.kinematics.preset])
    if errors:
        raise MachineConfigError(errors)
    return model


def _axis_switches(model: MachineModel, cfg: MachineConfig, axis: Axis, j: int,
                   index_of: dict[str, int], switches: list[dict[str, float]], put) -> None:
    """Styki osi `j` (krańcówki, czujnik bazy) i podłączenie ich do wejść napędów."""
    unit = model.unit(axis.letter)
    gantry = axis.homing.gantry_square and len(axis.drives) > 1
    sides: list[str | None] = list(axis.drives[:2]) if gantry else [None]
    sensor = axis.home_sensor
    shared = sensor.shared_with.removeprefix("limit_") if sensor and sensor.shared_with else None
    found: dict[str, dict[str | None, int]] = {"min": {}, "max": {}, "home": {}}

    def add(kind: str, sw: dict[str, float], name: str, drive: str | None) -> None:
        if drive is not None:
            sw["drive"] = float(index_of[drive])
            if drive != axis.drives[0]:
                sw["input"] = float(cfg.io.inputs.get(f"{name}_2", -1))
        found[kind][drive] = len(switches)
        switches.append(sw)

    for side_name, side in (("min", -1.0), ("max", 1.0)):
        sw = getattr(axis.limits, side_name)
        if sw is None:
            continue
        for drive in (sides if shared == side_name else [None]):
            add(side_name, {"joint": j, "role": 0, "side": side, "position": sw.position * unit,
                            "hysteresis": sw.hysteresis * unit, "nc": sw.contact == "NC",
                            "input": cfg.io.inputs.get(sw.input, -1),
                            "bounce": sw.debounce_ms / 1000.0}, sw.input, drive)
            if shared == side_name:
                found["home"][drive] = found[side_name][drive]
                _home_input(model, axis, drive, sw.input, cfg)
    if shared is not None:
        limit = getattr(axis.limits, shared)
        if limit is not None:
            model.home_inputs[axis.letter] = limit.input
    elif sensor is not None:
        model.home_inputs[axis.letter] = sensor.input or ""
        for drive in sides:
            add("home", {"joint": j, "role": 1, "side": float(axis.homing.direction),
                         "position": (sensor.position or 0.0) * unit,
                         "hysteresis": sensor.hysteresis * unit, "nc": sensor.contact == "NC",
                         "input": cfg.io.inputs.get(sensor.input or "", -1), "bounce": 0.0},
                sensor.input or "", drive)
            _home_input(model, axis, drive, sensor.input or "", cfg)

    # Bazowanie w napędzie (metoda drive, tryb 6) i styki na wejściach napędów.
    for name in axis.drives[:2]:
        d = index_of[name]
        if axis.homing.method == "drive":
            scale = model.counts_per_unit[name]
            put((f"drive.{d}.homing_method", float(axis.homing.cia402_method or 0)))
            put((f"drive.{d}.homing_speed_switch", float(round(axis.homing.search_speed * scale))))
            put((f"drive.{d}.homing_speed_zero", float(round(axis.homing.latch_speed * scale))))
            put((f"drive.{d}.home_offset", float(round(axis.homing.offset * scale))))
        for kind, key in (("min", "din_neg_limit"), ("max", "din_pos_limit"), ("home", "din_home")):
            where = found[kind]
            s = where.get(name, where.get(None))
            if s is not None:
                put((f"drive.{d}.{key}", float(s)))


def _home_input(model: MachineModel, axis: Axis, drive: str | None, name: str,
                cfg: MachineConfig) -> None:
    """Zapamiętuje wejście czujnika bazy napędu (dla mastera bazowania)."""
    for d in ([drive] if drive is not None else axis.drives[:2]):
        own = name if (drive is None or d == axis.drives[0]) else f"{name}_2"
        model.drive_home_inputs[d] = own if own in cfg.io.inputs else ""


def build_machine(machine: Path | str, library_dir: Path | None = None,
                  seed: int = 1, start: str = "random") -> MachineModel:
    """Wczytuje `machine.yaml` z biblioteką napędów i buduje model (błędy: MachineConfigError)."""
    cfg, drives = load_machine_drives(machine, library_dir)
    return build_model(cfg, drives, seed=seed, start=start)
