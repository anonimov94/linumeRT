"""Generator konfiguracji: wyjście sprzętowe step/dir — port równoległy i Mesa (sesja 062).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-24

Dane: `machine.yaml` z `target: hardware` i sekcją `hardware:` (interfejs, kanały stepgen,
piny fizyczne wejść/wyjść, piny kontraktu bezpieczeństwa) oraz sekcje `real:` szablonów napędów
(sterownik, czasy impulsów, skala z mechaniki — `linumert_plant.drive_real.hardware_plan`).

Bezpieczeństwo (CLAUDE.md §6, docs/bezpieczenstwo): E-STOP i STO to obwód sprzętowy. Generator
odmawia, gdy brak pinu monitora E-STOP, wyjścia sygnału życia PC albo wejścia potwierdzenia
zewnętrznego watchdoga. Monitor E-STOP idzie wprost do `iocontrol.0.emc-enable-in` (bez zatrzasku
w HAL; reset jest fizyczny), więc wynik przechodzi `linumert.machine.deployment --hal-from-ini`.
Grzyb HMI nie wchodzi do tego toru — ekran nie jest funkcją bezpieczeństwa.

Port równoległy: programowy stepgen w wątku bazowym (BASE_PERIOD); laptopy i karty PCIe-LPT
często mają zbyt duże opóźnienia — przed uruchomieniem test latencji (sesja 068).
Mesa 7i96S/7i76E przez hm2_eth: stepgen karty, wątek serwo. EtherCAT: sesja 063.
Nazwy pinów kart Mesa według dokumentacji hostmot2 LinuxCNC 2.9. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from typing import Any

from .schema import MachineConfig

PARPORT_WARNING = ("Port równoległy: programowy stepgen wymaga małej latencji (laptopy i karty "
                   "PCIe-LPT zwykle się nie nadają) — przed ruchem test latencji.")
MAXACCEL_MARGIN = 1.25         # STEPGEN_MAXACCEL = margines × MAX_ACCELERATION (zapas stepgen)
VFD_MAX_FREQ = 400             # [Hz] częstotliwość przy max_rpm (typowe wrzeciono HF)


class HardwareConfigError(ValueError):
    """Konfiguracja sprzętowa niekompletna albo niebezpieczna; `errors` po polsku."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def hardware_plan(cfg: MachineConfig) -> list[dict[str, Any]]:
    from linumert_plant.drive_library import load_library
    from linumert_plant.drive_real import hardware_plan as plan_of
    from linumert_plant.machine_drives import resolve_machine_drives

    try:
        return plan_of(cfg, resolve_machine_drives(cfg, load_library()))
    except ValueError as exc:
        errors = exc.args[0] if exc.args and isinstance(exc.args[0], list) else [str(exc)]
        raise HardwareConfigError(errors) from exc


def check(cfg: MachineConfig, plan: list[dict[str, Any]]) -> list[str]:
    """Błędy blokujące generowanie (pusta lista = można generować)."""
    errors: list[str] = []
    hw = cfg.hardware
    if cfg.target != "hardware" or hw is None:
        return ["cel hardware wymaga target: hardware i sekcji hardware: w machine.yaml"]
    if hw.interface == "ethercat":
        errors.append("hardware.interface ethercat: generator EtherCAT to sesja 063")
    if hw.interface == "mesa" and not hw.address:
        errors.append("hardware.address: adres IP karty Mesa (np. 10.10.10.10)")
    estop = cfg.io.estop.input
    if estop not in hw.inputs:
        errors.append(f"hardware.inputs.{estop}: brak pinu monitora E-STOP — generator odmawia "
                      "konfiguracji sprzętowej bez wejścia E-STOP")
    if not hw.heartbeat_output:
        errors.append("hardware.heartbeat_output: wymagane wyjście sygnału życia PC")
    if not hw.watchdog_monitor:
        errors.append("hardware.watchdog_monitor: wymagane wejście potwierdzenia watchdoga PC")
    for axis in cfg.axes:
        for side in ("min", "max"):
            sw = getattr(axis.limits, side)
            if sw is not None and sw.input not in hw.inputs:
                errors.append(f"hardware.inputs.{sw.input}: brak pinu krańcówki {axis.letter} "
                              f"{side}")
    for entry in plan:
        if entry["axis"] == "S":
            if entry["driver"] != "vfd_modbus":
                errors.append(f"wrzeciono: sterownik {entry['driver']} — w 062 tylko falownik "
                              "Modbus (hy_vfd)")
            elif entry["vfd"]["protocol"] != "hy_vfd":
                errors.append("wrzeciono: mb2hal wymaga własnego pliku konfiguracji (poza 062)")
            continue
        if entry["driver"] != "stepgen":
            errors.append(f"drives.{entry['drive']}: sterownik {entry['driver']} — w 062 tylko "
                          "stepgen")
        if hw.interface == "parport" and entry["drive"] not in hw.step_dir:
            errors.append(f"hardware.step_dir.{entry['drive']}: piny step i dir portu")
    return errors


