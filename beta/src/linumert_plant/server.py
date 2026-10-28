"""Serwer LRT-NET Plant: ramka mastera → krok modelu → odpowiedź (docs/PLANT.md §2–3, §8).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 016.

`PlantServer.handle()` jest czystą funkcją protokołu (bez gniazd), więc testy i scenariusze mogą
ją wołać bezpośrednio; `serve()` dokłada pętlę UDP. Tryby:
  lockstep  czas wyłącznie z pola `time_ns` ramek (bez zegara ściennego) — ten sam przebieg
            i ziarno dają identyczny ślad (SHA-256 odpowiedzi, REQ-QA-04);
  realtime  odstępy i watchdog z zegara monotonicznego hosta (VM-B).
Osie ramki to napędy osi z `machine.yaml` w kolejności `drives:` bez napędu wrzeciona
(gantry = dwa bloki, jak dwa jointy LinuxCNC). Wrzeciono (sesja 021, `vfd.SpindleModel`):
bez sekcji `vfd` w plant.yaml zadaje je `spindle_cmd` ramki [obr/min, znak = kierunek],
z sekcją `vfd` — falownik przez hy_vfd (pty) albo Modbus TCP (serwery w `serve.py`);
`spindle_actual` to zawsze obroty wału modelu [obr/min].
Odporność (REQ-QA-03): uszkodzona ramka jest odrzucana i liczona; wyjątek modelu przełącza
w stan bezpieczny (napędy wyłączone, wyjścia zerowe) bez kończenia procesu.
Panel (sesja 022): telemetria osi w buforze pierścieniowym (`panel.telemetry`), parametry
live napędów (`set_live`, presety), wirtualny pulpit jako bity `digital_in` (`panel.desk`).
Awarie (sesja 024, `faults.py`): utrata i opóźnienie ramek, wymuszone wejścia — `self.faults`.
Ten moduł działa poza RT (CLAUDE.md §5).
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import random
import socket
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .atc import ToolChangerModel, ToolSetterModel, ToolSpec
from .collisions import CollisionModel
from .core_binding import CW_FAULT_RESET, MODE_CSP, PlantMachine
from .drive_template import LiveParams
from .faults import Faults, FaultState
from .lrtnet import (
    FLAG_ESTOP_OPEN,
    FLAG_FAULT,
    FLAG_RESET_STATS,
    PORT,
    AxisReply,
    FrameError,
    Reply,
    decode_command,
    encode_reply,
    seq_delta,
)
from .oracle import Oracle
from .panel.desk import Desk, DeskConfig
from .panel.telemetry import Telemetry
from .trace import TraceWriter
from .vfd import SpindleModel, VfdConfig, VfdFaults

log = logging.getLogger("linumert_plant.server")

FAULT_COMM_WATCHDOG = 11  # drive.h: LRT_DRIVE_FAULT_COMM_WATCHDOG (E-4003, 8130h)
SW_FAULT = 0x0008
ERR_MODEL = 0xFF00  # 603Fh awarii ogólnej (E-4200) zgłaszany po wyjątku modelu
DT_MIN, DT_MAX = 100_000, 10_000_000  # [ns], docs/PLANT.md §3 reguła 3
# Podkroki rdzenia C na cykl mastera: krokowiec przy G0 wymaga kroku ≤ 0,5 ms (sesja 049,
# docs/raporty/plant_substeps.md); cel 607Ah jest interpolowany, więc wynik nie zależy od n ≥ 2.
DEFAULT_SUBSTEPS = 4
JITTER_WINDOW = 100
MODES = ("lockstep", "realtime")
PANEL_PORT = 8080


class PlantConfigError(ValueError):
    """Błędny `plant.yaml` (komunikat po polsku, ze ścieżką pola)."""


@dataclass
class PlantConfig:
    """Uruchomienie Plant (`plant.yaml`, docs/PLANT.md §7) — nie maszyna."""

    machine: Path | None = None
    listen: str = "127.0.0.1"
    port: int = PORT
    cycle_ns: int = 1_000_000
    substeps: int = DEFAULT_SUBSTEPS
    watchdog_ms: float = 50.0
    mode: str = "lockstep"
    seed: int = 1
    state_file: Path | None = None
    trace_path: Path | None = None
    trace_format: str = "csv"
    oracle_arm_bit: int | None = 31  # bit digital_out uzbrajający wyrocznię (None = zawsze)
    tools: dict[int, ToolSpec] = field(default_factory=dict)  # wysięg i średnica narzędzi
    vfd: VfdConfig | None = None  # falownik wrzeciona (hy_vfd / Modbus TCP); None = LRT-NET
    panel_listen: str = "127.0.0.1"  # panel web (sesja 022)
    panel_port: int = PANEL_PORT  # 0 = port wybrany przez system (testy)
    telemetry_ms: float = 5.0  # okres próbki telemetrii panelu [ms czasu modelu]
    desk: DeskConfig | None = None  # wirtualny pulpit (bity digital_in); None = brak

    def check(self) -> None:
        errors = []
        if self.mode not in MODES:
            errors.append(f"mode: {self.mode!r} — dozwolone {', '.join(MODES)}")
        if not 0 < self.port < 65536:
            errors.append(f"network.port: {self.port} poza 1–65535")
        if not DT_MIN <= self.cycle_ns <= DT_MAX:
            errors.append(f"timing.cycle_ns: {self.cycle_ns} poza {DT_MIN}–{DT_MAX}")
        if not 1 <= self.substeps <= 100:
            errors.append(f"timing.substeps: {self.substeps} poza 1–100")
        if not 1 <= self.watchdog_ms <= 10_000:
            errors.append(f"timing.watchdog_ms: {self.watchdog_ms} poza 1–10000")
        if self.oracle_arm_bit is not None and not 0 <= self.oracle_arm_bit <= 31:
            errors.append(f"oracle.arm_bit: {self.oracle_arm_bit} poza 0–31 (null = zawsze)")
        if self.trace_format not in ("csv", "jsonl"):
            errors.append(f"trace.format: {self.trace_format!r} — dozwolone csv, jsonl")
        if self.vfd is not None:
            errors += self.vfd.problems()
        if not 0 <= self.panel_port < 65536:
            errors.append(f"network.panel_port: {self.panel_port} poza 0–65535")
        if not 0.5 <= self.telemetry_ms <= 1000:
            errors.append(f"panel.telemetry_ms: {self.telemetry_ms} poza 0,5–1000")
        if self.desk is not None:
            errors += self.desk.problems()
        if errors:
            raise PlantConfigError("; ".join(errors))


def load_plant_config(path: Path | str) -> PlantConfig:
    """Wczytuje `plant.yaml`; ścieżki względne liczone od katalogu pliku."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise PlantConfigError(f"{path}: nie można odczytać ({exc.strerror})") from None
    except yaml.YAMLError as exc:
        raise PlantConfigError(f"{path}: błąd składni YAML ({exc})") from None
    if not isinstance(data, dict):
        raise PlantConfigError(f"{path}: oczekiwano mapy klucz: wartość")
    base = path.parent

    def section(name: str) -> dict[str, Any]:
        value = data.get(name) or {}
        if not isinstance(value, dict):
            raise PlantConfigError(f"{path}: {name}: oczekiwano mapy")
        return value

    def rel(value: Any) -> Path | None:
        return None if value in (None, "") else (base / str(value))

    net, timing, trace = section("network"), section("timing"), section("trace")
    oracle, vfd = section("oracle"), data.get("vfd")
    panel, desk = section("panel"), data.get("desk")
    if desk is not None and not isinstance(desk, dict):
        raise PlantConfigError(f"{path}: desk: oczekiwano mapy")
    if vfd is not None and not isinstance(vfd, dict):
        raise PlantConfigError(f"{path}: vfd: oczekiwano mapy")
    tools_raw = section("tools")
    try:
        cfg = PlantConfig(
            machine=rel(data.get("machine")), listen=str(net.get("listen", "127.0.0.1")),
            port=int(net.get("port", PORT)), cycle_ns=int(timing.get("cycle_ns", 1_000_000)),
            substeps=int(timing.get("substeps", DEFAULT_SUBSTEPS)),
            watchdog_ms=float(timing.get("watchdog_ms", 50)),
            mode=str(data.get("mode", "lockstep")), seed=int(data.get("seed", 1)),
            state_file=rel(data.get("state_file")),
            trace_path=rel(trace.get("path")), trace_format=str(trace.get("format", "csv")),
            oracle_arm_bit=(None if oracle.get("arm_bit", 31) is None
                            else int(oracle.get("arm_bit", 31))),
            tools={int(k): ToolSpec(float((v or {}).get("length", 50.0)),
                                    float((v or {}).get("diameter", 6.0)))
                   for k, v in tools_raw.items()},
            vfd=None if vfd is None else VfdConfig.from_dict(vfd, base),
            panel_listen=str(net.get("panel_listen", "127.0.0.1")),
            panel_port=int(net.get("panel_port", PANEL_PORT)),
            telemetry_ms=float(panel.get("telemetry_ms", 5.0)),
            desk=None if desk is None else DeskConfig.from_dict(desk))
    except (TypeError, ValueError) as exc:
        raise PlantConfigError(f"{path}: zły typ wartości ({exc})") from None
    cfg.check()
    return cfg


