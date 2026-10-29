"""Kontrakt operacji aplikacji headless — jedno źródło prawdy dla GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Każda funkcja aplikacji jest **operacją** o nazwie ``domena.akcja`` (np. ``machine.home``),
z modelem żądania, modelem wyniku, poziomem dostępu i oznaczeniem bezpieczeństwa. Ten sam
rejestr obsługuje:

- REST  ``POST /api/v1/call {"command": "machine.home", "params": {...}}``,
- WebSocket (ten sam kształt wiadomości),
- CLI   ``linumertctl machine home --axis X``,
- SDK   ``client.machine.home(axis="X")``,
- GUI  ``GET /api/v1/contract`` → schematy JSON do wygenerowania interfejsu.

Dlatego GUI powstaje na końcu projektu bez zmian w rdzeniu: czyta kontrakt, buduje ekrany,
wysyła operacje. Nowa funkcja = nowa operacja w rejestrze; GUI widzi ją automatycznie.

Status operacji:
- ``implemented`` — działa i ma test,
- ``planned``     — jest w kontrakcie, zgłasza ``not_implemented`` z planem wdrożenia.
GUI może więc rysować pełny zakres funkcji od początku, a backend dochodzi etapami.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from .errors import ApiError, InternalError, InvalidRequest, NotFound, NotImplementedCapability
from .schema import Empty, Model, Ok, OpStatus

log = logging.getLogger("linumert.contract")

Handler = Callable[[BaseModel, "Context"], BaseModel]

SAFETY_NONE = "none"
SAFETY_MOTION = "motion"      # porusza maszyną (wymaga bazowania / braku limitów)
SAFETY_STOP = "stop"          # zatrzymuje ruch; nigdy nie podlega limiterowi poleceń
SAFETY_CONFIG = "config"      # zmienia konfigurację / pliki

ROLE_OPERATOR = "operator"
ROLE_TECHNOLOG = "technolog"
ROLE_SERVICE = "serwis"


@dataclass(frozen=True)
class Operation:
    """Opis jednej operacji kontraktu."""

    name: str
    domain: str
    kind: str  # "command" (zmienia stan) | "query" (tylko czyta)
    summary: str
    request: type[Model]
    result: type[Model]
    status: OpStatus = "implemented"
    safety: str = SAFETY_NONE
    role: str = ROLE_OPERATOR
    idempotent: bool = False
    plan: str = ""  # dla status="planned": czego brakuje do wdrożenia

    @property
    def action(self) -> str:
        return self.name.split(".", 1)[1]


@dataclass
class Context:
    """Kontekst wywołania: kto woła, przez jaki kanał i do jakich usług ma dostęp.

    Usługi dostają tylko to, czego potrzebują — transport dokłada ``session`` i ``channel``.
    """

    services: dict[str, Any] = field(default_factory=dict)
    session: Any = None
    channel: str = "internal"  # "rest" | "ws" | "cli" | "sdk" | "internal"
    call_id: int | str = 0
    state: Any = None
    contract: Any = None  # rejestr operacji (dla system.contract)
    token: str = ""       # token sesji (dla access.session)


class Contract:
    """Rejestr operacji wraz z obsługą wywołań."""

    def __init__(self) -> None:
        self._ops: dict[str, Operation] = {}
        self._handlers: dict[str, Handler] = {}
        self._events: dict[str, dict[str, Any]] = {}

    # ---- rejestracja -------------------------------------------------------
    def register(self, op: Operation, handler: Handler | None = None) -> Operation:
        if op.name in self._ops:
            raise ValueError(f"operacja {op.name} jest już zarejestrowana")
        if op.status == "implemented" and handler is None:
            raise ValueError(f"operacja {op.name} wymaga handlera (status=implemented)")
        self._ops[op.name] = op
        self._handlers[op.name] = handler or _planned_handler(op)
        return op

    def command(self, name: str, *, domain: str, summary: str, request: type[Model] = Empty,
                result: type[Model] = Ok, safety: str = SAFETY_NONE, role: str = ROLE_OPERATOR,
                idempotent: bool = False, status: OpStatus = "implemented", plan: str = "",
                handler: Handler | None = None) -> Operation:
        return self.register(Operation(name, domain, "command", summary, request, result,
                                       status, safety, role, idempotent, plan), handler)

    def query(self, name: str, *, domain: str, summary: str, request: type[Model] = Empty,
              result: type[Model], role: str = ROLE_OPERATOR,
              status: OpStatus = "implemented", plan: str = "",
              handler: Handler | None = None) -> Operation:
        return self.register(Operation(name, domain, "query", summary, request, result,
                                       status, safety=SAFETY_NONE, role=role,
                                       idempotent=True, plan=plan), handler)

    def event(self, topic: str, *, summary: str, payload: dict[str, Any] | None = None) -> None:
        self._events[topic] = {"topic": topic, "summary": summary,
                               "payload": payload or {}}

    # ---- introspekcja ------------------------------------------------------
    def get(self, name: str) -> Operation:
        try:
            return self._ops[name]
        except KeyError:
            raise NotFound(f"nieznana operacja: {name}",
                           details={"command": name, "known": sorted(self._ops)[:40]}) from None

    def operations(self) -> list[Operation]:
        return sorted(self._ops.values(), key=lambda o: o.name)

    def domains(self) -> list[str]:
        return sorted({o.domain for o in self._ops.values()})

    def events(self) -> list[dict[str, Any]]:
        return [self._events[k] for k in sorted(self._events)]

    def export(self, *, application: str = "", version: str = "") -> dict[str, Any]:
        """Kontrakt jako czysty JSON — podstawa codegen dla dowolnego GUI."""
        return {
            "application": application,
            "version": version,
            "domains": self.domains(),
            "operations": [
                {
                    "name": o.name,
                    "domain": o.domain,
                    "kind": o.kind,
                    "summary": o.summary,
                    "status": o.status,
                    "safety": o.safety,
                    "role": o.role,
                    "idempotent": o.idempotent,
                    "plan": o.plan,
                    "request": _schema(o.request),
                    "result": _schema(o.result),
                }
                for o in self.operations()
            ],
            "events": self.events(),
        }

    # ---- wywołanie ---------------------------------------------------------
    def call(self, name: str, params: dict[str, Any] | None, ctx: Context) -> BaseModel:
        """Waliduje parametry, sprawdza uprawnienia i wykonuje operację."""
        op = self.get(name)
        _check_role(op, ctx)
        try:
            request = op.request.model_validate(params or {})
        except ValidationError as exc:
            raise InvalidRequest(f"parametry operacji {name} są niepoprawne",
                                 details={"errors": exc.errors(include_url=False)}) from None
        try:
            result = self._handlers[name](request, ctx)
        except ApiError:
            raise
        except Exception as exc:  # błąd usługi nie może wyciec jako traceback do GUI
            log.exception("operacja %s nie powiodła się", name)
            raise InternalError(f"operacja {name} nie powiodła się: {exc}",
                                details={"command": name}, cause=exc) from None
        if not isinstance(result, BaseModel):
            raise InternalError(f"handler {name} zwrócił {type(result).__name__} zamiast modelu")
        return result


def _check_role(op: Operation, ctx: Context) -> None:
    """Poziom dostępu: sesja (jeśli jest) musi pozwalać na tę operację."""
    session = getattr(ctx, "session", None)
    if session is None:
        return
    allowed = getattr(session, "allowed", None)
    if callable(allowed) and not allowed(f"{op.domain}.{op.action}"):
        from .errors import PermissionDenied

        raise PermissionDenied(
            f"brak uprawnień do {op.name} (wymagana rola: {op.role})",
            details={"command": op.name, "role_required": op.role,
                     "role_current": getattr(session, "role", "operator")},
        )


def _planned_handler(op: Operation) -> Handler:
    def handler(_request: BaseModel, _ctx: Context) -> BaseModel:
        raise NotImplementedCapability(op.name, op.plan)

    return handler


def _schema(model: type[Model]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("$defs", None)
    return schema


__all__ = [
    "ROLE_OPERATOR",
    "ROLE_SERVICE",
    "ROLE_TECHNOLOG",
    "SAFETY_CONFIG",
    "SAFETY_MOTION",
    "SAFETY_NONE",
    "SAFETY_STOP",
    "Context",
    "Contract",
    "Operation",
]
