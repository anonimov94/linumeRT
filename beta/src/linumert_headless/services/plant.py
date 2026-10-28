"""Usługa Plant: wirtualna obrabiarka, scenariusze, biblioteka napędów, telemetria.

SPDX-License-Identifier: GPL-2.0-or-later

Plant to jedyna droga do testowania dynamiki bez sprzętu. W projekcie beta zostają funkcje
potrzebne do działania **bez GUI**:

- uruchomienie serwera LRT-NET w wątku (``linumert_plant.server``) — tak samo jak
  ``python -m linumert_plant serve``, ale sterowane przez API,
- scenariusze z atrapą mastera (``scenario.run_mock`` + ``evaluate``) — pełny przebieg
  i kryteria odbioru bez LinuxCNC,
- biblioteka szablonów napędów (``drive_library``) i walidacja ``machine.yaml``,
- raport HTML scenariusza (dowód odbioru, nie GUI).

Usunięte: panel web (``panel/app.py``, fastapi) i scenariusze z LinuxCNC RIP — patrz
``PROVENANCE.md``.
"""

from __future__ import annotations

import socket
import threading
from pathlib import Path

from linumert.machine.schema import MachineConfigError
from linumert_plant import report as plant_report
from linumert_plant import scenario as scen
from linumert_plant.drive_library import TemplateError, load_library
from linumert_plant.faults import Faults
from linumert_plant.machine_drives import MachineConfigError as DrivesError
from linumert_plant.machine_drives import load_machine_drives
from linumert_plant.server import PlantConfig, PlantConfigError, PlantServer, load_plant_config

from ..errors import Conflict, InvalidRequest, NotFound
from ..schema import (
    DriveLibrary,
    DriveTemplateOut,
    MachineConfigName,
    Ok,
    PlantFaultRequest,
    PlantLiveRequest,
    PlantStartRequest,
    PlantStatus,
    PlantTelemetryRequest,
    ScenarioList,
    ScenarioResultOut,
    ScenarioRunRequest,
)
from .paths import ProjectPaths


