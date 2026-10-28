"""Modele danych API (pydantic) — wspólny słownik dla REST, WebSocket, CLI, SDK i GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Każda operacja kontraktu ma model żądania i model wyniku zdefiniowany **tutaj**, a nie
w transporcie. Dzięki temu:

- ``GET /api/v1/contract`` oddaje schematy JSON gotowe do codegen w dowolnym języku,
- CLI i SDK walidują te same dane co serwer (ten sam model),
- przyszłe GUI (web, Tauri, Electron, Qt, mobilne) nie wymyśla własnych typów.

Konwencje:
- jednostki zawsze w mm / mm·min⁻¹ / obr·min⁻¹ / s (kontrakt precyzji CLAUDE.md §4),
- wartości nieograniczone (``inf``) idą jako ``null``, bo JSON nie zna nieskończoności,
- nazwy pól wężowe (``snake_case``) — tak samo w JSON.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1

AxisName = Literal["X", "Y", "Z", "A", "B", "C", "U", "V", "W"]
TaskState = Literal["estop", "estop_reset", "off", "on"]
MachineMode = Literal["manual", "auto", "mdi"]
InterpState = Literal["idle", "reading", "paused", "waiting"]
OpStatus = Literal["implemented", "planned"]


def finite(value: float) -> float | None:
    """``inf``/``nan`` → ``None`` (JSON nie zna nieskończoności)."""
    return value if math.isfinite(value) else None


class Model(BaseModel):
    """Baza: zakaz nadmiarowych pól, żeby literówka w GUI nie przeszła po cichu."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Empty(Model):
    """Operacje bez parametrów i bez wyniku merytorycznego."""


class Ok(Model):
    """Standardowy wynik polecenia: potwierdzenie i opcjonalny komunikat dla operatora."""

    ok: bool = True
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- maszyna


class AxisState(Model):
    name: AxisName
    position: float = Field(description="pozycja rzeczywista [mm] w układzie maszynowym")
    commanded: float = Field(description="pozycja zadana [mm]")
    work_position: float = Field(description="pozycja w układzie detalu [mm]")
    following_error: float
    homed: bool
    soft_min: float | None = None
    soft_max: float | None = None
    limit_hit: bool = False


class SpindleState(Model):
    speed: float = 0.0
    direction: int = 0
    override: float = 1.0
    running: bool = False


class MachineState(Model):
    """Pełna migawka maszyny — to GUI rysuje jako DRO, status i pasek programu."""

    schema_version: int = SCHEMA_VERSION
    fresh: bool = Field(description="czy migawka jest świeża (backend odpowiada)")
    age_s: float = 0.0
    task_state: TaskState = "estop"
    mode: MachineMode = "manual"
    interp_state: InterpState = "idle"
    axes: list[AxisState] = Field(default_factory=list)
    all_homed: bool = False
    current_line: int = 0
    program: str = ""
    feed_override: float = 1.0
    rapid_override: float = 1.0
    spindle: SpindleState = Field(default_factory=SpindleState)
    tool_number: int = 0
    work_offset_name: str = "G54"
    work_offset: dict[str, float] = Field(default_factory=dict)
    gcodes: list[str] = Field(default_factory=list)
    mcodes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    backend: str = ""


class JogRequest(Model):
    axis: AxisName
    speed: float = Field(description="mm/s; 0 = zatrzymanie jogu tej osi")
    session: str = Field("", description="identyfikator sesji — deadman jogu")

    @field_validator("speed")
    @classmethod
    def _speed(cls, v: float) -> float:
        if not -50.0 <= v <= 50.0:
            raise ValueError("prędkość jogu poza zakresem ±50 mm/s")
        return v


class JogIncrementRequest(Model):
    axis: AxisName
    speed: float = Field(gt=0, le=50.0)
    distance: float = Field(gt=0, description="krok przyrostowy [mm]")


class JogStopRequest(Model):
    axis: AxisName | None = Field(None, description="None = zatrzymaj wszystkie osie")


class ModeRequest(Model):
    mode: MachineMode


