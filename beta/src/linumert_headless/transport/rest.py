"""Transport REST + WebSocket aplikacji headless.

SPDX-License-Identifier: GPL-2.0-or-later

Jeden punkt wejścia dla każdego GUI:

- ``POST /api/v1/call``  ``{"command": "machine.home", "params": {"axis": "X"}}``
- ``GET  /api/v1/contract``  pełny kontrakt ze schematami JSON (codegen GUI)
- ``GET  /api/v1/state``  migawka stanu (albo push przez ``/ws``)
- ``WS   /ws``  stan na żywo + wywoływanie operacji

Zabezpieczenia (przeniesione z bramy web i obowiązujące dla każdego klienta):
- token w nagłówku ``X-LRT-Token`` albo ``Authorization: Bearer``; poza localhost wymagany,
- kontrola ``Host``/``Origin`` — blokuje DNS-rebinding i wywołania z obcej strony,
- błędy jako ``{"error": {"code", "message", "details"}}`` z kodem HTTP z ``ApiError``,
- brak domyślnych poświadczeń i brak zwolnienia E-STOP dla roli operatora.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Any

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse

from ..app import Application
from ..errors import ApiError, InvalidRequest, PermissionDenied
from ..schema import SCHEMA_VERSION
from .ws import ConnectionHub

log = logging.getLogger("linumert.transport")

API = "/api/v1"


def error_response(exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content={"ok": False,
                                                             "error": exc.to_dict()})


# Trasy bez tokenu: health-check dla orkiestracji i informacje o aplikacji.
# Każda operacja maszyny/programu/konfiguracji wymaga tokenu — bez wyjątków.
OPEN_PATHS = frozenset({f"{API}/health", f"{API}/info"})


def create_app(app: Application, *, token: str = "",
               extra_hosts: Iterable[str] = (),
               allow_origins: Iterable[str] = (),
               allow_any_host: bool = False) -> FastAPI:
    """Aplikacja FastAPI z trasami API; ``token`` pusty = brak wymogu (tylko localhost)."""
    fastapi_app = FastAPI(title="linumeRT headless", version=_version(app),
                          docs_url=None, redoc_url=None, openapi_url=None)
    hub = ConnectionHub(app)
    allowed_hosts = {"127.0.0.1", "localhost", "[::1]", *extra_hosts}
    allowed_origins = set(allow_origins)

    def token_ok(candidate: str | None) -> bool:
        if not token:
            return True
        return candidate == token

    def host_ok(host: str | None) -> bool:
        if allow_any_host:  # jawne opt-in (podgląd przez proxy); domyślnie wyłączone
            return True
        if host is None:
            return False
        return host.split(":")[0].strip("[]") in allowed_hosts or host in allowed_hosts

    def origin_ok(origin: str | None) -> bool:
        if origin is None or not allowed_origins:
            return True
        return origin in allowed_origins

    def request_token(request: Request) -> str:
        header = request.headers.get("x-lrt-token")
        if header:
            return header
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return str(request.query_params.get("token", ""))

    def guard(request: Request) -> None:
        if not host_ok(request.headers.get("host")):
            raise PermissionDenied("odrzucono: nieznany Host (możliwy DNS-rebinding)",
                                   details={"host": request.headers.get("host", "")})
        if not origin_ok(request.headers.get("origin")):
            raise PermissionDenied("odrzucono: Origin spoza listy dozwolonych",
                                   details={"origin": request.headers.get("origin", "")})
        if request.url.path in OPEN_PATHS:
            return  # health-check bez poświadczeń (reszta wymaga tokenu)
        if not token_ok(request_token(request)):
            raise PermissionDenied("brak albo błędny token (X-LRT-Token)")

    @fastapi_app.middleware("http")
    async def guard_middleware(request: Request, call_next):
        if request.url.path.startswith(API) or request.url.path == "/ws":
            try:
                guard(request)
            except ApiError as exc:
                return error_response(exc)
        return await call_next(request)

    # ---- HTTP --------------------------------------------------------------
    @fastapi_app.get(f"{API}/health")
    def health() -> dict[str, Any]:
        return app.call_json("system.health", channel="rest")

    @fastapi_app.get(f"{API}/info")
    def info() -> dict[str, Any]:
        return app.call_json("system.info", channel="rest")

    @fastapi_app.get(f"{API}/contract")
    def contract() -> dict[str, Any]:
        """Kontrakt operacji — podstawa codegen dla dowolnego GUI."""
        return app.call_json("system.contract", channel="rest")

    @fastapi_app.get(f"{API}/operations")
    def operations() -> dict[str, Any]:
        """Skrócona lista operacji (bez schematów) — do szybkiego przeglądu."""
        return {
            "schema_version": SCHEMA_VERSION,
            "domains": app.contract.domains(),
            "operations": [
                {"name": o.name, "domain": o.domain, "kind": o.kind, "status": o.status,
                 "safety": o.safety, "role": o.role, "summary": o.summary}
                for o in app.contract.operations()
            ],
            "events": app.contract.events(),
        }

    @fastapi_app.get(f"{API}/state")
    def state(topics: str = "") -> dict[str, Any]:
        selected = tuple(t for t in topics.split(",") if t) or None
        return app.state(selected).model_dump(mode="json")

    # Jedna trasa dla wszystkich operacji. Rejestrowana ręcznie, bo ``params`` jest
    # dowolnym obiektem JSON — walidacją zajmuje się schemat operacji w kontrakcie,
    # a nie warstwa HTTP (inaczej GUI musiałoby znać typy Pythona).
    _register_call_route(fastapi_app, app, request_token)

    # ---- WebSocket ---------------------------------------------------------
    @fastapi_app.websocket("/ws")
    async def websocket(socket: WebSocket) -> None:
        # Middleware HTTP nie obejmuje handshake WebSocket.
        if not host_ok(socket.headers.get("host")) or not origin_ok(socket.headers.get("origin")):
            await socket.close(code=4403)
            return
        token = socket.query_params.get("token", "") or socket.headers.get("x-lrt-token", "")
        if not token_ok(token):
            await socket.close(code=4401)
            return
        await socket.accept()
        await hub.serve(socket, token)

    return fastapi_app


def _register_call_route(fastapi_app: FastAPI, app: Application, request_token) -> None:
    """``POST /api/v1/call`` — jedna trasa dla wszystkich operacji kontraktu."""

    async def endpoint(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            return error_response(InvalidRequest(f"ciało żądania nie jest JSON: {exc}"))
        if not isinstance(payload, dict):
            return error_response(InvalidRequest("oczekiwano obiektu JSON"))
        command = str(payload.get("command", ""))
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return error_response(InvalidRequest("params musi być obiektem"))
        try:
            result = app.call(command, params, channel="rest",
                              token=request_token(request),
                              call_id=payload.get("id", 0))
        except ApiError as exc:
            return error_response(exc)
        return JSONResponse({"ok": True, "id": payload.get("id", 0),
                             "result": result.model_dump(mode="json")})

    fastapi_app.add_api_route(f"{API}/call", endpoint, methods=["POST"],
                              include_in_schema=False)


def _version(app: Application) -> str:
    from .. import __version__

    return __version__


__all__ = ["API", "ConnectionHub", "create_app", "error_response"]
