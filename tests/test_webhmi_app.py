"""Testy aplikacji web-hmi (REST + WebSocket) bez LinuxCNC.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

import pytest
from linumert.cnc import FakeMachine, Mode
from linumert_webhmi import FakeBackend, Gateway, create_app
from linumert_webhmi.app import MAX_CLIENTS, MAX_MESSAGE_BYTES
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

TOKEN = "t" * 24
HEADERS = {"x-linumert-token": TOKEN}
BASE = "http://127.0.0.1:8765"


@pytest.fixture
def gateway():
    machine = FakeMachine()
    machine.estop_reset()
    machine.power_on()
    machine.home()
    machine.run_until_idle()
    machine.set_mode(Mode.MANUAL)
    return Gateway(FakeBackend(machine))


@pytest.fixture
def client(gateway):
    return TestClient(create_app(gateway, TOKEN), base_url=BASE)


def connect(client, **headers):
    """TestClient WebSocket zawsze wysyła Host: testserver, więc ustawiamy go jak przeglądarka."""
    return client.websocket_connect("/ws", headers={"host": "127.0.0.1:8765", **headers})


def hello(ws, token=TOKEN):
    ws.send_json({"auth": token})
    return ws.receive_json()


def test_token_must_be_long_enough(gateway):
    with pytest.raises(ValueError):
        create_app(gateway, "krotki")


def test_health_is_open_state_and_command_need_token(client):
    assert client.get("/api/health").json()["ok"] is True
    assert client.get("/api/state").status_code == 401
    assert client.get("/api/state", headers={"x-linumert-token": "zly" * 8}).status_code == 401
    assert client.post("/api/command", json={"cmd": "estop"}).status_code == 401
    state = client.get("/api/state", headers=HEADERS).json()["state"]
    assert state["task_state"] == "on" and state["schema"] == 1


def test_foreign_host_header_is_rejected(gateway):
    app = create_app(gateway, TOKEN)
    rebinding = TestClient(app, base_url="http://evil.example:8765")
    assert rebinding.get("/api/health").status_code == 403
    assert TestClient(app, base_url="http://localhost:8765").get("/api/health").status_code == 200


def test_rest_command_ok_conflict_and_validation(client):
    ok = client.post("/api/command", headers=HEADERS, json={"cmd": "jog", "axis": "X",
                                                            "speed": 1.0})
    assert ok.status_code == 200
    client.post("/api/command", headers=HEADERS, json={"cmd": "estop"})
    refused = client.post("/api/command", headers=HEADERS, json={"cmd": "jog", "axis": "X",
                                                                 "speed": 1.0})
    assert refused.status_code == 409 and "wlaczona" in refused.json()["detail"]
    bad = client.post("/api/command", headers=HEADERS, json={"cmd": "jog", "axis": "X",
                                                             "speed": 999})
    assert bad.status_code == 422


def test_websocket_auth_state_and_command(client, gateway):
    with connect(client) as ws:
        first = hello(ws)
        assert first["type"] == "state" and first["state"]["task_state"] == "on"
        ws.send_json({"id": 7, "cmd": "jog", "axis": "X", "speed": 2.0})
        seen = []
        for _ in range(20):
            message = ws.receive_json()
            seen.append(message)
            if message["type"] == "ack":
                break
        assert {"type": "ack", "id": 7} in seen
        ws.send_json({"id": 8, "cmd": "estop"})
        ws.send_json({"id": 9, "cmd": "jog", "axis": "X", "speed": 2.0})
        replies = {}
        while 9 not in replies:
            message = ws.receive_json()
            if message["type"] in ("ack", "error"):
                replies[message["id"]] = message
        assert replies[9]["type"] == "error" and "wlaczona" in replies[9]["message"]


def test_websocket_wrong_token_and_no_auth_are_closed(client):
    with connect(client) as ws:
        ws.send_json({"auth": "zly" * 8})
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
        assert info.value.code == 4401
    with connect(client) as ws:
        ws.send_text("to nie jest json")
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
        assert info.value.code == 4401


def test_websocket_foreign_origin_is_rejected(client):
    with pytest.raises(WebSocketDisconnect) as info:
        with connect(client, origin="http://evil.example"):
            pass
    assert info.value.code == 4403
    with connect(client, origin=BASE) as ws:
        assert hello(ws)["type"] == "state"


def test_websocket_foreign_host_is_rejected(client):
    with pytest.raises(WebSocketDisconnect) as info:
        with connect(client, host="evil.example:8765"):
            pass
    assert info.value.code == 4403


def test_websocket_oversized_and_invalid_messages_get_errors(client):
    with connect(client) as ws:
        hello(ws)
        ws.send_text("x" * (MAX_MESSAGE_BYTES + 1))
        ws.send_json({"id": 1, "cmd": "format_disk"})
        errors = []
        while len(errors) < 2:
            message = ws.receive_json()
            if message["type"] == "error":
                errors.append(message)
        assert "za duża" in errors[0]["message"]
        assert errors[1]["id"] == 1 and "niepoprawne" in errors[1]["message"]


def test_websocket_disconnect_stops_jog(client, gateway):
    with connect(client) as ws:
        hello(ws)
        ws.send_json({"id": 1, "cmd": "jog", "axis": "X", "speed": 2.0})
        while ws.receive_json().get("type") != "ack":
            pass
        assert gateway.backend.machine._jog  # jog trwa
    assert not gateway.backend.machine._jog  # rozłączenie ostatniego klienta zdjęło jog


def test_client_limit(client):
    sockets = []
    try:
        for _ in range(MAX_CLIENTS):
            ws = connect(client).__enter__()
            hello(ws)
            sockets.append(ws)
        with pytest.raises(WebSocketDisconnect) as info:
            with connect(client) as extra:
                extra.receive_json()
        assert info.value.code == 4429
    finally:
        for ws in sockets:
            ws.__exit__(None, None, None)