class HomeRequest(Model):
    axis: AxisName | None = Field(None, description="None = bazuj wszystkie osie")


class MdiRequest(Model):
    text: str = Field(min_length=1, max_length=200)


class RunRequest(Model):
    from_line: int = Field(1, ge=0)


class OverrideRequest(Model):
    feed: float | None = Field(None, gt=0, le=3.0, description="1.0 = 100 %")
    rapid: float | None = Field(None, gt=0, le=3.0)
    spindle: float | None = Field(None, gt=0, le=3.0)


class SpindleRequest(Model):
    speed: float = Field(ge=0, description="obr/min; 0 = zatrzymanie")
    direction: Literal[-1, 0, 1] = 1


class WorkOffsetRequest(Model):
    name: str = Field(pattern=r"^G5[4-9](\.[1-3])?$")
    values: dict[AxisName, float] = Field(default_factory=dict)


class AxisList(Model):
    axes: list[AxisName] = Field(default_factory=list)


# --------------------------------------------------------------------------- programy


class ProgramSummary(Model):
    name: str
    path: str
    kind: Literal["ngc", "lnx", "other"] = "other"
    size: int = 0
    modified: float = 0.0


class ProgramList(Model):
    root: str
    programs: list[ProgramSummary] = Field(default_factory=list)


class ProgramName(Model):
    name: str


class ProgramRead(Model):
    name: str
    path: str
    text: str


class ProgramWriteRequest(Model):
    name: str
    text: str
    overwrite: bool = False


class ProgramText(Model):
    name: str = ""
    text: str


class ViolationOut(Model):
    """Przekroczenie granicy osi.

    Kształt odpowiada ``linumert.programs.limits.Violation``: jest jeden przekroczony
    ``limit`` i ``side`` mówiąca, która strona (min/max) — nie para min/max.
    """

    axis: str
    line: int
    value: float
    limit: float = Field(description="przekroczony limit osi [mm/°]")
    side: str = Field("", description="min | max")
    count: int = Field(1, description="ile ruchów przekracza tę samą stronę limitu")
    message: str = ""


class LimitReportOut(Model):
    ok: bool
    violations: list[ViolationOut] = Field(default_factory=list)
    lines: int = 0
    program: str = ""
    moves: int = 0
    interpreter: str = Field("", description="rs274 (pełny LinuxCNC) albo subset (bez LinuxCNC)")


class CheckRequest(Model):
    name: str = Field("", description="program z katalogu nc_files albo puste przy text")
    text: str = ""
    ini: str = ""


class EstimateOut(Model):
    ok: bool = True
    source: str = Field("", description="rs274 (LinuxCNC) albo subset (szacunek "
                                        "bez przyspieszeń)")
    seconds: float = 0.0
    distance_mm: float = 0.0
    rapid_mm: float = 0.0
    feed_mm: float = 0.0
    tools: list[int] = Field(default_factory=list)
    message: str = ""


class EstimateRequest(Model):
    name: str = ""
    text: str = ""
    ini: str = ""


class ToolpathPoint(Model):
    line: int
    x: float
    y: float
    z: float
    rapid: bool
    feed: float


class ToolpathOut(Model):
    """Polilinia ścieżki: GUI rysuje z punktów (backend bez OpenGL)."""

    ok: bool = True
    unit: str = "mm"
    source: str = Field("", description="rs274 (LinuxCNC) albo subset (interpreter rdzenia)")
    points: list[ToolpathPoint] = Field(default_factory=list)
    bounds: dict[str, float] = Field(default_factory=dict)
    length_mm: float = 0.0
    notes: list[str] = Field(default_factory=list)
    message: str = ""


class ToolpathRequest(Model):
    name: str = ""
    text: str = ""
    max_points: int = Field(20000, ge=10, le=200000)


class LnxCompileRequest(Model):
    name: str = Field(description="program .lnx w katalogu nc_files")
    save: bool = Field(False, description="zapisz wynik .ngc obok źródła")


class CompileOut(Model):
    ok: bool = True
    name: str = ""
    gcode: str = ""
    path: str = ""
    message: str = ""


