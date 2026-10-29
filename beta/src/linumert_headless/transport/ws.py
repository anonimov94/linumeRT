"""Transport WebSocket: stan na żywo i wywoływanie operacji z GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Protokół (JSON, jedna wiadomość = jeden obiekt):

- serwer → klient: ``{"type": "hello", "session", "version", "schema", "topics"}`` na
  dzień dobry (pełna migawka wybranych tematów), potem ``{"type": "state", "version",
  "topics": {...}}`` przy każdej zmianie (stan maszyny 20 Hz, alarmy przy zmianie),
- klient → serwer:
  - ``{"id", "command", "params"}`` — wywołanie operacji z kontraktu; odpowiedź
    ``{"id", "ok", "result"|"error"}``,
  - ``{"id", "method": "state.get"}`` — pełna migawka (odświeżenie po luce w ``version``),
  - ``{"type": "hello", "topics": [...]}`` — wybór tematów (mniejszy ruch w GUI),
  - ``{"type": "ping"}`` — podtrzymanie sesji; odpowiedź ``{"type": "pong"}``.

Klient wykrywa zgubioną wiadomość po luce w ``version`` i odświeża całość przez
``state.get``. Dzięki temu GUI nie musi znać Pythona ani backendu — wystarczy JSON.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..app import Application
from ..schema import SCHEMA_VERSION

log = logging.getLogger("linumert.transport.ws")

STATE_PUSH_HZ = 20.0  # GUI nie potrzebuje 50 Hz; stan i tak jest migawką


class _Connection:
    """Stan jednego połączenia: kolejka zmian i wybrane tematy.

    Trzymany lokalnie (nie na hubie), bo hub jest współdzielony przez wszystkie
    połączenia — atrybut na hubie nadpisywałby się przy drugim kliencie GUI.
    """

    def __init__(self, queue: asyncio.Queue) -> None:
        self.queue = queue
        self.wanted: set[str] | None = None  # None = wszystkie tematy


class ConnectionHub:
    """Rozsyła zmiany stanu do podłączonych klientów i obsługuje ich polecenia."""

    def __init__(self, app: Application, push_hz: float = STATE_PUSH_HZ):
        self.app = app
        self.push_hz = push_hz

    async def serve(self, socket: WebSocket, token: str = "") -> None:
        session = self.app.sessions.open()
        conn = _Connection(asyncio.Queue(maxsize=256))

        def on_change(topic: str, payload: dict[str, Any], version: int) -> None:
            # Wywołane z wątku pętli stanu — przerzucamy do pętli asyncio.
            if conn.wanted is not None and topic not in conn.wanted:
                return  # klient nie subskrybuje tego tematu
            try:
                conn.queue.put_nowait({"type": "state", "version": version,
                                       "topics": {topic: payload}})
            except asyncio.QueueFull:
                log.debug("kolejka WebSocket pełna — klient odświeży przez state.get")

        unsubscribe = self.app.hub.subscribe(on_change)  # lokalne: każde połączenie swoje
        try:
            await socket.send_json(self._hello(session))
            pusher = asyncio.create_task(self._push(socket, conn))
            try:
                await self._receive(socket, session, token, conn)
            finally:
                pusher.cancel()
        except WebSocketDisconnect:
            pass
        except Exception:
            log.exception("połączenie WebSocket zakończone błędem")
        finally:
            unsubscribe()
            for axis in self.app.sessions.close(session):
                # Sesja zniknęła — jog musi stanąć (deadman).
                try:
                    self.app.call("machine.jog_stop", {"axis": axis}, channel="ws")
                except Exception:
                    log.warning("stop jogu po rozłączeniu %s nie powiódł się", axis,
                                exc_info=True)

    # ---- wiadomości serwera -------------------------------------------------
    def _hello(self, session: str, wanted: set[str] | None = None) -> dict[str, Any]:
        topics = self.app.hub.snapshot()["topics"]
        if wanted is not None:
            topics = {k: v for k, v in topics.items() if k in wanted}
        return {"type": "hello", "session": session, "schema": SCHEMA_VERSION,
                "version": self.app.hub.version, "topics": topics}

    async def _push(self, socket: WebSocket, conn: _Connection) -> None:
        period = 1.0 / self.push_hz
        while True:
            try:
                message = await asyncio.wait_for(conn.queue.get(), timeout=period)
            except TimeoutError:
                continue
            # Sklejamy zmiany z tego samego okna, żeby nie zasypywać GUI pakietami.
            topics: dict[str, Any] = dict(message.get("topics", {}))
            version = message.get("version", 0)
            while not conn.queue.empty():
                extra = conn.queue.get_nowait()
                topics.update(extra.get("topics", {}))
                version = max(version, extra.get("version", 0))
            await socket.send_json({"type": "state", "version": version, "topics": topics})

    # ---- wiadomości klienta -------------------------------------------------
    async def _receive(self, socket: WebSocket, session: str, token: str,
                       conn: _Connection) -> None:
        while True:
            raw = await socket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await socket.send_json(self._bad(message_id=None,
                                                 text="wiadomość nie jest JSON"))
                continue
            if not isinstance(message, dict):
                await socket.send_json(self._bad(None, "oczekiwano obiektu JSON"))
                continue

            kind = str(message.get("type", ""))
            if kind == "ping" or message.get("ping"):
                self.app.sessions.touch(session)
                await socket.send_json({"type": "pong"})
                continue

            if kind == "hello" or "hello" in message:
                # Wybór tematów: GUI bierze tylko to, co pokazuje (mniej ruchu w sieci).
                request = message.get("hello") or message
                topics = request.get("topics")
                conn.wanted = {str(t) for t in topics} if isinstance(topics, list) else None
                known = set(self.app.hub.snapshot()["topics"])
                if conn.wanted is not None:
                    unknown = sorted(conn.wanted - known)
                    if unknown:
                        await socket.send_json(self._bad(
                            message.get("id"),
                            f"nieznane tematy: {', '.join(unknown)}",
                            details={"known": sorted(known)}))
                        conn.wanted = None
                        continue
                await socket.send_json(self._hello(session, conn.wanted))
                continue

            if message.get("method") == "state.get":
                self.app.sessions.touch(session)
                response = self.app.handle_message(message, channel="ws", token=token)
                await socket.send_json(response.model_dump(mode="json"))
                continue

            command = message.get("command")
            if not isinstance(command, str) or not command.strip():
                # Jasny komunikat zamiast "nieznana operacja: " — GUI ma wiedzieć,
                # że wiadomość nie jest wywołaniem operacji.
                await socket.send_json(self._bad(
                    message.get("id"),
                    "oczekiwano pola 'command' (nazwa operacji z kontraktu), "
                    "'method': 'state.get' albo 'type': 'ping'|'hello'",
                    details={"known_types": ["ping", "hello"], "method": "state.get"}))
                continue

            params = dict(message.get("params") or {})
            # Sesja WebSocket jest właścicielem jogu — dokładamy ją do params,
            # żeby deadman działał bez zmian w GUI.
            if command.startswith("machine.jog") and "session" not in params:
                params["session"] = session
            self.app.sessions.touch(session)
            response = self.app.handle_message(message | {"command": command, "params": params},
                                               channel="ws", token=token)
            await socket.send_json(response.model_dump(mode="json"))

    @staticmethod
    def _bad(message_id: Any, text: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"id": message_id if message_id is not None else 0, "ok": False, "result": None,
                "error": {"code": "invalid_request", "message": text,
                          "details": details or {}}}


__all__ = ["STATE_PUSH_HZ", "ConnectionHub"]
