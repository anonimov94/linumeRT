"""Klient SDK: REST + WebSocket na kontrakcie operacji.

SPDX-License-Identifier: GPL-2.0-or-later

Klient nie ma ręcznie pisanych metod per funkcja — **dziedziny i metody generuje
z kontraktu** (``GET /api/v1/contract``). Dlatego:

- ``client.machine.home(axis="X")`` działa tak samo jak ``client.call("machine.home", ...)``;
- gdy backend dostanie nową operację, SDK widzi ją bez zmiany kodu — to samo, co GUI;
- walidacja parametrów odbywa się po stronie serwera (jedno źródło prawdy), a klient
  zgłasza ``RemoteError`` z kodem błędu z kontraktu.

Zależności: ``urllib`` (stdlib) dla REST; ``websockets`` tylko dla ``subscribe()``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from typing import Any


class ApiClientError(Exception):
    """Błąd klienta SDK (sieć, brak kontraktu, nieznana operacja)."""


class RemoteError(ApiClientError):
    """Błąd zwrócony przez serwer: ``code`` pochodzi z kontraktu błędów."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = details or {}


class DomainProxy:
    """``client.machine`` — zbiór metod jednej domeny, generowany z kontraktu."""

    def __init__(self, client: Client, domain: str, operations: list[dict[str, Any]]):
        self._client = client
        self.domain = domain
        self.operations = {o["name"]: o for o in operations}
        for name in self.operations:
            action = name.split(".", 1)[1]
            setattr(self, action, self._make_method(name))

    def _make_method(self, name: str):
        def method(**params: Any) -> Any:
            return self._client.call(name, **params)

        operation = self.operations[name]
        method.__name__ = name.split(".", 1)[1]
        method.__doc__ = (f"{operation.get('summary', '')}\n\n"
                          f"status: {operation.get('status')}, safety: "
                          f"{operation.get('safety')}, rola: {operation.get('role')}")
        return method

    def __repr__(self) -> str:
        return f"<DomainProxy {self.domain}: {len(self.operations)} operacji>"


class Client:
    """Klient aplikacji headless (REST + WebSocket)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080", token: str = "",
                 timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = ""
        self._contract: dict[str, Any] | None = None
        self._domains: dict[str, DomainProxy] = {}

    # ---- kontrakt ----------------------------------------------------------
    @property
    def contract(self) -> dict[str, Any]:
        if self._contract is None:
            self._contract = self._get("/api/v1/contract")
        return self._contract

    def operations(self) -> list[dict[str, Any]]:
        return list(self.contract.get("operations", []))

    def __getattr__(self, item: str) -> DomainProxy:
        """``client.machine`` — domena z kontraktu (leniwie, po pierwszym użyciu)."""
        if item.startswith("_") or item in {"base_url", "token", "timeout", "session"}:
            raise AttributeError(item)
        domains = {o["domain"] for o in self.operations()}
        if item not in domains:
            raise AttributeError(f"brak domeny {item!r} w kontrakcie; dostępne: "
                                 f"{', '.join(sorted(domains))}")
        proxy = DomainProxy(self, item,
                            [o for o in self.operations() if o["domain"] == item])
        self._domains[item] = proxy
        return proxy

    # ---- wywołania ---------------------------------------------------------
    def call(self, command: str, **params: Any) -> Any:
        payload = {"command": command, "params": params}
        response = self._post("/api/v1/call", payload)
        if not response.get("ok", False):
            error = response.get("error") or {}
            raise RemoteError(error.get("code", "error"), error.get("message", str(response)),
                              error.get("details"))
        return response.get("result")

    def state(self, topics: tuple[str, ...] | None = None) -> dict[str, Any]:
        query = f"?topics={','.join(topics)}" if topics else ""
        return self._get(f"/api/v1/state{query}")

    def health(self) -> dict[str, Any]:
        return self._get("/api/v1/health")

    def info(self) -> dict[str, Any]:
        return self._get("/api/v1/info")

    def subscribe(self, topics: tuple[str, ...] | None = None) -> Iterator[dict[str, Any]]:
        """Strumień zmian stanu przez WebSocket (wymaga pakietu ``websockets``).

        Zwraca słowniki ``{"version", "topics"}``. Luka w ``version`` oznacza zgubioną
        wiadomość — wtedy GUI powinno pobrać pełną migawkę przez ``state()``.
        """
        try:
            import asyncio

            import websockets
        except ImportError as exc:
            raise ApiClientError(
                "subscribe() wymaga pakietu websockets "
                "(pip install 'linumert-headless[server]')") from exc

        url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        query = urllib.parse.urlencode({"token": self.token} if self.token else {})
        endpoint = f"{url}/ws" + (f"?{query}" if query else "")
        wanted = set(topics) if topics else None

        async def stream() -> Any:
            async with websockets.connect(endpoint) as socket:
                hello = json.loads(await socket.recv())
                self.session = hello.get("session", "")
                yield {"version": hello.get("version", 0), "topics": hello.get("topics", {})}
                async for raw in socket:
                    message = json.loads(raw)
                    if message.get("type") != "state":
                        continue
                    if wanted and not (set(message.get("topics", {})) & wanted):
                        continue
                    yield message

        agen = stream()
        loop = asyncio.new_event_loop()
        try:
            while True:
                try:
                    message = loop.run_until_complete(agen.__anext__())
                except StopAsyncIteration:
                    return
                yield message
        finally:
            # Domknięcie generatora i pętli w tej samej pętli — inaczej websockets
            # zostawia wiszące taski keepalive po wyjściu z pętli ``for``.
            try:
                loop.run_until_complete(agen.aclose())
            except (RuntimeError, StopAsyncIteration):
                pass
            finally:
                loop.close()

    # ---- HTTP --------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"content-type": "application/json", "accept": "application/json"}
        if self.token:
            headers["x-lrt-token"] = self.token
        return headers

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(self.base_url + path, headers=self._headers())
        return self._read(request)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path, data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(), method="POST")
        return self._read(request)

    def _read(self, request: urllib.request.Request) -> dict[str, Any]:
        """Odczyt odpowiedzi; każdy błąd serwera wraca jako ``RemoteError`` z kodem.

        Dzięki temu ``client.info()`` i ``client.machine.state()`` zachowują się tak samo
        jak ``client.call(...)`` — GUI nie musi sprawdzać pola ``ok`` po każdym zapytaniu.
        """
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as inner:
                raise RemoteError("http_error", f"HTTP {exc.code}") from inner
            error = payload.get("error") or {}
            raise RemoteError(error.get("code", f"http_{exc.code}"),
                              error.get("message", f"HTTP {exc.code}"),
                              error.get("details")) from exc
        except urllib.error.URLError as exc:
            raise ApiClientError(f"brak połączenia z {self.base_url}: {exc.reason}") from exc


__all__ = ["ApiClientError", "Client", "DomainProxy", "RemoteError"]