def ini_extra(cfg: MachineConfig, plan: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Sekcje INI tylko dla sprzętu: [SAFETY], [VFD]."""
    hw = cfg.hardware
    out = {"SAFETY": [
        "# Kontrakt bezpieczeństwa (docs/bezpieczenstwo/README.md). Obwód E-STOP/STO sprzętowy.",
        f"ESTOP_MONITOR_PIN = {hw.inputs[cfg.io.estop.input]}",
        f"PC_HEARTBEAT_OUTPUT_PIN = {hw.heartbeat_output}",
        f"PC_WATCHDOG_MONITOR_PIN = {hw.watchdog_monitor}",
        "EXTERNAL_PC_WATCHDOG = 1", "PHYSICAL_RESET = 1", "AUTOMATIC_RESTART = 0"]}
    spindle = next(e for e in plan if e["axis"] == "S")
    vfd = spindle["vfd"]
    out["VFD"] = [f"DEVICE = {spindle['device']}", f"BAUD = {vfd['baud']}", "PARITY = none",
                  f"SLAVE = {vfd['address']}", f"MAX_RPM = {spindle['max_rpm']:g}",
                  f"MAX_FREQ = {VFD_MAX_FREQ}"]
    return out


def _board(cfg: MachineConfig) -> str:
    return f"hm2_{cfg.hardware.board}.0"


def render_hal(cfg: MachineConfig, js, plan: list[dict[str, Any]]) -> str:
    from .configgen import _switch_nets, switches

    hw = cfg.hardware
    by_drive = {e["drive"]: e for e in plan if e["axis"] != "S"}
    parport = hw.interface == "parport"
    out = [
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        f"# linumeRT · maszyna rzeczywista {cfg.machine.name}, interfejs {hw.interface}"
        + (f" ({hw.board})" if hw.board else "") + ", wygenerowane z machine.yaml.",
        "# Kontrakt D05 (docs/HAL_KONTRAKT.md); blok napędów step/dir. Monitor E-STOP wprost do",
        "# emc-enable-in (obwód i reset sprzętowe). Model-Author: Claude · generator sesji 062.",
        "# NIEZWERYFIKOWANE NA SPRZĘCIE.",
    ]
    if parport:
        out += [f"# {PARPORT_WARNING}", "",
                "loadrt [KINS]KINEMATICS",
                "loadrt [EMCMOT]EMCMOT base_period_nsec=[EMCMOT]BASE_PERIOD "
                "servo_period_nsec=[EMCMOT]SERVO_PERIOD num_joints=[KINS]JOINTS",
                f'loadrt hal_parport cfg="{hw.address or "0x378"} out"',
                f"loadrt stepgen step_type={','.join('0' for _ in js)}"]
    else:
        out += ["", "loadrt [KINS]KINEMATICS",
                "loadrt [EMCMOT]EMCMOT servo_period_nsec=[EMCMOT]SERVO_PERIOD "
                "num_joints=[KINS]JOINTS",
                "loadrt hostmot2", f'loadrt hm2_eth board_ip="{hw.address}"']
    inv = [sw for sw in switches(cfg) if sw.nc]
    out.append("loadrt timedelay names=sim_toolchange")
    if inv:
        out.append(f"loadrt not names={','.join(sw.comp for sw in inv)}")
    out.append("")
    if parport:
        out += ["addf parport.0.read base-thread", "addf stepgen.make-pulses base-thread",
                "addf parport.0.write base-thread", "addf stepgen.capture-position servo-thread",
                "addf motion-command-handler servo-thread", "addf motion-controller servo-thread",
                "addf stepgen.update-freq servo-thread"]
    else:
        b = _board(cfg)
        out += [f"addf {b}.read servo-thread", "addf motion-command-handler servo-thread",
                "addf motion-controller servo-thread"]
    out.append("addf sim_toolchange servo-thread")
    out += [f"addf {sw.comp} servo-thread" for sw in inv]
    if not parport:
        out += [f"addf {_board(cfg)}.write servo-thread",
                f"setp {_board(cfg)}.watchdog.timeout_ns 5000000"]
    out += ["", "# ---- napędy step/dir ----"]
    for j in js:
        e = by_drive[j.drive]
        c = e["channel"]
        sg = f"stepgen.{c}" if parport else f"{_board(cfg)}.stepgen.{c:02d}"
        t = e["timing_ns"]
        i = j.index
        out += [f"setp {sg}.position-scale [JOINT_{i}]SCALE",
                f"setp {sg}.maxaccel [JOINT_{i}]STEPGEN_MAXACCEL",
                f"setp {sg}.steplen {t['steplen']}", f"setp {sg}.stepspace {t['stepspace']}",
                f"setp {sg}.dirsetup {t['dirsetup']}", f"setp {sg}.dirhold {t['dirhold']}",
                f"net linumert.j{i}.pos-cmd   joint.{i}.motor-pos-cmd => {sg}.position-cmd",
                f"net linumert.j{i}.pos-fb    {sg}.position-fb => joint.{i}.motor-pos-fb",
                f"net linumert.j{i}.enable    joint.{i}.amp-enable-out => {sg}.enable",
                f"net linumert.j{i}.fault     => joint.{i}.amp-fault-in"]
        if parport:
            step, direction = hw.step_dir[j.drive]
            out += [f"net linumert.j{i}.step      {sg}.step => parport.0.pin-{step:02d}-out",
                    f"net linumert.j{i}.dir       {sg}.dir => parport.0.pin-{direction:02d}-out"]
    out += ["", "# ---- krańcówki i czujniki bazy (1 = obwód zamknięty; NC odwrócone) ----"]
    for sw in inv:
        out.append(f"net {sw.signal} {hw.inputs[sw.name]} => {sw.comp}.in")
    out += _switch_nets(cfg, js, lambda sw: f"{sw.comp}.out" if sw.nc else hw.inputs[sw.name])
    out += ["", "# ---- sonda ----"]
    if cfg.probe is not None and cfg.probe.input in hw.inputs:
        out.append(f"net linumert.io.probe        {hw.inputs[cfg.probe.input]} => "
                   "motion.probe-input")
    ts = cfg.positions.tool_setter
    if ts is not None and ts.input in hw.inputs:
        out.append(f"net linumert.io.toolsetter   {hw.inputs[ts.input]}")
    out += ["", "# ---- E-STOP: monitor obwodu sprzętowego wprost do LinuxCNC; reset fizyczny ----",
            f"net linumert.io.estop-ok     {hw.inputs[cfg.io.estop.input]} => "
            "iocontrol.0.emc-enable-in",
            "# potwierdzenie zewnętrznego watchdoga PC (diagnostyka na ekranie)",
            f"net linumert.io.pc-watchdog-ok {hw.watchdog_monitor}",
            "", "# ---- narzędzia i chłodzenie ----",
            "net linumert.io.tool-prepare   iocontrol.0.tool-prepare => iocontrol.0.tool-prepared"]
    coolant = hw.outputs.get("coolant")
    out.append("net linumert.io.coolant-flood  iocontrol.0.coolant-flood"
               + (f" => {coolant}" if coolant else ""))
    out.append("net linumert.io.coolant-mist   iocontrol.0.coolant-mist")
    return "\n".join(out) + "\n"


def render_spindle(cfg: MachineConfig) -> str:
    on = cfg.hardware.outputs.get("spindle_on")
    return "\n".join([
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "# linumeRT · wrzeciono przez falownik RS485 (hy_vfd, Modbus RTU poza RT), sekcja [VFD].",
        "# Wygenerowane z machine.yaml · Model-Author: Claude · generator sesji 062.",
        "# NIEZWERYFIKOWANE NA SPRZĘCIE.", "",
        "loadusr -Wn vfd hy_vfd -n vfd -d [VFD]DEVICE -r [VFD]BAUD -p [VFD]PARITY -t [VFD]SLAVE "
        "-S [VFD]MAX_RPM -F [VFD]MAX_FREQ",
        "loadrt scale names=spindle_rpm2rps", "addf spindle_rpm2rps servo-thread",
        "setp spindle_rpm2rps.gain 0.016666667", "",
        "net linumert.spindle.enable     motion.motion-enabled => vfd.enable",
        "net linumert.spindle.on         spindle.0.on => vfd.spindle-on" + (f" {on}" if on else ""),
        "net linumert.spindle.cw         spindle.0.forward => vfd.spindle-forward",
        "net linumert.spindle.ccw        spindle.0.reverse => vfd.spindle-reverse",
        "net linumert.spindle.rpm-cmd    spindle.0.speed-out-abs => vfd.speed-command",
        "net linumert.spindle.rpm-fb     vfd.spindle-speed-fb => spindle_rpm2rps.in",
        "net linumert.spindle.speed-fb   spindle_rpm2rps.out => spindle.0.speed-in",
        "net linumert.spindle.at-speed   vfd.spindle-at-speed => spindle.0.at-speed",
        "net linumert.spindle.vfd-ok     vfd.hycomm-ok",
    ]) + "\n"


def render_postgui(cfg: MachineConfig) -> str:
    """Piny ekranu po starcie: M6, pauza, grzyb HMI i sygnał życia PC → zewnętrzny watchdog."""
    hw = cfg.hardware
    return "\n".join([
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "# linumeRT · po starcie ekranu (piny linumert.*), maszyna rzeczywista; jak",
        "# config/sim/linumert_xyz/linumert_postgui.hal, plus sygnał życia PC na wyjście",
        "# sprzętowe.",
        "# Model-Author: Claude · generator sesji 062. NIEZWERYFIKOWANE NA SPRZĘCIE.", "",
        "net linumert.io.tool-change iocontrol.0.tool-change => sim_toolchange.in",
        "net linumert.io.tool-changed sim_toolchange.out => iocontrol.0.tool-changed",
        "net linumert.io.tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number",
        "",
        "net linumert.spindle.inhibit    linumert.spindle-inhibit => spindle.0.inhibit",
        "net linumert.z.eoffset-clear    linumert.eoffset-clear => lrt_retract_clear.in-0",
        "net linumert.z.eoffset-counts   linumert.eoffset-spindle-count => lrt_retract_legacy.in",
        "net linumert.z.eoffset          linumert.eoffset-value <= axis.z.eoffset",
        "setp lrt_retract_enable.in-0 1",
        "net linumert.retract.own linumert.retract-own",
        "net linumert.retract.target linumert.retract-target => lrt_retract_select.in1", "",
        "# D35: grzyb HMI (bez wpływu na tor sprzętowy) i sygnał życia ekranu → watchdog HAL",
        "# i wyjście do zewnętrznego watchdoga PC.",
        "net linumert.hmi.button         linumert.hmi-estop-ok   => lrt_hmi_ok.in-00",
        f"net linumert.hmi.heartbeat      linumert.hmi-heartbeat  => watchdog.input-0 "
        f"{hw.heartbeat_output}",
        "net linumert.hmi.wd-enable      linumert.hmi-wd-enable  => watchdog.enable-in",
        "net linumert.hmi.ack            linumert.hmi-ack        => lrt_ack_edge.in",
    ]) + "\n"