class StepEditRequest(Model):
    name: str
    line: int = Field(ge=1)
    changes: dict[str, float] = Field(default_factory=dict,
                                       description="słowo G-code → nowa wartość")


# --------------------------------------------------------------------------- narzędzia


class ToolOut(Model):
    number: int
    pocket: int = 0
    type: str | None = None
    description: str = ""
    holder: str = ""
    diameter: float | None = None
    params: dict[str, float] = Field(default_factory=dict)
    offsets: dict[str, float] = Field(default_factory=dict)
    life_min: float | None = None
    used_min: float = 0.0


class ToolList(Model):
    tools: list[ToolOut] = Field(default_factory=list)
    path: str = ""


class ToolNumber(Model):
    number: int = Field(ge=0)


class ToolUpsertRequest(Model):
    number: int = Field(ge=0)
    pocket: int = 0
    type: str | None = None
    description: str = ""
    holder: str = ""
    diameter: float | None = None
    params: dict[str, float] = Field(default_factory=dict)
    offsets: dict[str, float] = Field(default_factory=dict)
    life_min: float | None = None


class ToolWearRequest(Model):
    number: int = Field(ge=0)
    axis: Literal["X", "Y", "Z"] = "Z"
    value: float


class ToolTblOut(Model):
    path: str = ""
    text: str = ""
    units: str = "mm"


class ToolTblRequest(Model):
    units: Literal["mm", "inch"] = "mm"
    path: str = ""


# --------------------------------------------------------------------------- CAM


class CamOperation(Model):
    name: str
    version: int
    summary: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class CamCatalog(Model):
    operations: list[CamOperation] = Field(default_factory=list)


class CamGenerateRequest(Model):
    operation: str
    version: int = Field(0, description="0 = najnowsza wersja generatora")
    parameters: dict[str, Any] = Field(default_factory=dict)


class CamGenerateOut(Model):
    ok: bool = True
    operation: str = ""
    version: int = 0
    gcode: str = ""
    message: str = ""


# --------------------------------------------------------------------------- symulacja


class SimRunRequest(Model):
    program: str = Field("", description="G-code jako tekst (albo puste i wtedy name)")
    name: str = Field("", description="nazwa programu z katalogu nc_files")
    stock: str = Field("", description="przygotówka: 'BOX X100 Y80 Z20' albo pełna linia ;@STOCK")
    tools: list[tuple[int, float, float]] = Field(default_factory=list)
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rapid: float = 5000.0
    dt: float = Field(0.05, gt=0, le=1.0)


