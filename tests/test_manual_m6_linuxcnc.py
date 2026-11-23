# SPDX-License-Identifier: GPL-2.0-or-later
"""Sesja 034/G2: ręczna zmiana M6 przez WebSocket na LinuxCNC i Plant."""

import os
from pathlib import Path

import pytest
from plant_session import run_generated_plant

MACHINE = Path(__file__).resolve().parents[1] / "config/machines/mill_servo_table.yaml"

DRIVER = r"""
import subprocess
from pathlib import Path

from linumert_webhmi import Gateway, create_app
from linumert_webhmi.backend import LinuxCNCBackend
from linumert_webhmi.hal_link import open_hal, wire_manual_toolchange
from starlette.testclient import TestClient

TOKEN = "local-test-manual-toolchange"
REQUEST = "iocontrol.0.tool-change"
ACK = "iocontrol.0.tool-changed"
NUMBER = "iocontrol.0.tool-prep-number"

def pin(name):
    return subprocess.check_output(["halcmd", "getp", name], text=True).strip()

def pending(ws):
    ws.send_json({"alive": 1})
    return gateway.snapshot()[1].get("manual_m6")

def send(ws, cmd, request_id, expected="ack"):
    ws.send_json({"id": 1, "cmd": cmd, "tool_request_id": request_id})
    while True:
        reply = ws.receive_json()
        if reply.get("id") == 1:
            assert reply["type"] == expected, reply
            return

def run_to_request(ws, tool, mounted, offset):
    program = Path.cwd() / f"manual-m6-t{tool}.ngc"
    program.write_text(f"T{tool} M6\nG43 H{tool}\nM2\n", encoding="ascii")
    c.program_open(str(program))
    c.wait_complete()
    c.auto(linuxcnc.AUTO_RUN, 0)
    assert wait(lambda: pending(ws) is not None, 30), f"Brak żądania M6 dla T{tool}"
    until = time.monotonic() + 0.5
    while time.monotonic() < until:
        s.poll()
        assert pin(REQUEST) == "TRUE" and pin(ACK) == "FALSE"
        request = pending(ws)
        assert request is not None and request["tool"] == int(pin(NUMBER)) == tool
        assert s.interp_state != linuxcnc.INTERP_IDLE
        assert s.tool_in_spindle == mounted and abs(s.tool_offset[2] - offset) < 1e-6
        time.sleep(0.02)
    return request["id"]

def confirm(ws, request_id, tool, offset):
    send(ws, "tool_confirm", request_id)
    assert wait(lambda: pin(REQUEST) == "FALSE", 15), f"M6 T{tool} nie zwolniło żądania"
    assert wait(idle, 30), f"Program T{tool} nie zakończył się po potwierdzeniu"
    assert s.tool_in_spindle == tool and abs(s.tool_offset[2] - offset) < 1e-6

assert on and homed, "Plant niegotowy"
pins, component = open_hal(time.monotonic(), manual_toolchange=True)
wire_manual_toolchange()
gateway = Gateway(LinuxCNCBackend(module=linuxcnc), hal_pins=pins)
gateway.start()
try:
    assert pin(REQUEST) == pin(ACK) == "FALSE"
    c.mode(linuxcnc.MODE_AUTO)
    c.wait_complete()
    s.poll()
    assert s.tool_in_spindle == 0
    host = "127.0.0.1:8765"
    with TestClient(create_app(gateway, TOKEN), base_url=f"http://{host}") as client:
        with client.websocket_connect("/ws", headers={"host": host}) as ws:
            ws.send_json({"auth": TOKEN})
            assert ws.receive_json()["type"] == "state"

            first = run_to_request(ws, 1, 0, 0.0)
            confirm(ws, first, 1, 75.0)

            cancelled = run_to_request(ws, 2, 1, 75.0)
            send(ws, "tool_cancel", cancelled)
            assert wait(lambda: pin(REQUEST) == "FALSE" and
                        s.interp_state == linuxcnc.INTERP_IDLE, 30)
            assert pin(ACK) == "FALSE" and s.tool_in_spindle == 1
            assert abs(s.tool_offset[2] - 75.0) < 1e-6
            assert wait(lambda: any(row["code"] == "W-2130"
                                    for row in gateway.snapshot()[1]["alarms"]), 5)
            after_abort = s.tool_in_spindle

            retried = run_to_request(ws, 2, 1, 75.0)
            assert retried != cancelled
            send(ws, "tool_confirm", cancelled, expected="error")
            assert pin(REQUEST) == "TRUE" and pin(ACK) == "FALSE"
            confirm(ws, retried, 2, 80.0)
finally:
    gateway.stop()
print("RESULT " + json.dumps({"after_abort": after_abort, "tool": s.tool_in_spindle,
                              "offset_z": s.tool_offset[2]}), flush=True)
"""


@pytest.mark.linuxcnc
def test_manual_m6_waits_for_confirmation_and_can_be_cancelled_on_plant(tmp_path, monkeypatch):
    root = MACHINE.parents[2]
    path = os.pathsep.join((str(root / "core"), str(root / "webhmi/server"),
                            os.environ.get("PYTHONPATH", "")))
    monkeypatch.setenv("PYTHONPATH", path)
    result, _, _ = run_generated_plant(tmp_path, MACHINE, DRIVER, port=47746, timeout=420)
    assert result["after_abort"] == 1
    assert result["tool"] == 2
    assert result["offset_z"] == pytest.approx(80.0, abs=1e-6)
