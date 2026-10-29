"""Transport REST i WebSocket: ten sam kontrakt co CLI i GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Testy idą przez ``httpx``/``TestClient`` na prawdziwej aplikacji FastAPI, więc sprawdzają
trasowanie, token, kontrolę Host/Origin i kształt błędów — czyli to, co zobaczy GUI.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from linumert_headless.transport.rest import create_app  # noqa: E402

API = "/api/v1"


# TestClient ASGI używa hosta "testserver" — deklarujemy go w liście dozwolonych,
# zamiast luzować kontrolę Host w kodzie produkcyjnym.
TEST_HOST = "testserver"


@pytest.fixture
def client(app):
    """Request idzie przez całą aplikację FastAPI (trasy, middleware, walidacja)."""
    with TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,)),
                    headers={"x-lrt-token": "sekret"}) as http:
        yield http


def test_health_info_i_stan(client) -> None:
    health = client.get(f"{API}/health")
    assert health.status_code == 200
    assert health.json()["backend"] == "fake"

    info = client.get(f"{API}/info")
    assert info.json()["gui"] is False

    state = client.get(f"{API}/state")
    assert "machine" in state.json()["topics"]


def test_contract_zawiera_schematy_dla_gui(client) -> None:
    payload = client.get(f"{API}/contract").json()
    assert payload["operations"]
    first = payload["operations"][0]
    assert {"name", "domain", "kind", "status", "safety", "role", "request", "result"} <= set(first)
    assert payload["events"]


def test_call_wykonuje_operacje_i_zwraca_wynik(client) -> None:
    response = client.post(f"{API}/call",
                           json={"command": "machine.state", "params": {}})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["backend"] == "fake"


def test_call_z_parametrami_przechodzi_walidacje(client) -> None:
    response = client.post(f"{API}/call",
                           json={"command": "machine.jog",
                                 "params": {"axis": "X", "speed": 5.0}})
    # Bez zasilania: odmowa bezpieczeństwa, nie błąd 500.
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "safety_refused"


def test_bledne_parametry_daja_400_z_lista_bledow(client) -> None:
    response = client.post(f"{API}/call",
                           json={"command": "machine.jog", "params": {"axis": "Q"}})
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["details"]["errors"]


def test_nieznana_operacja_daje_404(client) -> None:
    response = client.post(f"{API}/call", json={"command": "machine.nie_ma", "params": {}})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_brak_tokenu_jest_odrzucony(app) -> None:
    with TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,))) as http:
        response = http.get(f"{API}/contract")  # trasa chroniona (health/info są otwarte)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_zly_token_jest_odrzucony(app) -> None:
    with TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,)),
                    headers={"x-lrt-token": "nie-te"}) as http:
        response = http.get(f"{API}/state")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_health_i_info_sa_bez_tokenu_ale_operacje_nie(app) -> None:
    """Health-check działa bez poświadczeń; każda operacja maszyny wymaga tokenu."""
    with TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,))) as http:
        assert http.get(f"{API}/health").status_code == 200
        assert http.get(f"{API}/info").status_code == 200
        for path in (f"{API}/state", f"{API}/contract", f"{API}/operations"):
            assert http.get(path).status_code == 403, path
        for command in ("machine.state", "machine.estop", "program.list"):
            denied = http.post(f"{API}/call", json={"command": command, "params": {}})
            assert denied.status_code == 403, command
        # Polecenie zatrzymujące też wymaga tokenu — brak wyjątków.
        assert http.post(f"{API}/call",
                         json={"command": "machine.estop", "params": {}}).status_code == 403


def test_dowolny_host_tylko_po_jawnym_opt_in(app) -> None:
    strict = TestClient(create_app(app, token="sekret", extra_hosts=(TEST_HOST,)))
    with strict:
        assert strict.get(f"{API}/health", headers={"host": "proxy.example"}).status_code == 403

    loose = TestClient(create_app(app, token="sekret", allow_any_host=True))
    with loose:
        assert loose.get(f"{API}/health", headers={"host": "proxy.example"}).status_code == 200
        # Opt-in dotyczy tylko Host — token nadal obowiązuje.
        assert loose.post(f"{API}/call", headers={"host": "proxy.example"},
                          json={"command": "machine.state", "params": {}}).status_code == 403


def test_obcy_host_jest_odrzucony(client) -> None:
    response = client.get(f"{API}/health", headers={"host": "zly.example.com"})
    assert response.status_code == 403
    assert "Host" in response.json()["error"]["message"]


def test_obcy_origin_jest_odrzucony(app) -> None:
    with TestClient(create_app(app, token="", extra_hosts=(TEST_HOST,),
                               allow_origins=("http://hmi.local",))) as http:
        response = http.get(f"{API}/health", headers={"origin": "http://obcy.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_ciagnienie_za_duzej_liczby_polecen_daje_429(client) -> None:
    codes = [client.post(f"{API}/call",
                         json={"command": "machine.state", "params": {}}).status_code
             for _ in range(200)]
    assert 429 in codes, "limiter poleceń powinien zadziałać"
    # Polecenie zatrzymujące przechodzi mimo wyczerpania tokenów.
    stop = client.post(f"{API}/call", json={"command": "machine.estop", "params": {}})
    assert stop.status_code == 200


def test_lista_operacji_jest_zgodna_z_kontraktem(client, app) -> None:
    listed = {o["name"] for o in client.get(f"{API}/operations").json()["operations"]}
    assert listed == {o.name for o in app.contract.operations()}
