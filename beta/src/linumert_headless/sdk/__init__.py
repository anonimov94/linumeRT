"""SDK Pythona — klient kontraktu dla GUI, skryptów i testów integracyjnych.

SPDX-License-Identifier: GPL-2.0-or-later

Zbudowany na kontrakcie, więc **nowa operacja backendu pojawia się w SDK automatycznie**:
``client.call("domena.akcja", ...)`` działa zawsze, a skróty ``client.machine.home(...)``
są generowane z ``GET /api/v1/contract`` przy pierwszym użyciu.

Przykład (dokładnie tak będzie wołać to przyszłe GUI)::

    from linumert_headless.sdk import Client

    client = Client("http://127.0.0.1:8080", token="...")
    client.machine.power_on()
    client.machine.home(axis="X")
    state = client.machine.state()
    for change in client.subscribe():          # generator zmian stanu
        print(change["version"], list(change["topics"]))
"""

from __future__ import annotations

from .client import ApiClientError, Client, DomainProxy, RemoteError

__all__ = ["ApiClientError", "Client", "DomainProxy", "RemoteError"]