@dataclass
class Stats:
    received: int = 0
    rejected: int = 0
    lost: int = 0
    late: int = 0
    steps: int = 0
    _gaps: deque = field(default_factory=lambda: deque(maxlen=JITTER_WINDOW), repr=False)

    @property
    def jitter_us(self) -> int:
        """Średnia ruchoma |odstęp − cycle_ns| z ostatnich 100 ramek [µs]."""
        return int(sum(self._gaps) / len(self._gaps) / 1000) if self._gaps else 0

    def reset(self) -> None:
        self.received = self.rejected = self.lost = self.late = 0
        self._gaps.clear()


def _spindle_template(mcfg) -> dict | None:
    """Parametry instancji napędu wrzeciona z domyślnej biblioteki (None = brak/niezgodność)."""
    from linumert.machine.schema import MachineConfigError

    from .drive_library import TemplateError, load_library
    from .machine_drives import resolve_machine_drives

    try:
        inst = resolve_machine_drives(mcfg, load_library()).get(mcfg.spindle.drive)
    except (MachineConfigError, TemplateError):
        return None
    return None if inst is None else inst.params


class PlantServer:
    """Protokół LRT-NET nad uruchomioną maszyną (`PlantMachine`)."""

    def __init__(self, machine: PlantMachine, config: PlantConfig | None = None,
                 trace: TraceWriter | None = None, spindle_template: dict | None = None,
                 drive_params: dict[str, dict] | None = None):
        """`drive_params`: parametry instancji napędów (szablon + overrides) dla zmian live."""
        self.machine = machine
        self.cfg = config or PlantConfig()
        self.cfg.check()
        self.trace = trace
        model = machine.model
        self.drives = [d for d in model.drives if d != model.spindle]
        self.stats = Stats()
        self.messages: deque[str] = deque(maxlen=200)
        self.watchdog_tripped = False
        self._reset_seen = False
        self.model_failed = False
        self._digest = hashlib.sha256()
        self._last_seq: int | None = None
        self._last_time: int | None = None  # time_ns ostatniej ramki z krokiem
        self._last_rx: int | None = None  # zegar odbioru (lockstep: time_ns, realtime: host)
        self._last_wall: int | None = None  # zegar hosta ostatniej przyjętej ramki (sesja 025)
        self._mode = {d: None for d in self.drives}
        self.mode_rejects = 0
        self._target = {d: 0 for d in self.drives}
        self.oracle = Oracle.for_machine(machine, self.drives, self.cfg.oracle_arm_bit)
        mcfg = model.config
        self.atc = ToolChangerModel.from_config(mcfg, self.cfg.tools)
        self.toolsetter = ToolSetterModel.from_config(mcfg)
        self.collisions = CollisionModel.from_config(mcfg)
        # długość narzędzia w modelu C (koniec narzędzia z kinematyki): sonda albo narzędzie z ATC
        self._tool_len = mcfg.probe.tip_length if mcfg.probe is not None else 0.0
        self._extra_inputs = (0, 0)
        self.events: list = []
        # wrzeciono z falownikiem (sesja 021): szablon napędu wrzeciona z machine.yaml
        if spindle_template is None:
            spindle_template = _spindle_template(mcfg)
        self.spindle = SpindleModel.from_machine(mcfg, spindle_template)
        self.vfd_faults = VfdFaults()
        self._estop = self._estop_input()
        # drugi kanał E-STOP (NC, ten sam grzyb, druga linia przewodów; hal/lrt_estop2.comp)
        self._estop_b = self.machine.model.inputs.get("estop_b")
        self._lock = threading.Lock()
        self._stop = threading.Event()
        # panel (sesja 022): parametry live, telemetria, pulpit
        self.live = {d: LiveParams(p) for d, p in (drive_params or {}).items() if d in self.drives}
        self.live_base = {d: lp.params for d, lp in self.live.items()}
        self.scale = {d: machine.counts_per_unit(d) or 1.0 for d in self.drives}
        self._letters = {d: machine.drive_letter(d) for d in self.drives}
        self.telemetry = Telemetry(self.drives, period_s=self.cfg.telemetry_ms / 1000.0)
        self.desk = None
        if self.cfg.desk is not None:
            problems = self.cfg.desk.problems(getattr(getattr(mcfg, "io", None), "inputs", None))
            if problems:
                raise PlantConfigError("; ".join(problems))
            self.desk = Desk(self.cfg.desk)
        # awarie (sesja 024): stan czytany w pętli ramek, API w `faults.Faults`
        self.fault_state = FaultState(rng=random.Random(self.cfg.seed))
        self.faults = Faults(self)

    # ---- pomocnicze --------------------------------------------------------------------
    def _estop_input(self) -> tuple[int, bool] | None:
        cfg = self.machine.model.config
        estop = getattr(getattr(cfg, "io", None), "estop", None)
        if estop is None or estop.input not in self.machine.model.inputs:
            return None
        return self.machine.model.inputs[estop.input], estop.contact == "NC"

    def _note(self, text: str) -> None:
        self.messages.append(text)
        log.warning(text)

    @property
    def digest(self) -> str:
        """SHA-256 wszystkich wysłanych odpowiedzi (ślad przebiegu, REQ-QA-04)."""
        return self._digest.hexdigest()

    # ---- watchdog i stan bezpieczny ----------------------------------------------------
    def trip_watchdog(self, gap_ms: float) -> None:
        """Brak ramek > watchdog_ms → wszystkie napędy w fault (E-4003), wyjścia bezpieczne.

        Awaria jest jednorazowa (nie trwała): wznowienie ramek jej nie kasuje, kasuje ją
        dopiero fault reset mastera (bit 7 słowa sterującego), docs/PLANT.md §3 reguła 4.
        """
        if self.watchdog_tripped:
            return
        self.watchdog_tripped = True
        self._reset_seen = False
        for drive in self.drives:
            self.machine.inject_fault(drive, FAULT_COMM_WATCHDOG, sticky=False)
        self.machine.set_outputs(0)
        if self.cfg.vfd is None:
            self.spindle.set_speed(0.0, False)  # wrzeciono zadawane przez LRT-NET
        self._note(f"E-4003: brak ramek magistrali przez {gap_ms:.0f} ms; napędy w stan błędu")

    def check_watchdog(self, now_ns: int | None = None) -> bool:
        """Sprawdzenie bez ramki (tryb realtime, pętla bezczynna). True = zadziałał."""
        if self.cfg.mode != "realtime" or self._last_rx is None:
            return False
        now = time.monotonic_ns() if now_ns is None else now_ns
        gap_ms = (now - self._last_rx) / 1e6
        if gap_ms > self.cfg.watchdog_ms:
            with self._lock:
                self.trip_watchdog(gap_ms)
            return True
        return False

    def safe_state(self, reason: str) -> None:
        """Wyjątek modelu: napędy wyłączone (disable voltage), wyjścia zerowe, bez kroków."""
        self.model_failed = True
        for drive in self.drives:
            try:
                self.machine.set_controlword(drive, 0)
            except Exception:  # noqa: BLE001 - model już niespójny; stan bezpieczny ważniejszy
                pass
        try:
            self.machine.set_outputs(0)
        except Exception:  # noqa: BLE001
            pass
        self.spindle.set_speed(0.0, False)
        self._note(f"E-4200: błąd modelu Plant ({reason}); napędy wyłączone, "
                   "wymagany restart Plant")

    # ---- protokół ----------------------------------------------------------------------
    def nose(self) -> tuple[float, float, float]:
        """Nos wrzeciona w G53 (koniec narzędzia względem stołu + bieżąca długość narzędzia)."""
        x, y, z = self.machine.tool_tip(workpiece=True)
        return (x, y, z + self._tool_len)

    def _sync_tool_length(self) -> None:
        if self.atc.type == "manual" and not self.atc.events:
            return  # bez ATC i bez ręcznej wymiany: długość z sondy (sesja 014)
        spec = self.atc.tool_spec()
        length = spec.length if spec is not None else 0.0
        if length != self._tool_len:
            self.machine.set_tool_length(length)
            self._tool_len = length

    def _step_discrete(self, dt: float, outputs: int) -> None:
        """Wrzeciono, magazyn, czujnik długości, kolizje (REQ-VM-08…10) po kroku modelu C."""
        self.spindle.step(dt)
        nose = self.nose()
        fresh = list(self.atc.step(dt, nose, outputs))
        self._sync_tool_length()
        fresh += self.collisions.check(dt, nose, self.atc.tool_spec(),
                                       exchange_aligned=self.atc.aligned(nose) is not None)
        mask, value = self.atc.inputs()
        if self.toolsetter is not None:
            tip = self.machine.tool_tip(workpiece=True)
            m2, v2 = self.toolsetter.inputs(tip)
            mask, value = mask | m2, (value & ~m2) | v2
        self._extra_inputs = (mask, value)
        for ev in fresh:
            self.events.append(ev)
            if len(self.events) <= 50:
                self._note(f"{ev.kind}: {getattr(ev, 'detail', '') or getattr(ev, 'pair', '')} "
                           f"przy {ev.position}")

    def manual_tool_change(self, tool: int | None) -> None:
        """Operator zmienia narzędzie ręcznie (REQ-VM-09); poza pozycją wymiany → zdarzenie."""
        with self._lock:
            ev = self.atc.manual_change(tool, self.nose())
            self._sync_tool_length()
            if ev is not None:
                self.events.append(ev)
                self._note(f"{ev.kind}: {ev.detail} przy {ev.position}")

    def report(self) -> dict:
        """Raport przebiegu (statystyki LRT-NET i wyrocznia REQ-VM-06) do pliku JSON."""
        s = self.stats
        return {"machine": self.machine.model.name, "frames": s.received,
                "rejected": s.rejected, "lost": s.lost, "late": s.late, "steps": s.steps,
                "watchdog_tripped": self.watchdog_tripped, "model_failed": self.model_failed,
                "digest": self.digest, "oracle": self.oracle.report(),
                "events": [asdict(e) for e in self.events[:500]],
                "machine_events": sorted(self.machine.events()),
                "drive_states": {d: self.machine.drive_state(d) for d in self.drives},
                "faults_active": self.faults.active(),
                "spindle_tool": self.atc.spindle_tool, "slots": list(self.atc.slots),
                "spindle": {"rpm": round(self.spindle.rpm, 1), "fault": self.spindle.fault}}

    def handle(self, frame: bytes, now_ns: int | None = None) -> bytes | None:
        """Jedna ramka master→plant. Zwraca odpowiedź albo None (ramka odrzucona)."""
        with self._lock:
            if self.fault_state.drop():  # awaria frame_loss: ramka „nie dotarła”
                return None
            return self._handle(frame, now_ns)

    def _handle(self, frame: bytes, now_ns: int | None) -> bytes | None:
        try:
            cmd = decode_command(frame)
            if len(cmd.axes) != len(self.drives):
                raise FrameError(f"ramka ma {len(cmd.axes)} osi, maszyna {len(self.drives)}")
        except FrameError as exc:
            self.stats.rejected += 1
            if self.stats.rejected <= 10 or self.stats.rejected % 1000 == 0:
                self._note(f"odrzucona ramka ({self.stats.rejected}.): {exc}")
            return None
        self.stats.received += 1
        if cmd.flags & FLAG_RESET_STATS:
            self.stats.reset()
        rx = cmd.time_ns if self.cfg.mode == "lockstep" else (
            time.monotonic_ns() if now_ns is None else now_ns)

        step = True
        wall = time.monotonic_ns()
        if self._last_seq is not None:
            delta = seq_delta(cmd.seq, self._last_seq)
            if (delta <= 0 and self._last_wall is not None
                    and (wall - self._last_wall) / 1e6 > self.cfg.watchdog_ms):
                # Nowa sesja mastera (restart LinuxCNC przy działającym Plant, VM-B jako usługa):
                # lrt_net numeruje od 1: po przerwie > watchdog_ms numeracja liczy się od nowa.
                self._note(f"nowa sesja mastera: seq {cmd.seq} po {self._last_seq}, "
                           f"przerwa {(wall - self._last_wall) / 1e6:.0f} ms")
                self._last_seq = self._last_time = self._last_rx = None
                delta = 1
            if delta <= 0:
                self.stats.late += 1
                step = False
            else:
                self.stats.lost += delta - 1
        if step:
            if self._last_rx is not None:
                gap = rx - self._last_rx
                if gap / 1e6 > self.cfg.watchdog_ms:
                    self.trip_watchdog(gap / 1e6)
                self.stats._gaps.append(abs(gap - self.cfg.cycle_ns))
            dt_ns = self.cfg.cycle_ns if self._last_time is None else cmd.time_ns - self._last_time
            dt_ns = min(max(dt_ns, DT_MIN), DT_MAX)
            self._last_seq, self._last_time, self._last_rx = cmd.seq, cmd.time_ns, rx
            self._last_wall = wall
            if not self.model_failed:
                try:
                    self._apply(cmd)
                    sub = self.cfg.substeps
                    self.machine.step_cycle(dt_ns / 1e9, sub)
                    self.stats.steps += 1
                    for v in self.oracle.check(self.machine, cmd, self.drives):
                        if self.oracle.total <= 20:
                            self._note(f"ORACLE_VIOLATION {v.kind} {v.name}: {v.detail} "
                                       f"(ramka {v.seq})")
                    self._step_discrete(dt_ns / 1e9, cmd.digital_out)
                    if self.desk is not None:
                        self.desk.step(dt_ns / 1e9)
                    self._sample()
                except Exception as exc:  # noqa: BLE001 - REQ-QA-03: proces nie może upaść
                    self.safe_state(f"{type(exc).__name__}: {exc}")
        reply = encode_reply(self._reply(cmd.seq, cmd.time_ns))
        self._digest.update(reply)
        return reply

    def _apply(self, cmd) -> None:
        m = self.machine
        for drive, axis in zip(self.drives, cmd.axes, strict=True):
            if axis.mode != self._mode[drive] and axis.mode != 0:
                # 0 = „brak trybu” (np. pierwszy cykl mastera): bez zmiany. Tryb nieobsługiwany
                # przez model napędu jest odrzucany jak zapis do 6060h w napędzie: zostaje
                # poprzedni, bez wyłączania Plant (REQ-QA-03).
                try:
                    m.set_mode(drive, axis.mode)
                    self._mode[drive] = axis.mode
                except ValueError as exc:
                    self.mode_rejects += 1
                    if self.mode_rejects == 1:
                        self._note(f"6060h odrzucony ({exc}); naped zostaje w poprzednim trybie")
            if axis.mode == MODE_CSP:
                m.set_target(drive, axis.target_pos)
                self._target[drive] = axis.target_pos
            m.set_controlword(drive, axis.controlword)
            if axis.controlword & CW_FAULT_RESET:
                self._reset_seen = True
        # Po watchdogu wyjścia zostają bezpieczne do fault resetu (zwolnienie w `_reply`).
        m.set_outputs(0 if self.watchdog_tripped else cmd.digital_out)
        if self.cfg.vfd is None and not self.watchdog_tripped:
            self.spindle.set_speed(cmd.spindle_cmd, cmd.spindle_cmd != 0.0)

    def _reply(self, seq: int, time_ns: int) -> Reply:
        m = self.machine
        axes = []
        fault = False
        for drive in self.drives:
            if self.model_failed:
                axes.append(AxisReply(statusword=SW_FAULT, error_code=ERR_MODEL))
                fault = True
                continue
            sw = m.statusword(drive)
            actual = m.position_actual(drive)
            mode = self._mode[drive] if self._mode[drive] is not None else MODE_CSP
            ferr = self._target[drive] - actual if mode == MODE_CSP else 0
            fault |= bool(sw & SW_FAULT)
            axes.append(AxisReply(statusword=sw, mode_display=m.od_read(drive, 0x6061),
                                  actual_pos=actual, following_error=ferr,
                                  torque_pct=m.torque_actual(drive),
                                  error_code=m.drive_error_code(drive)))
        if self.watchdog_tripped and self._reset_seen and not fault:
            self.watchdog_tripped = False
            self._note("E-4003 skasowany: napędy po fault reset, wyjścia zwolnione")
        mask, value = self._extra_inputs  # magazyn, czujnik długości (sesja 020)
        inputs = (m.inputs & ~mask) | value
        if self.desk is not None:  # wirtualny pulpit (sesja 022)
            mask, value = self.desk.inputs()
            inputs = (inputs & ~mask) | value
        if self._estop is not None and self._estop_b is not None:  # kanał B = kanał A
            a = inputs >> self._estop[0] & 1
            inputs = (inputs & ~(1 << self._estop_b)) | (a << self._estop_b)
        if self.fault_state.forced:  # awarie limit / atc_sensor / estop_channel (sesja 024)
            mask, value = self.fault_state.inputs()
            inputs = (inputs & ~mask) | value
        flags = FLAG_FAULT if fault else 0
        if self._estop is not None:
            bit, nc = self._estop
            closed = bool(inputs >> bit & 1)
            if closed != nc:
                flags |= FLAG_ESTOP_OPEN
        if self.trace is not None:
            self.trace.put(seq, time_ns, axes)
        return Reply(seq=seq, time_ns=time_ns, axes=axes, digital_in=inputs,
                     spindle_actual=self.spindle.rpm,
                     frames_lost=self.stats.lost, frames_late=self.stats.late,
                     jitter_us=self.stats.jitter_us, flags=flags)

    # ---- panel (sesja 022) -------------------------------------------------------------
    def _sample(self) -> None:
        """Próbka telemetrii co `telemetry_ms` czasu modelu (bez I/O; panel czyta kopię)."""
        m = self.machine
        t = m.time
        if not self.telemetry.due(t):
            return
        values: list[float] = []
        for d in self.drives:
            k = self.scale[d]
            act = m.position_actual(d)
            cmd = self._target[d] if (self._mode[d] or MODE_CSP) == MODE_CSP else act
            values += (cmd / k, act / k, (cmd - act) / k, m.torque_actual(d),
                       m.joint_velocity(self._letters[d]), m.lost_steps(d))
        self.telemetry.put(t, tuple(values))

    def reload_machine(self, machine: PlantMachine, drive_params: dict[str, dict]) -> None:
        """Nowy model maszyny bez restartu Plant (edytor panelu, sesja 023, REQ-VM-12).

        Wywołujący sprawdza, że napędy są wyłączone. Liczba i nazwy napędów LRT-NET muszą
        zostać (ramki mastera mają stałą liczbę osi); statystyki, ślad i ustawienia zostają,
        a modele zależne od maszyny (wyrocznia, magazyn, kolizje, wrzeciono, live) powstają
        od nowa. Aktywne awarie są zdejmowane.
        """
        fresh = PlantServer(machine, self.cfg, spindle_template=_spindle_template(
            machine.model.config), drive_params=drive_params)
        if fresh.drives != self.drives:
            raise PlantConfigError(f"zmieniona lista napędów LRT-NET ({', '.join(fresh.drives)} "
                                   f"zamiast {', '.join(self.drives)}) — wymagany restart Plant")
        self.faults.clear_all()
        with self._lock:
            for name in ("machine", "oracle", "atc", "toolsetter", "collisions", "_tool_len",
                         "spindle", "live", "live_base", "scale", "_letters", "_estop", "_estop_b",
                         "_extra_inputs"):
                setattr(self, name, getattr(fresh, name))
            self._mode = {d: None for d in self.drives}
            self._target = {d: 0 for d in self.drives}
            self.events.clear()
            self._note(f"model przeładowany: {machine.model.name}")

    def live_values(self) -> dict[str, dict[str, float]]:
        """Bieżące wartości parametrów live każdego napędu osi."""
        with self._lock:
            return {d: {p: lp.get(p) for p in lp.params["live"]} for d, lp in self.live.items()}

    def set_live(self, drive: str, path: str, value) -> dict:
        """Zmiana parametru live (REQ-VD-04): walidacja szablonu, rdzeń C, dziennik z czasem.

        Błąd (`TemplateError`, `KeyError`, `ValueError`) nie zmienia modelu ani dziennika.
        """
        with self._lock:
            return self._set_live(drive, path, value)

    def _set_live(self, drive: str, path: str, value) -> dict:
        if drive not in self.live:
            raise KeyError(f"napęd {drive} bez parametrów live (znane: {', '.join(self.live)})")
        live = self.live[drive]
        params, log_len = live.params, len(live.log)
        record = live.set(path, value, t=self.machine.time)
        target, c_value = live.c_command(path, record.new)
        try:
            self.machine.set_live(drive, target, c_value)
        except RuntimeError as exc:
            live.params = params
            del live.log[log_len:]
            raise ValueError(f"{drive} {path}: rdzeń C odrzucił zmianę ({exc})") from None
        self.messages.append(f"live {drive} {path}: {record.old} → {record.new} "
                             f"(t = {record.t:.3f} s)")
        return {"drive": drive, **record._asdict()}

    def apply_live(self, values: dict[str, dict[str, float]]) -> list[dict]:
        """Preset: najpierw walidacja wszystkich zmian na kopiach, potem zapis do modelu."""
        with self._lock:
            for drive, changes in values.items():
                if drive not in self.live:
                    raise KeyError(f"napęd {drive} bez parametrów live")
                probe = LiveParams(self.live[drive].params)
                for path, value in changes.items():
                    probe.set(path, value, t=0.0)
            done = []
            for drive, changes in values.items():
                for path, value in changes.items():
                    if self.live[drive].get(path) != value:
                        done.append(self._set_live(drive, path, value))
            return done

    def live_log(self) -> list[dict]:
        """Dziennik zmian live wszystkich napędów, chronologicznie."""
        with self._lock:
            out = [{"drive": d, **r._asdict()} for d, lp in self.live.items() for r in lp.log]
        return sorted(out, key=lambda r: r["t"])

    # ---- UDP ---------------------------------------------------------------------------
    def bind(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.cfg.listen, self.cfg.port))
        return sock

    def serve(self, sock: socket.socket, max_frames: int | None = None) -> None:
        """Pętla odbioru do `stop()` (albo `max_frames` przyjętych ramek)."""
        poll = max(self.cfg.watchdog_ms / 4000.0, 0.001)
        sock.settimeout(poll)
        delayed: deque[tuple[float, bytes, Any]] = deque()  # awaria delay (sesja 024)
        while not self._stop.is_set():
            while delayed and delayed[0][0] <= time.monotonic():
                _due, data, to = delayed.popleft()
                with contextlib.suppress(OSError):
                    sock.sendto(data, to)
            if delayed:
                sock.settimeout(min(poll, max(delayed[0][0] - time.monotonic(), 0.0001)))
            try:
                frame, addr = sock.recvfrom(2048)
            except TimeoutError:
                sock.settimeout(poll)
                self.check_watchdog()
                continue
            except OSError as exc:  # np. ICMP port unreachable od mastera
                if self._stop.is_set():
                    break
                self._note(f"błąd gniazda: {exc}")
                continue
            reply = self.handle(frame, time.monotonic_ns())
            if reply is not None and (self.fault_state.delay_ms > 0 or delayed):
                delayed.append((time.monotonic() + self.fault_state.delay_ms / 1000.0,
                                reply, addr))
            elif reply is not None:
                try:
                    sock.sendto(reply, addr)
                except OSError as exc:
                    self._note(f"nie wysłano odpowiedzi do {addr}: {exc}")
            if max_frames is not None and self.stats.received >= max_frames:
                break

    def stop(self) -> None:
        self._stop.set()
