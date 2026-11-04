"""Magazyn stanu: wersjonowane migawki domen i zdarzenia dla klientów.

SPDX-License-Identifier: GPL-2.0-or-later

GUI nigdy nie odpytuje maszyny ani Plant bezpośrednio. Czyta **stan** z tego magazynu
(REST ``GET /api/v1/state`` albo push przez WebSocket) i wysyła **operacje** kontraktu.
Każdy temat ma rosnący ``version``, więc klient może:

- pobrać pełną migawkę przy starcie,
- potem dostawać tylko zmiany (``since=version``),
- wykryć zgubioną wiadomość (dziura w wersjach) i odświeżyć całość.

Magazyn jest synchronizowany i bez zależności od transportu — ten sam obiekt obsługuje
REST, WebSocket, CLI i testy.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from typing import Any

Listener = Callable[[str, dict[str, Any], int], None]

HISTORY_LIMIT = 512


class StateHub:
    """Stan aplikacji: tematy, wersje, historia zmian i subskrypcje."""

    def __init__(self, history_limit: int = HISTORY_LIMIT):
        self._lock = threading.RLock()
        self._topics: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, int] = {}
        self._version = 0
        self._history: deque[tuple[int, str, dict[str, Any]]] = deque(maxlen=history_limit)
        self._listeners: list[Listener] = []

    # ---- zapis -------------------------------------------------------------
    def publish(self, topic: str, payload: dict[str, Any]) -> int:
        """Ustawia temat i powiadamia subskrybentów; zwraca wersję globalną."""
        with self._lock:
            previous = self._topics.get(topic)
            if previous == payload:
                return self._version
            self._version += 1
            self._versions[topic] = self._versions.get(topic, 0) + 1
            self._topics[topic] = payload
            self._history.append((self._version, topic, payload))
            version, listeners = self._version, list(self._listeners)
        for listener in listeners:
            listener(topic, payload, version)
        return version

    def update(self, topic: str, **fields: Any) -> int:
        """Łączy pola z istniejącym tematem (wygodne dla liczników i statusów)."""
        with self._lock:
            current = dict(self._topics.get(topic) or {})
        current.update(fields)
        return self.publish(topic, current)

    # ---- odczyt ------------------------------------------------------------
    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def snapshot(self, *, topics: tuple[str, ...] | None = None) -> dict[str, Any]:
        with self._lock:
            keys = topics or tuple(sorted(self._topics))
            return {
                "version": self._version,
                "topics": {k: self._topics[k] for k in keys if k in self._topics},
                "topic_versions": {k: self._versions[k] for k in keys if k in self._versions},
            }

    def get(self, topic: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._topics.get(topic)
            return dict(value) if isinstance(value, dict) else value

    def changes_since(self, version: int) -> list[dict[str, Any]]:
        """Zmiany po ``version`` — do przyrostowego odświeżania GUI bez pełnej migawki."""
        with self._lock:
            items = [e for e in self._history if e[0] > version]
        return [{"version": v, "topic": t, "payload": p} for v, t, p in items]

    # ---- subskrypcje -------------------------------------------------------
    def subscribe(self, listener: Listener) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def topics(self) -> list[str]:
        with self._lock:
            return sorted(self._topics)


__all__ = ["StateHub"]
