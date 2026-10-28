"""Protokół WebSocket: push stanu, wybór tematów, polecenia i sesja jogu.

SPDX-License-Identifier: GPL-2.0-or-later

To jest główny kanał przyszłego GUI: jedna migawka na dzień dobry, potem zmiany.
Testy sprawdzają też rzeczy, które łatwo zepsuć po cichu — brak wycieku subskrypcji
przy wielu klientach i czytelny błąd dla wiadomości, która nie jest poleceniem.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from linumert_headless.transport.rest import create_app  # noqa: E402

TEST_HOST = "testserver"


@pytest.fixture
def client(app):
    with TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,))) as http:
        yield http


def ws_url(token: str = "sekret") -> str:
    return f"/ws?token={token}"


def push(app) -> None:
    """Wymusza publikację stanu.

    W produkcji robi to pętla odpytywania (50 Hz); testy mają zegar ręczny, więc
    napędzają push jawnie — inaczej ``receive_json`` czekałby wiecznie.
    """
    app.publish_state()


def next_state(ws, limit: int = 20) -> dict:
    """Pierwsza wiadomość ``state`` — pomija odpowiedzi na polecenia."""
    for _ in range(limit):
        message = ws.receive_json()
        if message.get("type") == "state":
            return message
    raise AssertionError("brak wiadomości state w oczekiwanym czasie")


def test_hello_zawiera_migawke_i_wersje(client) -> None:
    with client.websocket_connect(ws_url()) as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["schema"] == 1
        assert hello["session"]
        assert hello["version"] >= 0
        assert set(hello["topics"]) >= {"machine", "alarms"}
        assert hello["topics"]["machine"]["schema_version"] == 1


def test_wybor_tematow_ogranicza_push(app, client) -> None:
    """GUI bierze tylko to, co pokazuje — reszta nie zajmuje łącza."""
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()  # hello
        ws.send_json({"type": "hello", "topics": ["machine"]})
        filtered = ws.receive_json()
        assert filtered["type"] == "hello"
        assert set(filtered["topics"]) == {"machine"}

        # Zmiana musi być rzeczywista: hub pomija powiadomienie przy identycznym
        # payloadzie, a atrapa startuje w E-STOP — samo machine.estop nic nie zmienia.
        ws.send_json({"id": 1, "command": "machine.estop_reset", "params": {}})
        assert ws.receive_json()["ok"] is True
        push(app)
        assert set(next_state(ws)["topics"]) == {"machine"}


def test_nieznany_temat_daje_czytelny_blad(client) -> None:
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()
        ws.send_json({"type": "hello", "topics": ["nie_ma"]})
        reply = ws.receive_json()
        assert reply["ok"] is False
        assert reply["error"]["code"] == "invalid_request"
        assert "nieznane tematy" in reply["error"]["message"]
        assert "machine" in reply["error"]["details"]["known"]


def test_wiadomosc_bez_polecenia_nie_udaje_operacji(client) -> None:
    """Błąd ma mówić, czego brakuje — a nie 'nieznana operacja: '."""
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()
        ws.send_json({"id": 5, "params": {}})
        reply = ws.receive_json()
        assert reply["ok"] is False
        assert reply["id"] == 5
        assert reply["error"]["code"] == "invalid_request"
        assert "command" in reply["error"]["message"]
        assert "nieznana operacja" not in reply["error"]["message"]


def test_zly_json_i_nie_obiekt_sa_odrzucane(client) -> None:
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()
        ws.send_text("{to nie jest json")
        assert ws.receive_json()["error"]["code"] == "invalid_request"
        ws.send_json([1, 2, 3])
        assert ws.receive_json()["error"]["code"] == "invalid_request"


def test_ping_podtrzymuje_sesje(client) -> None:
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"
        ws.send_json({"ping": True})  # zapis alternatywny
        assert ws.receive_json()["type"] == "pong"


def test_state_get_zwraca_pelna_migawke(client) -> None:
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()
        ws.send_json({"id": 9, "method": "state.get"})
        reply = ws.receive_json()
        assert reply["id"] == 9
        assert reply["ok"] is True
        assert set(reply["result"]) >= {"machine", "alarms"}


def test_polecenie_przez_ws_dziala_i_daje_push(app, client) -> None:
    with client.websocket_connect(ws_url()) as ws:
        hello = ws.receive_json()
        assert hello["topics"]["machine"]["task_state"] == "estop"

        ws.send_json({"id": 2, "command": "machine.estop_reset", "params": {}})
        reply = ws.receive_json()
        assert reply["ok"] is True

        push(app)
        # Po resecie E-STOP maszyna jest w stanie "estop_reset" — zasilanie jeszcze nie.
        assert next_state(ws)["topics"]["machine"]["task_state"] == "estop_reset"

        ws.send_json({"id": 3, "method": "state.get"})
        assert ws.receive_json()["result"]["machine"]["task_state"] == "estop_reset"


def test_brak_tokenu_zamyka_polaczenie(app) -> None:
    """Bez tokenu serwer zamyka połączenie (kod 4401) — GUI dostaje jednoznaczny sygnał."""
    with TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,))) as http:
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with http.websocket_connect("/ws") as ws:
                ws.receive_json()
        assert excinfo.value.code == 4401


def test_dwa_polaczenia_nie_wykradaja_sobie_subskrypcji(app, client) -> None:
    """Każdy klient GUI ma własną subskrypcję; po zamknięciu nie zostaje ślad."""
    baseline = len(app.hub._listeners)
    with client.websocket_connect(ws_url()) as first:
        first.receive_json()
        with client.websocket_connect(ws_url()) as second:
            second.receive_json()
            assert len(app.hub._listeners) == baseline + 2

            # Zmiana stanu dociera do obu klientów — nie tylko do ostatniego.
            first.send_json({"id": 1, "command": "machine.estop_reset", "params": {}})
            assert first.receive_json()["ok"] is True
            push(app)
            message = next_state(second)
            assert message["topics"]["machine"]["task_state"] == "estop_reset"
        assert len(app.hub._listeners) == baseline + 1
    assert len(app.hub._listeners) == baseline, "subskrypcje muszą być sprzątane"


def test_jog_przez_ws_dostaje_sesje_i_staje_po_rozlaczeniu(app, client) -> None:
    """Deadman: sesja WebSocket jest właścicielem jogu i znika razem z połączeniem."""
    with client.websocket_connect(ws_url()) as ws:
        ws.receive_json()
        for command in ("machine.estop_reset", "machine.power_on"):
            ws.send_json({"id": 1, "command": command, "params": {}})
            assert ws.receive_json()["ok"] is True
        ws.send_json({"id": 2, "command": "machine.home", "params": {}})
        assert ws.receive_json()["ok"] is True

        app.backend.tick()
        app.backend.advance(1.0)  # domknięcie bazowania

        ws.send_json({"id": 3, "command": "machine.jog",
                      "params": {"axis": "X", "speed": 10.0}})
        assert ws.receive_json()["ok"] is True
        assert app.backend.machine._jog["X"] == 10.0

    app.backend.tick()
    app.backend.advance(0.2)
    # jog_stop usuwa oś ze słownika jogów (FakeMachine.jog_stop → pop), więc brak klucza
    # oznacza zatrzymany ruch — deadman zadziałał po zerwaniu połączenia.
    assert app.backend.machine._jog.get("X", 0.0) == 0.0, \
        "jog musi stanąć po zerwaniu połączenia"
