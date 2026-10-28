"""Korzeń kompozycji: konfiguracja → backendy → usługi → kontrakt → pętla stanu.

SPDX-License-Identifier: GPL-2.0-or-later

``build_application()`` składa całą aplikację. To jedyne miejsce, które zna konkretne klasy:
transporty (REST/WebSocket/CLI) i SDK dostają gotowy obiekt ``Application`` z rejestrem
operacji i magazynem stanu. Dlatego:

- GUI podłącza się do ``/api/v1/call`` + ``/ws`` i nie musi wiedzieć nic o Pythonie,
- testy budują aplikację z atrapą backendu i sprawdzają operacje bez transportu,
- nowa funkcja = metoda usługi + jedna linia rejestracji w ``register_operations()``.

Pętla stanu (``poll_hz``, domyślnie 50 Hz) odświeża migawkę maszyny, publikuje ją
w magazynie i pilnuje deadmana jogu — dokładnie tak, jak robiłaby to warstwa ekranu.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from .backends.fake import FakeBackend
from .config import AppConfig
from .contract import (
    ROLE_SERVICE,
    ROLE_TECHNOLOG,
    SAFETY_CONFIG,
    SAFETY_MOTION,
    SAFETY_STOP,
    Context,
    Contract,
)
from .errors import ApiError, BackendUnavailable
from .schema import (
    AccessAuditOut,
    AccessAuditRequest,
    AccessRolesOut,
    AlarmAckRequest,
    AlarmCodesOut,
    AlarmList,
    AlarmRaiseRequest,
    AxisList,
    CallResponse,
    CheckRequest,
    Cia402Out,
    Cia402Request,
    CompileOut,
    ConfigGenerateOut,
    ConfigGenerateRequest,
    ConfigValidateOut,
    ContractOut,
    DeploymentCheckOut,
    DeploymentCheckRequest,
    DiagDoctor,
    DiagJournalOut,
    DiagJournalRequest,
    DriveLibrary,
    EstimateOut,
    EstimateRequest,
    HealthOut,
    HomeRequest,
    JogIncrementRequest,
    JogRequest,
    JogStopRequest,
    JournalCsvOut,
    LimitReportOut,
    LnxCompileRequest,
    LnxCompileTextRequest,
    LoginOut,
    LoginRequest,
    MachineConfigList,
    MachineConfigName,
    MachineConfigOut,
    MachineDrivesOut,
    MachineState,
    MdiRequest,
    ModeRequest,
    Ok,
    OverrideRequest,
    PinClearRequest,
    PinSetRequest,
    PlantFaultRequest,
    PlantFaultsOut,
    PlantLiveRequest,
    PlantStartRequest,
    PlantStatus,
    PlantTelemetryRequest,
    ProgramList,
    ProgramName,
    ProgramRead,
    ProgramWriteRequest,
    RunRequest,
    ScenarioList,
    ScenarioResultOut,
    ScenarioRunRequest,
    SessionOut,
    SimResultOut,
    SimRunRequest,
    SpindleRequest,
    StateSnapshot,
    StepEditRequest,
    SystemInfo,
    TelemetryOut,
    ToolChangeRequest,
    ToolHistoryOut,
    ToolImportRequest,
    ToolList,
    ToolNumber,
    ToolOut,
    ToolpathOut,
    ToolpathRequest,
    ToolTblOut,
    ToolTblRequest,
    ToolUpsertRequest,
    ToolWearRequest,
    WorkOffsetRequest,
)
from .services import (
    AccessService,
    AlarmService,
    CamService,
    DiagService,
    MachineConfigService,
    MachineService,
    OffsetService,
    PlantService,
    ProgramService,
    ProjectPaths,
    SimService,
    SystemService,
    ToolService,
)
from .services.alarm import AlarmOut
from .services.cam import CamCatalog, CamGenerateOut, CamGenerateRequest
from .services.offset import (
    ProbeApplyIn,
    ProbeCalibrateIn,
    ProbeOut,
    ProbeRunIn,
    ProbeRunOut,
    StockIn,
    StockOut,
    WorkpieceIn,
    WorkpieceOut,
)
from .session import SessionManager
from .state import StateHub

log = logging.getLogger("linumert.app")


class Application:
    """Złożona aplikacja: kontrakt, usługi, magazyn stanu i pętla odświeżania."""

    def __init__(self, config: AppConfig, contract: Contract, services: dict[str, Any],
                 hub: StateHub, sessions: SessionManager, backend: Any,
                 clock: Callable[[], float] = time.monotonic):
        self.config = config
        self.contract = contract
        self.services = services
        self.hub = hub
        self.sessions = sessions
        self.backend = backend
        self.paths: ProjectPaths = services["paths"]
        self._clock = clock
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = time.monotonic()

    # ---- wywołania ---------------------------------------------------------
    def call(self, command: str, params: dict[str, Any] | None = None, *,
             channel: str = "internal", token: str = "", call_id: int | str = 0) -> Any:
        """Wykonuje operację kontraktu i zwraca model wyniku."""
        access: AccessService = self.services["access"]
        ctx = Context(services=self.services, session=access.session(token), channel=channel,
                      call_id=call_id, state=self.hub, contract=self.contract, token=token)
        operation = self.contract.get(command)
        stopping = operation.safety == SAFETY_STOP
        if not stopping:
            self.sessions.charge(stopping=False)
        result = self.contract.call(command, params, ctx)
        self._log(command, channel)
        return result

    def call_json(self, command: str, params: dict[str, Any] | None = None,
                  **kwargs: Any) -> dict[str, Any]:
        return self.call(command, params, **kwargs).model_dump(mode="json")

    def handle_message(self, message: dict[str, Any], *, channel: str = "ws",
                       token: str = "") -> CallResponse:
        """Obsługa wiadomości ``{"id", "command", "params"}`` (WebSocket/SDK)."""
        call_id = message.get("id", 0)
        if message.get("method") == "state.get":
            return CallResponse(id=call_id, ok=True, result=self.hub.snapshot()["topics"])
        command = str(message.get("command", ""))
        params = message.get("params") or {}
        try:
            result = self.call(command, params, channel=channel, token=token, call_id=call_id)
        except ApiError as exc:
            return CallResponse(id=call_id, ok=False, error=exc.to_dict())
        return CallResponse(id=call_id, ok=True, result=result.model_dump(mode="json"))

    # ---- pętla stanu -------------------------------------------------------
    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="lrt-state", daemon=True)
            self._thread.start()
        self.publish_state()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        for name in ("plant", "tools", "diag", "access"):
            close = getattr(self.services.get(name), "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # zamknięcie nie może przesłonić błędu głównego
                    log.warning("zamknięcie usługi %s nie powiodło się", name, exc_info=True)

    def _loop(self) -> None:
        period = 1.0 / max(self.config.poll_hz, 1.0)
        while not self._stop.is_set():
            time.sleep(period)
            try:
                self.backend.tick()
                self.publish_state()
                for axis in self.services["machine"].expired_jog():
                    log.info("deadman jogu wygasł — stop %s", axis)
            except BackendUnavailable:
                self.hub.update("health", backend_alive=False)
            except Exception:
                log.exception("błąd pętli stanu")

    def publish_state(self) -> int:
        """Odświeża tematy stanu (maszyna, alarmy) w magazynie."""
        machine: MachineService = self.services["machine"]
        try:
            state = machine.state()
        except BackendUnavailable:
            return self.hub.update("health", backend_alive=False)
        self.hub.publish("machine", state.model_dump(mode="json"))
        active = self.services["alarm"].list(limit=50)
        self.hub.publish("alarms", {"active": [a.model_dump(mode="json") for a in active.active],
                                    "worst_level": active.worst_level})
        return self.hub.version

    # ---- pomocnicze --------------------------------------------------------
    def state(self, topics: tuple[str, ...] | None = None) -> StateSnapshot:
        snap = self.hub.snapshot(topics=topics)
        return StateSnapshot(version=snap["version"], topics=snap["topics"])

    def uptime(self) -> float:
        return time.monotonic() - self._started

    def _log(self, operation: str, channel: str) -> None:
        diag: DiagService | None = self.services.get("diag")
        if diag is None:
            return
        try:
            diag.log("info", f"{operation} ({channel})")
        except Exception:
            log.debug("zapis do dziennika nie powiódł się", exc_info=True)


def build_application(config: AppConfig | None = None, *, backend: Any = None,
                      start: bool = False) -> Application:
    """Składa aplikację; ``backend`` pozwala podstawić atrapę w testach."""
    cfg = config or AppConfig()
    paths = cfg.paths()
    paths.state.mkdir(parents=True, exist_ok=True)

    machine_backend = backend if backend is not None else make_backend(cfg)
    hub = StateHub()
    sessions = SessionManager()

    services: dict[str, Any] = {"paths": paths}
    services["machine"] = MachineService(machine_backend, sessions,
                                         sink=lambda topic, payload: hub.publish(topic, payload))
    services["program"] = ProgramService(paths)
    services["tools"] = ToolService(paths)
    services["cam"] = CamService()
    services["offset"] = OffsetService(paths)
    services["sim"] = SimService(paths, services["program"])
    services["plant"] = PlantService(paths)
    services["diag"] = DiagService(paths)
    services["config"] = MachineConfigService(paths)
    services["alarm"] = AlarmService()
    services["access"] = AccessService(paths)
    services["system"] = SystemService(
        backend_name=getattr(machine_backend, "name", "unknown"),
        state_version=lambda: hub.version,
        backend_alive=lambda: backend_alive(machine_backend),
    )

    contract = Contract()
    register_operations(contract)

    app = Application(cfg, contract, services, hub, sessions, machine_backend)
    # Stan początkowy publikujemy od razu: klient REST/GUI, który wejdzie przed startem
    # pętli, musi dostać pełną migawkę, a nie pusty słownik tematów.
    app.publish_state()
    if start:
        app.start()
    return app


def make_backend(cfg: AppConfig) -> Any:
    """Backend maszyny z konfiguracji (``fake`` albo ``linuxcnc``)."""
    if cfg.backend == "fake":
        return FakeBackend(axes=cfg.axes, autostart=cfg.autostart)
    if cfg.backend == "linuxcnc":
        from .backends.linuxcnc import LinuxCNCBackend, available

        if not available():
            raise BackendUnavailable(
                "backend linuxcnc wymaga modułu linuxcnc (LinuxCNC 2.9); "
                "poza maszyną użyj --backend fake")
        return LinuxCNCBackend()
    raise ValueError(f"nieznany backend {cfg.backend!r} (fake | linuxcnc)")


def backend_alive(backend: Any) -> bool:
    try:
        backend.snapshot()
    except Exception:
        return False
    return True


def _load_program(request: ProgramName, ctx: Context) -> Ok:
    """Wczytuje program z katalogu NC do sterowania (kolejność argumentów handlera)."""
    program = ctx.services["program"].read(request)
    return ctx.services["machine"].load_program(program.path, program.text)


def _tool_change(request: ToolChangeRequest, ctx: Context) -> Ok:
    """Narzędzie musi być w bazie (T0 = pusty uchwyt), zanim makro M6 ruszy maszyną."""
    if request.tool > 0:
        ctx.services["tools"].get(ToolNumber(number=request.tool))
    return ctx.services["machine"].tool_change(request)


def _csv_out(text: str) -> JournalCsvOut:
    """Dziennik CSV: tekst plus liczba niepustych wierszy dla GUI."""
    lines = [line for line in str(text).splitlines() if line.strip()]
    return JournalCsvOut(csv=str(text), lines=len(lines))


def register_operations(c: Contract) -> Contract:
    """Rejestruje wszystkie operacje kontraktu.

    Handler to cienkie przekierowanie do metody usługi — transport, GUI i CLI wołają
    dokładnie te same operacje, więc nie ma drugiej ścieżki do obejścia walidacji.
    """

    # ---- system ------------------------------------------------------------
    c.query("system.info", domain="system", summary="Informacje o aplikacji i backendzie",
            result=SystemInfo, handler=lambda r, ctx: ctx.services["system"].info())
    c.query("system.health", domain="system", summary="Zdrowie backendu i wersja stanu",
            result=HealthOut, handler=lambda r, ctx: ctx.services["system"].health())
    c.query("system.contract", domain="system",
            summary="Pełny kontrakt operacji ze schematami JSON — podstawa budowy GUI",
            result=ContractOut,
            handler=lambda r, ctx: ctx.services["system"].contract(ctx.contract.export()))
    c.query("system.state", domain="system", summary="Migawka stanu wszystkich domen",
            result=StateSnapshot,
            handler=lambda r, ctx: StateSnapshot(**{
                "version": ctx.state.version, "topics": ctx.state.snapshot()["topics"]}))

    # ---- machine -----------------------------------------------------------
    c.query("machine.state", domain="machine", summary="Migawka maszyny (DRO, tryb, program)",
            result=MachineState, handler=lambda r, ctx: ctx.services["machine"].state())
    c.command("machine.estop", domain="machine", summary="Aktywuj E-STOP", safety=SAFETY_STOP,
              idempotent=True, handler=lambda r, ctx: ctx.services["machine"].estop())
    c.command("machine.estop_reset", domain="machine", summary="Reset E-STOP (rola serwisu)",
              role=ROLE_SERVICE, safety=SAFETY_STOP,
              handler=lambda r, ctx: ctx.services["machine"].estop_reset())
    c.command("machine.power_on", domain="machine", summary="Włącz zasilanie",
              safety=SAFETY_MOTION, handler=lambda r, ctx: ctx.services["machine"].power_on())
    c.command("machine.power_off", domain="machine", summary="Wyłącz zasilanie",
              safety=SAFETY_STOP, idempotent=True,
              handler=lambda r, ctx: ctx.services["machine"].power_off())
    c.command("machine.set_mode", domain="machine", summary="Ustaw tryb MANUAL/AUTO/MDI",
              request=ModeRequest, safety=SAFETY_MOTION,
              handler=lambda r, ctx: ctx.services["machine"].set_mode(r))
    c.command("machine.home", domain="machine", summary="Bazuj oś albo wszystkie osie",
              request=HomeRequest, safety=SAFETY_MOTION,
              handler=lambda r, ctx: ctx.services["machine"].home(r))
    c.command("machine.mdi", domain="machine", summary="Wykonaj blok MDI", request=MdiRequest,
              safety=SAFETY_MOTION, handler=lambda r, ctx: ctx.services["machine"].mdi(r))
    c.command("machine.run", domain="machine", summary="Uruchom program od linii",
              request=RunRequest, safety=SAFETY_MOTION,
              handler=lambda r, ctx: ctx.services["machine"].run(r))
    c.command("machine.pause", domain="machine", summary="Pauza programu", safety=SAFETY_STOP,
              handler=lambda r, ctx: ctx.services["machine"].pause())
    c.command("machine.resume", domain="machine", summary="Wznów program",
              safety=SAFETY_MOTION, handler=lambda r, ctx: ctx.services["machine"].resume())
    c.command("machine.stop", domain="machine", summary="Zatrzymaj ruch i program",
              safety=SAFETY_STOP, idempotent=True,
              handler=lambda r, ctx: ctx.services["machine"].stop())
    c.command("machine.set_override", domain="machine",
              summary="Nastawy posuwu, G0 i wrzeciona", request=OverrideRequest,
              handler=lambda r, ctx: ctx.services["machine"].set_override(r))
    c.command("machine.spindle", domain="machine", summary="Wrzeciono: obroty i kierunek",
              request=SpindleRequest, safety=SAFETY_MOTION,
              handler=lambda r, ctx: ctx.services["machine"].spindle(r))
    c.command("machine.jog", domain="machine", summary="Jog ciągły z deadmanem sesji",
              request=JogRequest, safety=SAFETY_MOTION,
              handler=lambda r, ctx: ctx.services["machine"].jog(r))
    c.command("machine.jog_increment", domain="machine",
              summary="Jog przyrostowy o zadany krok", request=JogIncrementRequest,
              safety=SAFETY_MOTION,
              handler=lambda r, ctx: ctx.services["machine"].jog_increment(r))
    c.command("machine.jog_stop", domain="machine", summary="Zatrzymaj jog",
              request=JogStopRequest, safety=SAFETY_STOP, idempotent=True,
              handler=lambda r, ctx: ctx.services["machine"].jog_stop(r))
    c.command("machine.set_work_offset", domain="machine", summary="Ustaw offset G54–G59.3",
              request=WorkOffsetRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["machine"].set_work_offset(r))
    c.query("machine.axes", domain="machine", summary="Znane litery osi", result=AxisList,
            handler=lambda r, ctx: AxisList(axes=list(ctx.services["machine"].known_axes())))
    c.command("machine.tool_change", domain="machine", summary="Zmiana narzędzia (M6/ATC)",
              request=ToolChangeRequest, safety=SAFETY_MOTION,
              handler=_tool_change)

    # ---- program -----------------------------------------------------------
    c.query("program.list", domain="program", summary="Programy w katalogu NC",
            result=ProgramList, handler=lambda r, ctx: ctx.services["program"].list())
    c.query("program.read", domain="program", summary="Treść programu", request=ProgramName,
            result=ProgramRead, handler=lambda r, ctx: ctx.services["program"].read(r))
    c.command("program.write", domain="program", summary="Zapisz program (.ngc/.lnx)",
              request=ProgramWriteRequest, role=ROLE_TECHNOLOG, safety=SAFETY_CONFIG,
              handler=lambda r, ctx: ctx.services["program"].write(r))
    c.command("program.delete", domain="program", summary="Usuń program",
              request=ProgramName, role=ROLE_TECHNOLOG, safety=SAFETY_CONFIG,
              handler=lambda r, ctx: ctx.services["program"].delete(r))
    c.command("program.compile", domain="program", summary="Kompiluj .lnx → G-code",
              request=LnxCompileRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["program"].compile_lnx(r))
    # To samo, ale z tekstu i bez zapisu — edytor GUI podgląda wynik przed zapisem.
    c.query("program.compile_text", domain="program",
            summary="Kompiluj .lnx z tekstu (bez zapisu na dysk)",
            request=LnxCompileTextRequest, result=CompileOut,
            handler=lambda r, ctx: CompileOut(
                gcode=ctx.services["program"].compile_text(r.text),
                message="skompilowano w pamięci"))
    c.query("program.check", domain="program", summary="Sprawdź granice osi programu",
            request=CheckRequest, result=LimitReportOut,
            handler=lambda r, ctx: ctx.services["program"].check(r))
    c.query("program.estimate", domain="program", summary="Czas, droga i narzędzia programu",
            request=EstimateRequest, result=EstimateOut,
            handler=lambda r, ctx: ctx.services["program"].estimate(r))
    c.query("program.toolpath", domain="program",
            summary="Punkty ścieżki do podglądu — GUI rysuje u siebie",
            request=ToolpathRequest, result=ToolpathOut,
            handler=lambda r, ctx: ctx.services["program"].toolpath(r))
    c.command("program.edit_step", domain="program", summary="Zmień parametr kroku .lnx",
              request=StepEditRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["program"].edit_step(r))
    c.command("program.load", domain="program", summary="Wczytaj program do sterowania",
              request=ProgramName, safety=SAFETY_MOTION, handler=_load_program)

    # ---- tools -------------------------------------------------------------
    c.query("tool.list", domain="tool", summary="Narzędzia z bazy", result=ToolList,
            handler=lambda r, ctx: ctx.services["tools"].list())
    c.query("tool.get", domain="tool", summary="Narzędzie po numerze", request=ToolNumber,
            result=ToolOut, handler=lambda r, ctx: ctx.services["tools"].get(r))
    c.command("tool.upsert", domain="tool", summary="Dodaj albo zaktualizuj narzędzie",
              request=ToolUpsertRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["tools"].upsert(r))
    c.command("tool.delete", domain="tool", summary="Usuń narzędzie", request=ToolNumber,
              role=ROLE_TECHNOLOG, handler=lambda r, ctx: ctx.services["tools"].delete(r))
    c.command("tool.set_wear", domain="tool", summary="Korekcja zużycia (X/Y/Z)",
              request=ToolWearRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["tools"].set_wear(r))
    c.query("tool.history", domain="tool", summary="Historia zmian narzędzia",
            request=ToolNumber, result=ToolHistoryOut,
            handler=lambda r, ctx: ToolHistoryOut(**ctx.services["tools"].history(r)))
    c.command("tool.import_tbl", domain="tool", summary="Import tool.tbl do bazy",
              request=ToolImportRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["tools"].import_tbl(r.text, r.units))
    c.command("tool.export_tbl", domain="tool", summary="Eksport tool.tbl dla LinuxCNC",
              request=ToolTblRequest, result=ToolTblOut, role=ROLE_TECHNOLOG,
              safety=SAFETY_CONFIG, handler=lambda r, ctx: ctx.services["tools"].export_tbl(r))

    # ---- cam ---------------------------------------------------------------
    c.query("cam.operations", domain="cam",
            summary="Katalog operacji CAM ze schematem parametrów (formularze GUI)",
            result=CamCatalog, handler=lambda r, ctx: ctx.services["cam"].operations())
    c.command("cam.generate", domain="cam", summary="Generuj G-code z parametrów",
              request=CamGenerateRequest, result=CamGenerateOut, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["cam"].generate(r))

    # ---- offset ------------------------------------------------------------
    c.query("offset.stock_get", domain="offset", summary="Przygotówka", result=StockOut,
            handler=lambda r, ctx: ctx.services["offset"].stock_get())
    c.command("offset.stock_set", domain="offset", summary="Ustaw przygotówkę",
              request=StockIn, result=StockOut, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["offset"].stock_set(r))
    c.query("offset.workpiece_get", domain="offset", summary="Definicja detalu",
            result=WorkpieceOut, handler=lambda r, ctx: ctx.services["offset"].workpiece_get())
    c.command("offset.workpiece_set", domain="offset", summary="Ustaw definicję detalu",
              request=WorkpieceIn, result=WorkpieceOut,
              handler=lambda r, ctx: ctx.services["offset"].workpiece_set(
                  {k: v for k, v in r.model_dump().items() if v not in ("", None)}))
    c.command("offset.probe_calibrate", domain="offset",
              summary="Kalibracja sondy (współczynnik)", request=ProbeCalibrateIn,
              result=ProbeOut, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["offset"].probe_calibrate(r))
    c.command("offset.probe_apply", domain="offset", summary="Zastosuj kalibrację do pomiaru",
              request=ProbeApplyIn, result=ProbeOut, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["offset"].probe_apply(r))
    c.command("offset.probe_run", domain="offset",
              summary="Sondowanie G38.2 jednej osi i zapis offsetu (ruch)",
              request=ProbeRunIn, result=ProbeRunOut, safety=SAFETY_MOTION,
              role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["offset"].probe_run(
                  r, ctx.services["machine"]))

    # ---- sim ---------------------------------------------------------------
    c.command("sim.run", domain="sim",
              summary="Symulacja: materiał, kolizje, czas (dane, bez grafiki)",
              request=SimRunRequest, result=SimResultOut,
              handler=lambda r, ctx: ctx.services["sim"].run(r))

    # ---- plant -------------------------------------------------------------
    c.query("plant.status", domain="plant", summary="Stan wirtualnej obrabiarki",
            result=PlantStatus, handler=lambda r, ctx: ctx.services["plant"].status())
    c.command("plant.start", domain="plant", summary="Uruchom serwer LRT-NET",
              request=PlantStartRequest, result=PlantStatus, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["plant"].start(r))
    c.command("plant.stop", domain="plant", summary="Zatrzymaj Plant", safety=SAFETY_STOP,
              handler=lambda r, ctx: ctx.services["plant"].stop())
    c.query("plant.scenarios", domain="plant", summary="Scenariusze testowe",
            result=ScenarioList, handler=lambda r, ctx: ctx.services["plant"].scenarios())
    c.command("plant.scenario_run", domain="plant",
              summary="Przebieg scenariusza z kryteriami i raportem",
              request=ScenarioRunRequest, result=ScenarioResultOut, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["plant"].run_scenario(r))
    c.query("plant.drives", domain="plant", summary="Biblioteka szablonów napędów",
            result=DriveLibrary, handler=lambda r, ctx: ctx.services["plant"].drives())
    c.command("plant.set_live", domain="plant", summary="Parametry live napędu",
              request=PlantLiveRequest, role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["plant"].set_live(r))
    c.command("plant.fault_set", domain="plant", summary="Wstrzyknij albo zdejmij awarię",
              request=PlantFaultRequest, role=ROLE_SERVICE,
              handler=lambda r, ctx: ctx.services["plant"].set_fault(r))
    c.query("plant.telemetry", domain="plant", summary="Próbki telemetrii osi",
            request=PlantTelemetryRequest, result=TelemetryOut,
            handler=lambda r, ctx: TelemetryOut(**ctx.services["plant"].telemetry(r)))
    # Awarie wstrzyknięte w Plant + katalog rodzajów — GUI rysuje panel testowy.
    c.query("plant.faults", domain="plant",
            summary="Aktywne awarie Plant i katalog rodzajów",
            result=PlantFaultsOut,
            handler=lambda r, ctx: PlantFaultsOut(**ctx.services["plant"].faults()))
    # Parametry napędów po rozwiązaniu szablonu z biblioteki nadpisaniami z machine.yaml.
    c.query("plant.machine_drives", domain="plant",
            summary="Rozwiązane parametry napędów maszyny",
            request=MachineConfigName, result=MachineDrivesOut,
            handler=lambda r, ctx: MachineDrivesOut(**ctx.services["plant"].machine_drives(r)))

    # ---- config ------------------------------------------------------------
    c.query("config.machines", domain="config",
            summary="Maszyny z config/machines wraz z walidacją", result=MachineConfigList,
            handler=lambda r, ctx: ctx.services["config"].list())
    c.query("config.machine_get", domain="config", summary="Konfiguracja maszyny",
            request=MachineConfigName, result=MachineConfigOut,
            handler=lambda r, ctx: ctx.services["config"].get(r))
    c.query("config.validate", domain="config", summary="Walidacja machine.yaml",
            request=MachineConfigName, result=ConfigValidateOut,
            handler=lambda r, ctx: ctx.services["config"].validate(r))
    c.command("config.generate", domain="config",
              summary="Generuj INI/HAL (podgląd albo zapis)", request=ConfigGenerateRequest,
              result=ConfigGenerateOut, role=ROLE_TECHNOLOG, safety=SAFETY_CONFIG,
              handler=lambda r, ctx: ctx.services["config"].generate(r))
    c.query("config.check_deployment", domain="config",
              summary="Sprawdź wdrożoną konfigurację LinuxCNC",
              request=DeploymentCheckRequest, result=DeploymentCheckOut,
              handler=lambda r, ctx: ctx.services["config"].check_deployment(r))

    # ---- alarms ------------------------------------------------------------
    c.query("alarm.list", domain="alarm", summary="Aktywne alarmy i historia",
            result=AlarmList, handler=lambda r, ctx: ctx.services["alarm"].list())
    # Katalog kodów z komunikatami PL/EN — GUI nie trzyma własnych tłumaczeń.
    c.query("alarm.codes", domain="alarm",
            summary="Katalog kodów alarmów z komunikatami PL/EN",
            result=AlarmCodesOut, handler=lambda r, ctx: ctx.services["alarm"].codes())
    c.command("alarm.raise", domain="alarm", summary="Zgłoś alarm (testy i integracje)",
              request=AlarmRaiseRequest, result=AlarmOut, role=ROLE_SERVICE,
              handler=lambda r, ctx: ctx.services["alarm"].raise_alarm(r))
    c.command("alarm.ack", domain="alarm", summary="Potwierdź alarm albo wszystkie",
              request=AlarmAckRequest, handler=lambda r, ctx: ctx.services["alarm"].acknowledge(r))
    c.command("alarm.reset", domain="alarm",
              summary="Wyczyść alarmy (nie zwalnia E-STOP)", role=ROLE_TECHNOLOG,
              handler=lambda r, ctx: ctx.services["alarm"].reset())

    # ---- diagnostics -------------------------------------------------------
    c.query("diag.doctor", domain="diag", summary="Inwentaryzacja środowiska (read-only)",
            result=DiagDoctor, handler=lambda r, ctx: ctx.services["diag"].doctor())
    c.query("diag.journal_csv", domain="diag",
            summary="Dziennik zdarzeń jako CSV (eksport)",
            request=DiagJournalRequest, result=JournalCsvOut,
            handler=lambda r, ctx: _csv_out(ctx.services["diag"].journal_csv(r)))
    c.query("diag.journal", domain="diag", summary="Dziennik zdarzeń",
            request=DiagJournalRequest, result=DiagJournalOut,
            handler=lambda r, ctx: ctx.services["diag"].journal(r))
    c.query("diag.cia402", domain="diag", summary="Dekoduj statusword CiA 402",
            request=Cia402Request, result=Cia402Out,
            handler=lambda r, ctx: ctx.services["diag"].cia402(r))

    # ---- access ------------------------------------------------------------
    c.command("access.login", domain="access", summary="Zaloguj rolę PIN-em",
              request=LoginRequest, result=LoginOut,
              handler=lambda r, ctx: ctx.services["access"].login(r))
    c.query("access.session", domain="access", summary="Bieżąca sesja i uprawnienia",
            result=SessionOut,
            handler=lambda r, ctx: ctx.services["access"].current(ctx.token))
    c.command("access.set_pin", domain="access", summary="Ustaw PIN roli",
              request=PinSetRequest, role=ROLE_SERVICE, safety=SAFETY_CONFIG,
              handler=lambda r, ctx: ctx.services["access"].set_pin(r))
    # Bez wylogowania GUI nie ma jak zamknąć sesji po zmianie operatora.
    c.command("access.logout", domain="access", summary="Wyloguj bieżącą sesję",
              handler=lambda r, ctx: ctx.services["access"].logout(ctx.token))
    c.query("access.roles", domain="access",
            summary="Role z PIN-ami i wymagana rola dla uprawnień",
            result=AccessRolesOut,
            handler=lambda r, ctx: AccessRolesOut(**ctx.services["access"].roles()))
    c.query("access.audit", domain="access", summary="Historia zdarzeń dostępu",
            request=AccessAuditRequest, result=AccessAuditOut,
            handler=lambda r, ctx: AccessAuditOut(
                **ctx.services["access"].audit(limit=r.limit, action=r.action)))
    c.command("access.clear_pin", domain="access", summary="Usuń PIN roli",
              request=PinClearRequest, role=ROLE_SERVICE, safety=SAFETY_CONFIG,
              handler=lambda r, ctx: ctx.services["access"].clear_pin(r.role))

    # ---- zdarzenia dla GUI -------------------------------------------------
    c.event("machine", summary="Migawka maszyny (DRO, tryb, program) — 50 Hz")
    c.event("alarms", summary="Aktywne alarmy i najgorszy poziom")
    c.event("health", summary="Zdrowie backendu")
    c.event("plant", summary="Stan Plant (ramki LRT-NET, wyrocznia)")
    return c


__all__ = ["Application", "backend_alive", "build_application", "make_backend",
           "register_operations"]