class SimResultOut(Model):
    """Wynik symulacji jako dane — GUI rysuje podgląd u siebie (backend bez OpenGL)."""

    ok: bool = True
    volume_removed_mm3: float = 0.0
    seconds: float = 0.0
    rapid_seconds: float = 0.0
    feed_seconds: float = 0.0
    length_mm: float = 0.0
    lines: int = 0
    segments: int = 0
    collisions: list[list[str]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    bounds: dict[str, float] = Field(default_factory=dict)
    stock_line: str = ""
    cache_key: str = ""
    message: str = ""


# --------------------------------------------------------------------------- Plant


class PlantStatus(Model):
    running: bool = False
    machine: str = ""
    listen: str = ""
    port: int = 0
    mode: str = ""
    frames: int = 0
    rejected: int = 0
    lost: int = 0
    late: int = 0
    message: str = ""


class PlantStartRequest(Model):
    machine: str = Field(description="nazwa maszyny z config/machines albo ścieżka YAML")
    plant: str = Field("", description="ścieżka plant.yaml (opcjonalnie)")
    mode: Literal["lockstep", "realtime"] = "lockstep"
    listen: str = "127.0.0.1"
    port: int = Field(0, ge=0, le=65535, description="0 = port wybrany przez system")


class ScenarioRunRequest(Model):
    scenario: str = Field(description="nazwa albo ścieżka scenariusza YAML")
    machine: str = ""


class ScenarioResultOut(Model):
    ok: bool = True
    name: str = ""
    passed: bool = False
    criteria: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    report_html: str = ""
    message: str = ""


class ScenarioList(Model):
    root: str = ""
    scenarios: list[str] = Field(default_factory=list)


class FaultCatalogItem(Model):
    """Rodzaj awarii, którą można wstrzyknąć w Plant (``plant.fault_set``)."""

    kind: str
    desc: str = ""
    params: list[str] = Field(default_factory=list)


class PlantFaultsOut(Model):
    active: list[dict[str, Any]] = Field(default_factory=list)
    catalog: list[FaultCatalogItem] = Field(default_factory=list)


class MachineDrivesOut(Model):
    """Rozwiązane napędy maszyny: szablon z biblioteki plus nadpisania z machine.yaml."""

    machine: str
    axes: list[str] = Field(default_factory=list)
    drives: dict[str, dict[str, Any]] = Field(default_factory=dict)


class DriveTemplateOut(Model):
    id: str
    kind: str = ""
    summary: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class DriveLibrary(Model):
    root: str = ""
    templates: list[DriveTemplateOut] = Field(default_factory=list)


class TelemetryOut(Model):
    """Próbki telemetrii Plant: kolumny (nazwy kanałów) i wiersze próbek."""

    drive: str = ""
    cursor: int = 0
    columns: dict[str, Any] = Field(default_factory=dict)
    samples: list[list[float]] = Field(default_factory=list)


class PlantLiveRequest(Model):
    drive: str = ""
    parameters: dict[str, float] = Field(default_factory=dict)


class PlantFaultRequest(Model):
    """Wstrzyknięcie albo zdjęcie awarii w Plant.

    Katalog (``plant.faults``) ma rodzaje o różnych parametrach: ``drive_fault`` chce
    ``drive`` i ``code``, ``frame_loss`` — ``percent``, ``delay`` — ``ms``, ``limit``
    i ``atc_sensor`` — ``input``/``closed``, ``axis_jam`` — ``axis``. Poprzedni schemat
    miał tylko pole ``drive``, które usługa przekazywała jako ``target``, więc żaden
    rodzaj z parametrami nie dawał się wstrzyknąć.
    """

    kind: str = Field(description="rodzaj awarii z katalogu plant.faults")
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict,
                                   description="parametry rodzaju, np. drive, code, percent, ms")


class PlantTelemetryRequest(Model):
    drive: str = ""
    limit: int = Field(500, ge=1, le=20000)


# --------------------------------------------------------------------------- diagnostyka


class DiagDoctor(Model):
    ok: bool = True
    entries: list[dict[str, Any]] = Field(default_factory=list)
    report: str = ""


class DiagJournalRequest(Model):
    limit: int = Field(200, ge=1, le=10000)
    kind: str = ""


class DiagJournalOut(Model):
    entries: list[dict[str, Any]] = Field(default_factory=list)
    warning: str = ""


class Cia402Request(Model):
    statusword: int = Field(ge=0, le=0xFFFF)
    error_code: int = Field(0, ge=0, le=0xFFFF)


class Cia402Out(Model):
    state: str = ""
    description: str = ""
    flags: dict[str, bool] = Field(default_factory=dict)
    error_text: str = ""


# --------------------------------------------------------------------------- konfiguracja


class MachineConfigSummary(Model):
    name: str
    path: str
    axes: list[str] = Field(default_factory=list)
    valid: bool = False
    errors: list[str] = Field(default_factory=list)


class MachineConfigList(Model):
    root: str = ""
    machines: list[MachineConfigSummary] = Field(default_factory=list)


class MachineConfigName(Model):
    name: str


class MachineConfigOut(Model):
    name: str
    path: str
    axes: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class ConfigValidateOut(Model):
    ok: bool
    errors: list[str] = Field(default_factory=list)


class ConfigGenerateRequest(Model):
    name: str
    target: Literal["sim", "plant"] = "sim"
    write: bool = Field(False, description="zapisz pliki na dysku (inaczej tylko podgląd)")
    out_dir: str = ""


