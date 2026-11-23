# SPDX-License-Identifier: GPL-2.0-or-later
"""Przerwanie AUTO po awarii napędu i jawne odzyskanie na Plant."""

import os
from pathlib import Path

import pytest
from plant_session import DRIVER_PRELUDE, run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config/machines/mill_servo_table.yaml"
PORT = 47747

DRIVER = r"""
from pathlib import Path

import httpx
from linumert_webhmi import Gateway, create_app
from linumert_webhmi.backend import LinuxCNCBackend
from linumert_webhmi.hal_link import open_hal
from starlette.testclient import TestClient

assert on and homed, "Plant niegotowy"
host = "127.0.0.1:8765"
token = "local-test-drive-fault"
pins, component = open_hal(time.monotonic())
gateway = Gateway(LinuxCNCBackend(module=linuxcnc, programs_dir=Path.cwd()), hal_pins=pins)
gateway.start()

def state():
    return gateway.snapshot()[1]

def has_fault_alarm():
    return any(alarm["code"] == "E-4200" for alarm in state()["alarms"])

def exercise(ws, plant):
    request_id = 0

    def send(cmd, expected="ack", **args):
        nonlocal request_id
        request_id += 1
        ws.send_json({"id": request_id, "cmd": cmd, **args})
        while True:
            reply = ws.receive_json()
            if reply.get("id") == request_id:
                assert reply["type"] == expected, (cmd, reply)
                return reply

    assert wait(lambda: all(name in state()["programs"] for name in
                            ("fault-test.ngc", "recovery.ngc")), 10)
    send("open", name="fault-test.ngc")
    assert wait(lambda: state()["mode"] == "auto", 10)
    before = s.position[0]
    send("run")
    assert wait(lambda: s.current_vel > 0.1 and s.position[0] > before + 0.1, 30)
    plant.post("/api/faults/drive_fault", json={"drive": "drv_x"}).raise_for_status()
    assert wait(lambda: state()["drive_fault_axes"] == ["X"] and has_fault_alarm(), 15)
    assert wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE and
                abs(s.current_vel) < 1e-4, 30), state()
    stopped = s.position[0]
    assert stopped < before + 80
    for command in ("resume", "run"):
        reply = send(command, expected="error")
        assert "Aktywna awaria napędu: X" in reply["message"], reply
    send("reset")
    assert has_fault_alarm(), state()

    plant.post("/api/faults/drive_fault/clear", json={"drive": "drv_x"}).raise_for_status()
    if state()["task_state"] == "on":
        send("power_off")
    assert wait(lambda: state()["task_state"] in ("off", "estop_reset"), 15), state()
    send("power_on")
    assert wait(lambda: s.task_state == linuxcnc.STATE_ON and
                state()["drive_fault_axes"] == [], 20), state()
    send("reset")
    assert wait(lambda: not has_fault_alarm(), 5)
    s.poll()
    recovery_start = s.position[0]
    assert abs(recovery_start - stopped) < 0.1 and idle(), "Reset nie uruchamia programu"
    send("open", name="recovery.ngc")
    send("run")
    assert wait(lambda: abs(s.position[0] - (recovery_start + 1)) < 1e-4 and idle(),
                30), state()
    return {"travel_before_stop": stopped - before, "recovered": True}

try:
    Path("fault-test.ngc").write_text("G21 G91 G1 X80 F300\nM2\n", encoding="ascii")
    Path("recovery.ngc").write_text("G21 G91 G1 X1 F120\nM2\n", encoding="ascii")
    with httpx.Client(base_url=f"http://127.0.0.1:{PANEL_PORT}", trust_env=False) as plant:
        with TestClient(create_app(gateway, token), base_url=f"http://{host}") as client:
            with client.websocket_connect("/ws", headers={"host": host}) as ws:
                ws.send_json({"auth": token})
                assert ws.receive_json()["type"] == "state"
                result = exercise(ws, plant)
finally:
    gateway.stop()
print("RESULT " + json.dumps(result), flush=True)
"""


@pytest.mark.linuxcnc
def test_webhmi_drive_fault_blocks_auto_until_recovery_on_plant(tmp_path, monkeypatch):
    path = os.pathsep.join((str(ROOT / "core"), str(ROOT / "webhmi/server"),
                            os.environ.get("PYTHONPATH", "")))
    monkeypatch.setenv("PYTHONPATH", path)
    result, _, _ = run_generated_plant(
        tmp_path, MACHINE, DRIVER, port=PORT, timeout=420,
        prelude=DRIVER_PRELUDE + f"\nPANEL_PORT = {PORT}\n",
        plant_args=("--panel", str(PORT), "--state-dir", str(tmp_path)),
    )
    assert 0.1 < result["travel_before_stop"] < 80
    assert result["recovered"]
