"""CLI i SDK: te same operacje co REST, bez drugiej ścieżki walidacji.

SPDX-License-Identifier: GPL-2.0-or-later

CLI jest generowane z kontraktu, więc test sprawdza i parser, i wykonanie operacji
w trybie lokalnym. SDK testujemy na żywym serwerze (uvicorn w wątku), bo klient mówi
przez HTTP — dokładnie tak, jak będzie mówić GUI.
"""

from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from linumert_headless.transport.cli import build_parser, main

# --------------------------------------------------------------------------- CLI


def test_cli_parser_powstaje_z_kontraktu(app) -> None:
    parser = build_parser(app.contract)
    text = parser.format_usage()
    assert "linumertctl" in text
    # Każda operacja kontraktu jest podpoleceniem — nowa funkcja jest od razu w CLI.
    choices = set(parser._subparsers._group_actions[0].choices)
    assert {"machine.state", "program.list", "system.info"} <= choices
    assert len(choices) >= len(app.contract.operations())


def test_cli_wypisuje_stan_maszyny(capsys, workdir) -> None:
    code = main(["--backend", "fake", "--root", str(workdir), "machine.state"])
    assert code == 0
    out = capsys.readouterr().out
    assert "backend: fake" in out
    assert "task_state:" in out


def test_cli_json_i_kontrakt_do_pliku(capsys, tmp_path, workdir) -> None:
    target = tmp_path / "api" / "contract.json"
    code = main(["--root", str(workdir), "contract", "--out", str(target)])
    assert code == 0
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["operations"]
    assert capsys.readouterr().out.startswith("zapisano kontrakt")


def test_cli_flagi_globalne_dzialaja_przed_podkomenda_i_po_niej(app, workdir) -> None:
    """``linumertctl operations --json`` musi działać — tak podaje dokumentacja.

    argparse nie przepuszcza flag parsera głównego za nazwę podpolecenia, więc przy
    flagach tylko na parserze głównym forma z README/API padała z kodem 2 (błąd
    użycia), a działała wyłącznie ``linumertctl --json operations``. Oba poziomy
    dostają ten sam zestaw argumentów, a ``SUPPRESS`` jako domyślna pilnuje, żeby
    podparser nie skasował wartości podanej przed nazwą podpolecenia.
    """
    parser = build_parser(app.contract)
    przed = parser.parse_args(["--json", "operations"])
    po = parser.parse_args(["operations", "--json"])
    assert przed.json is po.json is True, "obie pozycje muszą dawać ten sam wynik"

    # wartość podana z przodu nie może być nadpisana pustą domyślną z podparsera
    args = parser.parse_args(["--url", "http://x:8080", "machine.state"])
    assert args.url == "http://x:8080"
    args = parser.parse_args(["machine.state", "--url", "http://x:8080"])
    assert args.url == "http://x:8080"
    args = parser.parse_args(["--root", "/tmp/a", "machine.state", "--url", "http://x:8080"])
    assert (args.root, args.url) == ("/tmp/a", "http://x:8080")

    # domyślne nadal obowiązują, gdy flagi nie podano wcale
    args = parser.parse_args(["machine.state"])
    assert (args.url, args.backend, args.json) == ("", "fake", False)


def test_cli_operations_z_json_po_podkomendzie(capsys, workdir) -> None:
    """Dokładna forma z dokumentacji, wykonana end-to-end (nie tylko sparsowana)."""
    code = main(["--root", str(workdir), "operations", "--json"])
    assert code == 0, "forma z README.md i API.md musi działać"
    payload = json.loads(capsys.readouterr().out)
    assert payload["operations"] and payload["domains"]


def test_cli_blad_operacji_daje_kod_1_i_komunikat(capsys, workdir) -> None:
    code = main(["--root", str(workdir), "program.read", "name=nie_ma.ngc"])
    assert code == 1
    err = capsys.readouterr().err
    assert "not_found" in err


def test_cli_parametr_bez_znaku_rownosci_daje_kod_2(capsys, workdir) -> None:
    code = main(["--root", str(workdir), "program.read", "nazwa"])
    assert code == 2
    assert "bez '='" in capsys.readouterr().err


def test_cli_lista_operacji(capsys, workdir) -> None:
    assert main(["--root", str(workdir), "operations"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["domains"]
    assert {o["name"] for o in payload["operations"]}


# --------------------------------------------------------------------------- SDK


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def server(app):
    """Żywy serwer uvicorn w wątku — SDK mówi do niego przez HTTP."""
    uvicorn = pytest.importorskip("uvicorn")
    from linumert_headless.transport.rest import create_app

    port = _free_port()
    config = uvicorn.Config(create_app(app, token="sdk-token"), host="127.0.0.1",
                            port=port, log_level="error")
    instance = uvicorn.Server(config)
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and not instance.started:
        time.sleep(0.05)
    assert instance.started, "serwer nie wystartował"
    yield f"http://127.0.0.1:{port}"
    instance.should_exit = True
    thread.join(timeout=5.0)


def test_sdk_domeny_powstaja_z_kontraktu(server) -> None:
    from linumert_headless.sdk import Client

    client = Client(server, token="sdk-token")
    operations = client.operations()
    assert operations
    assert callable(client.machine.state)
    assert callable(client.program.list)
    assert "Bazuj" in client.machine.home.__doc__


def test_sdk_wywoluje_operacje_przez_http(server) -> None:
    from linumert_headless.sdk import Client

    client = Client(server, token="sdk-token")
    assert client.info()["gui"] is False
    assert client.health()["backend"] == "fake"
    state = client.machine.state()
    assert [axis["name"] for axis in state["axes"]] == ["X", "Y", "Z"]
    assert client.call("system.info")["application"]


def test_sdk_blad_serwera_ma_kod_z_kontraktu(server) -> None:
    from linumert_headless.sdk import Client, RemoteError

    client = Client(server, token="sdk-token")
    with pytest.raises(RemoteError) as excinfo:
        client.program.read(name="nie_ma.ngc")
    assert excinfo.value.code == "not_found"


def test_sdk_bez_tokenu_dostaje_403(server) -> None:
    from linumert_headless.sdk import Client, RemoteError

    client = Client(server, token="")
    # health/info są otwarte (health-check), więc sprawdzamy na chronionej operacji
    assert client.health()["backend"] == "fake"
    with pytest.raises(RemoteError) as excinfo:
        client.machine.state()
    assert excinfo.value.code == "permission_denied"


def test_sdk_brak_domeny_spoza_kontraktu(server) -> None:
    from linumert_headless.sdk import Client

    client = Client(server, token="sdk-token")
    with pytest.raises(AttributeError) as excinfo:
        client.nie_ma_takiej_domeny  # noqa: B018 - celowy dostęp do nieistniejącej domeny
    assert "brak domeny" in str(excinfo.value)


def test_sdk_subskrypcja_stanu(server) -> None:
    """GUI dostaje push stanu przez WebSocket — pierwsza wiadomość to pełna migawka."""
    pytest.importorskip("websockets")
    from linumert_headless.sdk import Client

    client = Client(server, token="sdk-token")
    stream = client.subscribe(topics=("machine",))
    first = next(stream)
    assert first["version"] >= 0
    assert "machine" in first["topics"]