class ConfigGenerateOut(Model):
    ok: bool = True
    files: dict[str, str] = Field(default_factory=dict, description="nazwa → treść")
    written: list[str] = Field(default_factory=list)
    message: str = ""


class DeploymentCheckRequest(Model):
    ini: str


class DeploymentCheckOut(Model):
    ok: bool = True
    issues: list[str] = Field(default_factory=list)
    hal_files: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- alarmy


class AlarmOut(Model):
    id: int
    code: str
    level: str = ""            # warning | simulation | program | error (z katalogu)
    message: str = ""
    raised: float = 0.0
    acknowledged: bool = False
    state: str = "active"      # active | acknowledged | cleared
    count: int = 1             # ile razy zgłoszono ten sam alarm, gdy był aktywny
    params: dict[str, Any] = Field(default_factory=dict)


class AlarmList(Model):
    active: list[AlarmOut] = Field(default_factory=list)
    history: list[AlarmOut] = Field(default_factory=list)
    worst_level: str | None = None


class AlarmCodeOut(Model):
    """Pozycja katalogu alarmów — GUI buduje z tego listę i opisy (PL/EN)."""

    code: str
    level: str = ""
    clear: str = ""                      # "ack" | "reset" — jak operator gasi alarm
    params: list[str] = Field(default_factory=list)   # parametry komunikatu
    message_pl: str = ""
    message_en: str = ""


class AlarmCodesOut(Model):
    codes: list[AlarmCodeOut] = Field(default_factory=list)


class AlarmRaiseRequest(Model):
    code: str
    params: dict[str, Any] = Field(default_factory=dict)


class AlarmAckRequest(Model):
    alarm_id: int | None = Field(None, description="None = potwierdź wszystkie")


# --------------------------------------------------------------------------- dostęp


class LoginRequest(Model):
    role: Literal["operator", "technolog", "serwis"]
    pin: str = Field(min_length=1, max_length=32)


class LoginOut(Model):
    ok: bool = True
    role: str = "operator"
    token: str = ""
    enforced: bool = False
    message: str = ""


class SessionOut(Model):
    role: str = "operator"
    enforced: bool = False
    permissions: list[str] = Field(default_factory=list)


class PinSetRequest(Model):
    role: Literal["technolog", "serwis"]
    pin: str = Field(min_length=4, max_length=32)


# --------------------------------------------------------------------------- system


class CapabilityOut(Model):
    """Jedna operacja kontraktu — z tego GUI generuje ekrany i formularze."""

    name: str
    domain: str
    kind: str = Field(description="command (zmienia stan) albo query (tylko czyta)")
    status: OpStatus
    summary: str = ""
    safety: str = "none"
    role: str = "operator"
    idempotent: bool = False
    plan: str = Field("", description="dla status=planned: czego brakuje do wdrożenia")
    request: dict[str, Any] = Field(default_factory=dict, description="schemat JSON żądania")
    result: dict[str, Any] = Field(default_factory=dict, description="schemat JSON wyniku")


class ContractOut(Model):
    schema_version: int = SCHEMA_VERSION
    application: str = ""
    version: str = ""
    operations: list[CapabilityOut] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class SystemInfo(Model):
    application: str
    version: str
    schema_version: int = SCHEMA_VERSION
    backend: str = ""
    python: str = ""
    platform: str = ""
    gui: bool = False
    opengl: bool = False
    notes: str = ""


class HealthOut(Model):
    ok: bool = True
    backend: str = ""
    backend_alive: bool = False
    uptime_s: float = 0.0
    threads: int = 0
    state_version: int = 0


class StateSnapshot(Model):
    """Wersjonowany stan wszystkich domen — to GUI subskrybuje przez WebSocket."""

    version: int = 0
    topics: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CallRequest(Model):
    """Wywołanie operacji przez WebSocket (kształt JSON-RPC 2.0)."""

    id: int | str = 0
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class CallResponse(Model):
    id: int | str = 0
    ok: bool = True
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


_models = {
    name: value for name, value in list(globals().items())
    if isinstance(value, type) and issubclass(value, Model)
}
__all__ = sorted(_models)
