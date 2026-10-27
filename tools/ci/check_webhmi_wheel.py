"""Check the WebHMI shipped in a wheel, outside the source checkout.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

SMOKE = r'''
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))

import linumert_webhmi
from linumert.cnc import FakeMachine, Mode
from linumert_webhmi import FakeBackend, Gateway, create_app
from starlette.testclient import TestClient

assert Path(linumert_webhmi.__file__).resolve().is_relative_to(root)
machine = FakeMachine()
machine.estop_reset()
machine.power_on()
machine.home()
machine.run_until_idle()
machine.set_mode(Mode.MANUAL)
gateway = Gateway(FakeBackend(machine))
token = "wheel-smoke-test-token"
with TestClient(create_app(gateway, token), base_url="http://127.0.0.1:8765") as client:
    for asset in ("index.html", "app.js", "style.css"):
        response = client.get("/" if asset == "index.html" else "/" + asset)
        assert response.status_code == 200, (asset, response.status_code)
        expected = root / "linumert_webhmi" / "static" / asset
        assert response.content == expected.read_bytes(), asset
    with client.websocket_connect("/ws", headers={"host": "127.0.0.1:8765"}) as ws:
        ws.send_json({"auth": token})
        state = ws.receive_json()
        assert state["type"] == "state" and state["state"]["schema"] == 1
        ws.send_json({"id": 1, "cmd": "jog", "axis": "X", "speed": 1})
        while True:
            reply = ws.receive_json()
            if reply["type"] in ("ack", "error"):
                assert reply == {"type": "ack", "id": 1}, reply
                break
        assert machine._jog
    assert not machine._jog, "disconnect must stop jogging"
print("WebHMI wheel: static assets, authentication, jog and disconnect PASS")
'''


def main() -> None:
    wheel = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="linumert-webhmi-wheel-") as directory:
        with ZipFile(wheel) as archive:
            archive.extractall(directory)
        subprocess.run([sys.executable, "-I", "-c", SMOKE, directory],
                       cwd=directory, check=True, timeout=30)


if __name__ == "__main__":
    main()
