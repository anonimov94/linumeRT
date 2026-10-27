"""Aplikacja FastAPI bramy web: REST + WebSocket z tokenem, kontrolą Host i Origin.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

- REST: ``GET /api/health`` (bez tokenu), ``GET /api/state``, ``POST /api/command``
  (nagłówek ``X-Linumert-Token``).
- WebSocket ``/ws``: pierwsza wiadomość ``{"auth": "<token>"}`` w ciągu ``AUTH_TIMEOUT_S``;
  potem serwer wysyła ``{"type":"state","version":n,"state":{...}}`` przy zmianie stanu
  (≤ ``PUSH_HZ``, keepalive co 0,2 s), a klient polecenia ``{"id":..,"cmd":..}`` z odpowiedzią
  ``ack``/``error``. Token nigdy w URL.
- Host (ochrona przed DNS rebinding) i Origin (strona z innego źródła nie otworzy sesji)
  muszą należeć do dozwolonych; domyślnie tylko loopback.
Bezpieczeństwo fizyczne to obwód sprzętowy; brama jest ekranem, nie funkcją bezpieczeństwa.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .backend import CommandError
from .gateway import Gateway
from .schema import SCHEMA_VERSION, Command

PUSH_HZ = 30.0
KEEPALIVE_S = 0.2
AUTH_TIMEOUT_S = 3.0
MAX_MESSAGE_BYTES = 2048
MAX_CLIENTS = 4
MAX_PENDING = 8  # połączenia czekające na uwierzytelnienie
STATIC = Path(__file__).resolve().parent / "static"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "[::1]")


def _host_only(value: str) -> str:
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def create_app(gateway: Gateway, token: str, extra_hosts: tuple[str, ...] = ()) -> FastAPI:
    if len(token) < 16:
        raise ValueError("token bramy: co najmniej 16 znaków")
    allowed_hosts = set(LOOPBACK_HOSTS) | set(extra_hosts)
    app = FastAPI(title="linumeRT web-hmi", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.gateway = gateway
    sockets = {"count": 0, "pending": 0}

    def token_ok(candidate: object) -> bool:
        return isinstance(candidate, str) and hmac.compare_digest(
            candidate.encode(), token.encode())

    def host_ok(host_header: str | None) -> bool:
        return bool(host_header) and _host_only(host_header) in allowed_hosts

    def origin_ok(origin: str | None) -> bool:
        if origin is None:  # klient spoza przeglądarki (testy, narzędzia): token i tak wymagany
            return True
        try:
            parts = urlsplit(origin)
            host = f"[{parts.hostname}]" if parts.hostname and ":" in parts.hostname else (
                parts.hostname or "")
            parts.port  # noqa: B018 - wymusza walidację numeru portu
        except ValueError:
            return False
        return (parts.scheme in ("http", "https") and not parts.username
                and not parts.path.strip("/") and not parts.query and not parts.fragment
                and host in allowed_hosts)

    @app.middleware("http")
    async def guard_host(request: Request, call_next):
        if not host_ok(request.headers.get("host")):
            return JSONResponse({"detail": "niedozwolony nagłówek Host"}, status_code=403)
        return await call_next(request)

    def need_token(request: Request) -> None:
        if not token_ok(request.headers.get("x-linumert-token")):
            raise HTTPException(401, "brak lub zły token")

    @app.get("/api/health")
    def health() -> dict:
        _, state = gateway.snapshot()
        return {"ok": True, "schema": SCHEMA_VERSION, "task_state": state.get("task_state")}

    @app.get("/api/state")
    def get_state(request: Request) -> dict:
        need_token(request)
        version, state = gateway.snapshot()
        return {"version": version, "state": state}

    @app.post("/api/command")
    def post_command(request: Request, command: Command) -> dict:
        need_token(request)
        try:
            gateway.execute(command)
        except CommandError as error:
            raise HTTPException(409, str(error)) from None
        return {"ok": True}

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        if not host_ok(socket.headers.get("host")) or not origin_ok(
                socket.headers.get("origin")):
            await socket.close(code=4403)
            return
        await socket.accept()
        if sockets["count"] >= MAX_CLIENTS or sockets["pending"] >= MAX_PENDING:
            await socket.close(code=4429)
            return
        sockets["pending"] += 1
        try:
            first = await asyncio.wait_for(socket.receive_text(), AUTH_TIMEOUT_S)
            auth = json.loads(first) if len(first) <= MAX_MESSAGE_BYTES else {}
        except (TimeoutError, ValueError, WebSocketDisconnect):
            await _close(socket, 4401)
            return
        finally:
            sockets["pending"] -= 1
        if not isinstance(auth, dict) or not token_ok(auth.get("auth")):
            await _close(socket, 4401)
            return
        sockets["count"] += 1
        session = secrets.token_hex(8)
        gateway.client_connected(session)
        try:
            await _serve(socket, gateway, session)
        except WebSocketDisconnect:
            pass
        finally:
            sockets["count"] -= 1
            gateway.client_disconnected(session)

    if (STATIC / "index.html").exists():
        app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


async def _close(socket: WebSocket, code: int) -> None:
    try:
        await socket.close(code=code)
    except RuntimeError:
        pass


async def _serve(socket: WebSocket, gateway: Gateway, session: str) -> None:
    async def pusher() -> None:
        sent, last = -1, 0.0
        loop = asyncio.get_running_loop()
        while True:
            version, state = gateway.snapshot()
            now = loop.time()
            if version != sent or now - last >= KEEPALIVE_S:
                await socket.send_json({"type": "state", "version": version, "state": state})
                sent, last = version, now
            await asyncio.sleep(1.0 / PUSH_HZ)

    task = asyncio.create_task(pusher())
    try:
        while True:
            text = await socket.receive_text()
            if len(text) > MAX_MESSAGE_BYTES:
                await socket.send_json({"type": "error", "message": "wiadomość za duża"})
                continue
            msg_id = None
            try:
                data = json.loads(text)
                msg_id = data.get("id") if isinstance(data, dict) else None
                command = Command.model_validate(data)
                await asyncio.to_thread(gateway.execute, command, session)
                await socket.send_json({"type": "ack", "id": msg_id})
            except (ValueError, ValidationError) as error:
                await socket.send_json({"type": "error", "id": msg_id,
                                        "message": f"niepoprawne polecenie: {error}"[:300]})
            except CommandError as error:
                await socket.send_json({"type": "error", "id": msg_id, "message": str(error)})
            except Exception:  # noqa: BLE001 - jedno złe polecenie nie zrywa sesji
                await socket.send_json({"type": "error", "id": msg_id,
                                        "message": "błąd wewnętrzny bramy"})
    finally:
        task.cancel()
