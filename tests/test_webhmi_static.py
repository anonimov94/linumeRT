"""Static Cyberdeck client smoke tests.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT
"""

from pathlib import Path

from linumert.cnc import FakeMachine
from linumert_webhmi import FakeBackend, Gateway, create_app
from starlette.testclient import TestClient

TOKEN = "test-token-for-webhmi-static"
STATIC = Path(__file__).resolve().parents[1] / "webhmi/server/linumert_webhmi/static"


def test_static_files_served_by_create_app():
    gateway = Gateway(FakeBackend(FakeMachine()))
    client = TestClient(create_app(gateway, TOKEN), base_url="http://127.0.0.1:8765")
    for path in ("index.html", "app.js", "style.css"):
        response = client.get("/" if path == "index.html" else "/" + path)
        assert response.status_code == 200, path
        assert response.content, path


def test_static_client_has_no_external_urls():
    for path in ("index.html", "app.js", "style.css"):
        content = (STATIC / path).read_text(encoding="utf-8")
        assert "http://" not in content, path
        assert "https://" not in content, path
        assert "SPDX-License-Identifier: GPL-2.0-or-later" in content, path
        assert "Model-Author: ChatGPT" in content, path
