"""Static WebHMI, ES modules and interlock regression smoke tests.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from linumert.cnc import FakeMachine
from linumert_webhmi import FakeBackend, Gateway, create_app
from linumert_webhmi.app import KEEPALIVE_S
from starlette.testclient import TestClient

TOKEN = "test-token-for-webhmi-static"
ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "webhmi/server/linumert_webhmi/static"
MODULES = ("connection.js", "interlocks.js", "jog.js", "dro.js", "scene.js", "main.js",
           "events.js", "log.js")
FILES = ("index.html", "app.js", "style.css", *(f"js/{name}" for name in MODULES),
         "js/package.json")


def test_static_files_served_by_create_app():
    gateway = Gateway(FakeBackend(FakeMachine()))
    client = TestClient(create_app(gateway, TOKEN), base_url="http://127.0.0.1:8765")
    for name in FILES:
        path = "/" if name == "index.html" else "/" + name
        response = client.get(path)
        assert response.status_code == 200, name
        assert response.content, name
    assert "type=\"module\"" in client.get("/").text


def test_static_client_is_local_and_has_license_headers():
    for name in FILES:
        content = (STATIC / name).read_text(encoding="utf-8")
        assert "http://" not in content, name
        assert "https://" not in content, name
        if name.endswith((".js", ".html", ".css")):
            assert "SPDX-License-Identifier: GPL-2.0-or-later" in content, name
            assert "Model-Author: ChatGPT" in content, name


def test_e2e_selectors_still_exist():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for selector in ('id="token"', 'id="connect"', 'id="axisRows"', 'id="jogSpeed"',
                     'id="commandResult"', 'class="status-tag offline"',
                     'data-cmd="estop"', 'data-cmd="stop"', 'data-mode="manual"'):
        assert selector in html, selector
    js = (STATIC / "js/jog.js").read_text(encoding="utf-8")
    assert 'node.className = "jog-button"' in js
    assert "INTERVAL_MS = 150" in js
    for selector in ('id="eventLog"', 'id="logFilter"', 'id="logExport"',
                     'id="logClear"', 'id="lamps"', 'id="stateRate"',
                     'id="stateAge"', 'id="ackLatency"', 'id="jogStatus"'):
        assert selector in html, selector
    assert '<th title="Błąd nadążania">FERR</th>' in html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js nie jest zainstalowany")
def test_node_interlocks():
    subprocess.run(
        ["node", "--test", str(ROOT / "tests/webhmi_js/test_interlocks.mjs")],
        cwd=ROOT, check=True, timeout=40,
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js nie jest zainstalowany")
def test_node_check_all_modules():
    for name in ("app.js", *[f"js/{module}" for module in MODULES]):
        subprocess.run(["node", "--check", str(STATIC / name)], check=True, timeout=15)


def test_js_dom_selector_is_module_local():
    """Każdy moduł używający $(...) deklaruje lub importuje selektor we własnym scope."""
    for path in sorted((STATIC / "js").glob("*.js")):
        source = path.read_text(encoding="utf-8")
        if re.search(r"(?<![\w$])\$\s*\(", source):
            assert re.search(
                r"\b(?:const|let|var)\s+\$\s*=|\bimport\s+(?:\$|\{[^}]*\$)",
                source,
            ), path.name


def test_ws_keepalive_leaves_margin_for_dro_freshness():
    """Dwa okresy keepalive muszą zmieścić się w progu 500 ms po stronie JS."""
    assert KEEPALIVE_S * 2 < 0.5


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js nie jest zainstalowany")
def test_node_events():
    subprocess.run(
        ["node", "--test", str(ROOT / "tests/webhmi_js/test_events.mjs")],
        cwd=ROOT, check=True, timeout=40,
    )


def test_ferr_schema_and_threshold():
    from linumert_webhmi.schema import snapshot_to_dict

    result = snapshot_to_dict(FakeMachine().snapshot())
    assert all("following_error" in axis for axis in result["axes"])
    source = (STATIC / "js/dro.js").read_text(encoding="utf-8")
    assert "FERR_WARN_MM = 0.05" in source
    assert "axis.following_error" in source
