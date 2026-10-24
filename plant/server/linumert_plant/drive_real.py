"""Napędy rzeczywiste: sekcja `real:` szablonu i plan sprzętu maszyny (REQ-VD-06, sesja 061).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

Ten sam szablon opisuje napęd wirtualny (Plant) i rzeczywisty. Sekcja `real:` mówi, jak
LinuxCNC steruje napędem fizycznym; parametry mechaniki (`mechanics.ratio`) i liczba impulsów
na obrót (`motor.encoder_counts_per_rev`) są wspólne, więc skala impulsów na mm/° wynika
z szablonu, a nie z osobnej, ręcznie przepisywanej liczby.

    real:
      driver: stepgen            # stepgen | ethercat_cia402 | vfd_modbus | pwm
      timing_ns: {steplen: 5000, stepspace: 5000, dirsetup: 20000, dirhold: 20000}

Sterowniki: `stepgen` (step/dir: programowy stepgen na porcie równoległym albo stepgen karty
Mesa — wybór interfejsu w `machine.yaml`), `ethercat_cia402` (CSP przez linuxcnc-ethercat;
mapowanie obiektów, 60C2h = okres wątku serwo), `vfd_modbus` (hy_vfd albo mb2hal, poza RT),
`pwm` (wrzeciono sterowane PWM). Kanały (numer stepgen, pozycja slave) podaje `machine.yaml`
w sekcji `hardware:`; `hardware_plan()` łączy jedno z drugim dla generatora konfiguracji (062).
Nazwy pinów HAL powstają w generatorze. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math
from typing import Any

DRIVERS = ("stepgen", "ethercat_cia402", "vfd_modbus", "pwm")
# Typ napędu wirtualnego → sterowniki rzeczywiste, którymi da się go zastąpić.
ALLOWED = {
    "stepper_open": ("stepgen", "ethercat_cia402"),
    "servo_stepper": ("stepgen", "ethercat_cia402"),
    "servo_csp": ("ethercat_cia402", "stepgen"),
    "rotary_geared": ("stepgen", "ethercat_cia402"),
    "spindle_vfd": ("vfd_modbus", "pwm", "ethercat_cia402"),
}
TIMING_KEYS = ("steplen", "stepspace", "dirsetup", "dirhold")
TIMING_RANGE = (100, 1_000_000)          # [ns]
CIA_PDO_REQUIRED = ("6040h", "6041h", "607Ah", "6064h")
CIA_PDO_ALLOWED = CIA_PDO_REQUIRED + ("6060h", "6061h", "603Fh", "606Ch", "6077h", "60FDh")
VFD_PROTOCOLS = ("hy_vfd", "mb2hal")
VFD_BAUDS = (4800, 9600, 19200, 38400, 57600, 115200)
INTERFACES = ("parport", "mesa", "ethercat")
MESA_BOARDS = ("7i96s", "7i76e")
STEPGEN_INTERFACES = ("parport", "mesa")


def _int_in(value: Any, lo: int, hi: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


def check_real(raw: Any, typ: str | None, issues: list, issue_type) -> dict[str, Any] | None:
    """Waliduje sekcję `real:`; błędy dopisuje do `issues` jako `issue_type(path, text)`."""
    def bad(path: str, text: str) -> None:
        issues.append(issue_type(f"real{path}", text))

    if not isinstance(raw, dict):
        bad("", "sekcja musi być słownikiem")
        return None
    driver = raw.get("driver")
    if driver not in DRIVERS:
        bad(".driver", f"nieznany sterownik „{driver}”; dozwolone: {', '.join(DRIVERS)}")
        return None
    if typ in ALLOWED and driver not in ALLOWED[typ]:
        bad(".driver", f"typ „{typ}” nie może mieć sterownika „{driver}”; dozwolone: "
                       f"{', '.join(ALLOWED[typ])}")
    known = {"driver", {"stepgen": "timing_ns", "ethercat_cia402": "pdo",
                        "vfd_modbus": "vfd", "pwm": "pwm"}[driver]}
    for key in raw:
        if key not in known:
            bad(f".{key}", f"nieznane pole dla sterownika {driver}")
    out: dict[str, Any] = {"driver": driver}
    if driver == "stepgen":
        timing = raw.get("timing_ns")
        if not isinstance(timing, dict) or set(timing) != set(TIMING_KEYS):
            bad(".timing_ns", f"wymagane pola {', '.join(TIMING_KEYS)} [ns]")
        else:
            for key in TIMING_KEYS:
                if not _int_in(timing[key], *TIMING_RANGE):
                    bad(f".timing_ns.{key}",
                        f"liczba całkowita {TIMING_RANGE[0]}..{TIMING_RANGE[1]} ns")
            out["timing_ns"] = {k: timing[k] for k in TIMING_KEYS}
    elif driver == "ethercat_cia402":
        pdo = raw.get("pdo")
        if not isinstance(pdo, list) or not all(isinstance(x, str) for x in pdo):
            bad(".pdo", "lista obiektów CiA 402 w PDO, np. [6040h, 6041h, 607Ah, 6064h]")
        else:
            missing = [o for o in CIA_PDO_REQUIRED if o not in pdo]
            unknown = [o for o in pdo if o not in CIA_PDO_ALLOWED]
            if missing:
                bad(".pdo", f"brak obiektów CSP: {', '.join(missing)}")
            if unknown:
                bad(".pdo", f"nieobsługiwane obiekty: {', '.join(unknown)}")
            if len(set(pdo)) != len(pdo):
                bad(".pdo", "powtórzone obiekty")
            out["pdo"] = list(pdo)
    elif driver == "vfd_modbus":
        vfd = raw.get("vfd")
        if not isinstance(vfd, dict) or set(vfd) != {"protocol", "baud", "address"}:
            bad(".vfd", "wymagane pola protocol, baud, address")
        else:
            if vfd["protocol"] not in VFD_PROTOCOLS:
                bad(".vfd.protocol", f"dozwolone: {', '.join(VFD_PROTOCOLS)}")
            if vfd["baud"] not in VFD_BAUDS:
                bad(".vfd.baud", f"dozwolone: {', '.join(map(str, VFD_BAUDS))}")
            if not _int_in(vfd["address"], 1, 247):
                bad(".vfd.address", "adres Modbus 1..247")
            out["vfd"] = dict(vfd)
    else:
        pwm = raw.get("pwm")
        if not isinstance(pwm, dict) or set(pwm) != {"frequency_hz"}:
            bad(".pwm", "wymagane pole frequency_hz")
        elif not _int_in(pwm["frequency_hz"], 10, 100_000):
            bad(".pwm.frequency_hz", "liczba całkowita 10..100000 Hz")
        else:
            out["pwm"] = dict(pwm)
    return out


def real_schema() -> dict[str, Any]:
    """Fragment JSON Schema sekcji `real:` (reguły typ ↔ sterownik: README biblioteki)."""
    timing = {"type": "object", "additionalProperties": False, "required": list(TIMING_KEYS),
              "properties": {k: {"type": "integer", "minimum": TIMING_RANGE[0],
                                 "maximum": TIMING_RANGE[1]} for k in TIMING_KEYS}}
    return {
        "type": "object", "required": ["driver"], "additionalProperties": False,
        "description": "Napęd rzeczywisty (REQ-VD-06): sterownik LinuxCNC i jego parametry.",
        "properties": {
            "driver": {"enum": list(DRIVERS)},
            "timing_ns": timing,
            "pdo": {"type": "array", "items": {"enum": list(CIA_PDO_ALLOWED)},
                    "uniqueItems": True},
            "vfd": {"type": "object", "additionalProperties": False,
                    "required": ["protocol", "baud", "address"],
                    "properties": {"protocol": {"enum": list(VFD_PROTOCOLS)},
                                   "baud": {"enum": list(VFD_BAUDS)},
                                   "address": {"type": "integer", "minimum": 1,
                                               "maximum": 247}}},
            "pwm": {"type": "object", "additionalProperties": False,
                    "required": ["frequency_hz"],
                    "properties": {"frequency_hz": {"type": "integer", "minimum": 10,
                                                    "maximum": 100000}}},
        },
    }


# ---------------------------------------------------------------------------- skala i plan

def counts_per_unit(params: dict[str, Any]) -> float:
    """Impulsy na mm (oś liniowa) albo na ° (obrotowa) z mechaniki szablonu.

    `mechanics.ratio`: [m/rad] dla liniowej, [rad/rad] dla obrotowej; impulsy na obrót silnika
    `motor.encoder_counts_per_rev` (krokowiec: mikrokroki na obrót).
    """
    counts = float(params["motor"]["encoder_counts_per_rev"])
    ratio = float(params["mechanics"]["ratio"])
    if params["mechanics"]["kind"] == "linear":
        per_rev = ratio * math.tau * 1000.0          # [mm / obrót silnika]
    else:
        per_rev = ratio * 360.0                      # [° / obrót silnika]
    return counts / per_rev


def joint_drives(cfg) -> list[tuple[Any, str]]:
    """Jointy LinuxCNC = napędy osi w kolejności sekcji `drives:` bez wrzeciona.

    Ta sama reguła co ramka LRT-NET i konfiguracja Plant (tests/test_plant_config.py), więc
    numer jointu nie zależy od celu (plant, sim, hardware).
    """
    owner = {name: axis for axis in cfg.axes for name in axis.drives}
    return [(owner[d.name], d.name) for d in cfg.drives if d.name in owner]


def hardware_plan(cfg, drives: dict[str, Any]) -> list[dict[str, Any]]:
    """Plan sprzętu: każdy napęd osi i wrzeciono → sterownik, kanał, skala.

    `cfg` — `MachineConfig` z `target: hardware` i sekcją `hardware:`; `drives` — rozwiązane
    instancje (`resolve_machine_drives`). Błędy jako ValueError z listą komunikatów.
    """
    hw = cfg.hardware
    if hw is None:
        raise ValueError(["hardware: brak sekcji (wymagana dla target: hardware)"])
    errors: list[str] = []
    plan: list[dict[str, Any]] = []
    for joint, (axis, name) in enumerate(joint_drives(cfg)):
        inst = drives[name]
        real = inst.params.get("real")
        entry = {"drive": name, "axis": axis.letter, "joint": joint,
                 "template": inst.template_id}
        if real is None:
            errors.append(f"drives.{name}: szablon {inst.template_id} nie ma sekcji real:")
            continue
        entry["driver"] = real["driver"]
        if real["driver"] == "stepgen" and hw.interface not in STEPGEN_INTERFACES:
            errors.append(f"drives.{name}: stepgen wymaga interfejsu parport albo mesa, "
                          f"a hardware.interface = {hw.interface}")
        if real["driver"] == "ethercat_cia402" and hw.interface != "ethercat":
            errors.append(f"drives.{name}: ethercat_cia402 wymaga hardware.interface: ethercat")
        if name not in hw.channels:
            errors.append(f"hardware.channels: brak kanału napędu {name}")
            continue
        entry["channel"] = hw.channels[name]
        entry["scale"] = counts_per_unit(inst.params)
        entry["max_velocity"] = axis.max_velocity
        entry["max_acceleration"] = axis.max_acceleration
        for key in ("timing_ns", "pdo"):
            if key in real:
                entry[key] = real[key]
        plan.append(entry)
    channels = [e["channel"] for e in plan]
    if len(set(channels)) != len(channels):
        errors.append("hardware.channels: dwa napędy na tym samym kanale")
    spindle = drives[cfg.spindle.drive]
    real = spindle.params.get("real")
    if real is None:
        errors.append(f"drives.{cfg.spindle.drive}: szablon wrzeciona nie ma sekcji real:")
    else:
        entry = {"drive": cfg.spindle.drive, "axis": "S", "joint": None,
                 "template": spindle.template_id, "driver": real["driver"],
                 "max_rpm": cfg.spindle.max_rpm, "min_rpm": cfg.spindle.min_rpm}
        for key in ("vfd", "pwm", "pdo"):
            if key in real:
                entry[key] = real[key]
        if hw.spindle_device:
            entry["device"] = hw.spindle_device
        elif real["driver"] == "vfd_modbus":
            errors.append("hardware.spindle_device: falownik Modbus wymaga portu, "
                          "np. /dev/ttyUSB0")
        plan.append(entry)
    if errors:
        raise ValueError(errors)
    return plan