def _free_port(listen: str) -> int:
    """Wolny port UDP na ``listen`` (``request.port = 0`` = „wybierz sam")."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind((listen, 0))
        return int(probe.getsockname()[1])


class PlantService:
    """Operacje domeny ``plant``."""

    domain = "plant"

    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self._server: PlantServer | None = None
        self._thread: threading.Thread | None = None
        self._socket = None
        self._lock = threading.RLock()

    # ---- biblioteka napędów ------------------------------------------------
    def drives(self) -> DriveLibrary:
        try:
            library = load_library(self.paths.drives)
        except TemplateError as exc:
            raise InvalidRequest(f"biblioteka napędów jest niepoprawna: {exc}") from exc
        items = []
        for tpl_id, tpl in sorted(library.items()):
            items.append(DriveTemplateOut(
                id=tpl_id,
                kind=str(tpl.get("kind", "")),
                summary=str(tpl.get("summary", "") or tpl.get("description", "")),
                parameters={k: v for k, v in tpl.items()
                            if k not in {"id", "kind", "summary", "description"}},
            ))
        return DriveLibrary(root=str(self.paths.drives), templates=items)

    def machine_drives(self, request: MachineConfigName) -> dict:
        """Rozwiązane parametry napędów maszyny — szablon z biblioteki plus nadpisania.

        ``load_machine_drives`` zwraca **krotkę** ``(MachineConfig, dict[str, DriveInstance])``;
        poprzedni kod wołał ``.items()`` na krotce, więc każda taka operacja kończyła się
        ``AttributeError: 'tuple' object has no attribute 'items'``.
        """
        path = self.paths.machine(request.name)
        try:
            config, drives = load_machine_drives(path, self.paths.drives)
        except (MachineConfigError, DrivesError, TemplateError) as exc:
            raise InvalidRequest(f"napędy maszyny {request.name} są niepoprawne: {exc}") from exc
        return {"machine": request.name,
                "drives": {name: dict(inst.params or {}) for name, inst in drives.items()},
                # Axis to model pydantic z polem letter — str(a) dałoby GUI repr modelu.
                "axes": [str(getattr(a, "letter", a)) for a in config.axes or []]}

    # ---- scenariusze -------------------------------------------------------
    def scenarios(self) -> ScenarioList:
        root = self.paths.scenarios
        names: list[str] = []
        if root.exists():
            names = sorted(p.name for p in root.rglob("*.yaml"))
        return ScenarioList(root=str(root), scenarios=names)

    def run_scenario(self, request: ScenarioRunRequest) -> ScenarioResultOut:
        path = self.paths.scenario(request.scenario)
        machine = Path(request.machine) if request.machine else None
        try:
            loaded = scen.load_scenario(path, machine)
        except (scen.ScenarioError, OSError) as exc:
            raise InvalidRequest(f"scenariusz {path.name} jest niepoprawny: {exc}") from exc
        try:
            result = scen.run_mock(loaded)
            scen.evaluate(result)
        except scen.ScenarioError as exc:
            raise Conflict(f"przebieg scenariusza nie powiódł się: {exc}") from exc
        passed = all(c.passed for c in result.criteria) if result.criteria else result.completed
        return ScenarioResultOut(
            name=loaded.name,
            passed=passed,
            criteria=[{"name": c.name, "passed": c.passed, "detail": c.detail}
                      for c in result.criteria],
            events=[{"event": e} for e in result.events],
            report_html=plant_report.render(result),
            message=f"{len(result.criteria)} kryteriów, "
                    f"{'PASS' if passed else 'FAIL'}",
        )

    # ---- serwer LRT-NET ----------------------------------------------------
    def status(self) -> PlantStatus:
        with self._lock:
            if self._server is None:
                return PlantStatus(running=False, message="Plant nie jest uruchomiony")
            stats = self._server.stats
            cfg = self._server.cfg
            return PlantStatus(
                running=self._thread is not None and self._thread.is_alive(),
                machine=str(self._server.machine.model.name),
                listen=cfg.listen, port=cfg.port, mode=cfg.mode,
                frames=stats.received, rejected=stats.rejected,
                lost=stats.lost, late=stats.late,
                message="Plant odpowiada na LRT-NET",
            )

    def start(self, request: PlantStartRequest) -> PlantStatus:
        with self._lock:
            if self._server is not None:
                raise Conflict("Plant już działa — użyj plant.stop")
            given = Path(request.machine)
            source = given if given.is_absolute() else self.paths.machine(request.machine)
            if not source.exists():
                raise NotFound(f"nie znaleziono maszyny {request.machine}",
                               details={"name": request.machine})
            cfg = load_plant_config(request.plant) if request.plant else PlantConfig()
            cfg.machine = source
            cfg.mode = request.mode
            cfg.listen = request.listen
            # PlantConfig waliduje port 1–65535, więc 0 („wybierz wolny”) rozwiązujemy
            # sami: zajmujemy port na chwilę i oddajemy go serwerowi LRT-NET.
            cfg.port = request.port if request.port else _free_port(request.listen)
            try:
                from linumert_plant.serve import build_server

                server = build_server(cfg, self.paths.drives)
                sock = server.bind()
            except (MachineConfigError, PlantConfigError, OSError) as exc:
                raise Conflict(f"Plant nie wystartował: {exc}") from exc
            cfg.port = sock.getsockname()[1]
            self._server, self._socket = server, sock
            self._thread = threading.Thread(target=server.serve, args=(sock,),
                                            name="plant-lrtnet", daemon=True)
            self._thread.start()
        return self.status()

    def stop(self) -> Ok:
        with self._lock:
            if self._server is None:
                return Ok(message="Plant nie był uruchomiony")
            server, sock, thread = self._server, self._socket, self._thread
            self._server = self._socket = self._thread = None
        server.stop()
        if sock is not None:
            sock.close()
        if thread is not None:
            thread.join(timeout=2.0)
        return Ok(message="Plant zatrzymany")

    # ---- parametry live, awarie, telemetria --------------------------------
    def _require(self) -> PlantServer:
        if self._server is None:
            raise Conflict("Plant nie jest uruchomiony — użyj plant.start")
        return self._server

    def set_live(self, request: PlantLiveRequest) -> Ok:
        """Parametry live napędu: ``set_live(drive, "ścieżka.parametru", wartość)``."""
        server = self._require()
        if not request.drive:
            raise InvalidRequest("podaj napęd (drive)",
                                 details={"drives": list(server.drives)})
        applied: dict[str, float] = {}
        for path, value in request.parameters.items():
            try:
                server.set_live(request.drive, path, value)
            except (KeyError, ValueError) as exc:
                raise InvalidRequest(f"parametr {path} napędu {request.drive} odrzucony: {exc}",
                                     details={"drive": request.drive, "parameter": path}) from exc
            applied[path] = float(value)
        return Ok(message=f"parametry live {request.drive} zaktualizowane",
                  details={"applied": applied})

    def set_fault(self, request: PlantFaultRequest) -> Ok:
        """Wstrzyknięcie albo zdjęcie awarii (``Faults.inject`` / ``Faults.clear``).

        Parametry idą do ``Faults`` bez zmiany nazw — ``drive_fault`` czyta ``drive``,
        nie ``target``, a ``FaultError`` jest podklasą ``ValueError``.
        """
        server = self._require()
        params = dict(request.params or {})
        try:
            if request.enabled:
                server.faults.inject(request.kind, **params)
            else:
                server.faults.clear(request.kind, **params)
        except (KeyError, ValueError) as exc:
            raise InvalidRequest(
                f"awaria {request.kind} nie jest znana albo ma złe parametry: {exc}",
                details={"kind": request.kind, "catalog": Faults.catalog()}) from exc
        return Ok(message=f"awaria {request.kind}: "
                          f"{'wstrzyknięta' if request.enabled else 'zdjęta'}")

    def faults(self) -> dict:
        server = self._require()
        return {"active": server.faults.active(), "catalog": server.faults.catalog()}

    def telemetry(self, request: PlantTelemetryRequest) -> dict:
        """Próbki telemetrii z bufora pierścieniowego (``Telemetry.since``)."""
        server = self._require()
        index = None if not request.drive else (
            server.drives.index(request.drive) if request.drive in server.drives else None)
        if request.drive and index is None:
            raise InvalidRequest(f"nieznany napęd {request.drive}",
                                 details={"drives": list(server.drives)})
        cursor, rows = server.telemetry.since(index)
        rows = rows[-request.limit:]
        return {
            "drive": request.drive,
            "cursor": cursor,
            "columns": server.telemetry.columns(index),
            "samples": [list(row) for row in rows],
        }

    def close(self) -> None:
        if self._server is not None:
            self.stop()


__all__ = ["PlantService"]
