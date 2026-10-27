# SPDX-License-Identifier: GPL-2.0-or-later
"""Real LinuxCNC WebHMI acceptance, isolated from pytest. Model-Author: Codex."""

import json
import sys
import time
from pathlib import Path

import linuxcnc
from linumert_webhmi import Gateway, create_app
from linumert_webhmi.backend import LinuxCNCBackend
from starlette.testclient import TestClient


def run(output):
    control, status = linuxcnc.command(), linuxcnc.stat()

    def wait(predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status.poll()
            if predicate():
                return
            time.sleep(0.02)
        raise AssertionError({"position": list(status.actual_position),
                              "mode": status.task_mode, "state": status.task_state})

    def x():
        status.poll()
        return status.actual_position[0]

    # Fixture-only reset. There is deliberately no corresponding web command.
    control.state(linuxcnc.STATE_ESTOP_RESET)
    wait(lambda: status.task_state == linuxcnc.STATE_ESTOP_RESET)
    control.state(linuxcnc.STATE_ON)
    wait(lambda: status.task_state == linuxcnc.STATE_ON)
    control.mode(linuxcnc.MODE_MANUAL)
    assert control.wait_complete(5) == linuxcnc.RCS_DONE
    control.home(-1)
    wait(lambda: all(status.homed[:3]), 120)
    control.mode(linuxcnc.MODE_MDI)
    assert control.wait_complete(5) == linuxcnc.RCS_DONE
    control.mdi("G21 G90 G53 G1 X100 Y100 Z-10 F3000")
    assert control.wait_complete(30) == linuxcnc.RCS_DONE
    wait(lambda: status.interp_state == linuxcnc.INTERP_IDLE and status.inpos)
    control.mode(linuxcnc.MODE_MANUAL)
    assert control.wait_complete(5) == linuxcnc.RCS_DONE

    gateway = Gateway(LinuxCNCBackend(module=linuxcnc))
    token = "webhmi-live-acceptance-token"
    report = {}
    command_id = 0

    def command(ws, payload, expected="ack"):
        nonlocal command_id
        command_id += 1
        ws.send_json({"id": command_id, **payload})
        while True:
            response = ws.receive_json()
            if response.get("id") == command_id:
                assert response["type"] == expected, response
                return response

    def connect(ws):
        ws.send_json({"auth": token})
        first = ws.receive_json()
        assert first["type"] == "state", first
        return first["state"]

    gateway.start()
    try:
        with TestClient(create_app(gateway, token), base_url="http://127.0.0.1:8765") as client:
            with client.websocket_connect("/ws", headers={"host": "127.0.0.1:8765"}) as ws:
                initial = connect(ws)
                axis = next(a for a in initial["axes"] if a["name"] == "X")
                assert abs(axis["position"] - x()) <= 0.001, (axis, x())
                report["dro_x"] = axis["position"]
                start = x()
                command(ws, {"cmd": "jog_increment", "axis": "X", "speed": 5,
                             "distance": 1})
                wait(lambda: abs(x() - start - 1) < 0.001 and status.inpos)
                report["increment_mm"] = x() - start
                time.sleep(0.15)
                assert abs(x() - start - 1) < 0.001, "increment repeated without another click"
                command(ws, {"cmd": "jog_stop"})
                command(ws, {"cmd": "mode", "mode": "mdi"})
                command(ws, {"cmd": "jog_increment", "axis": "X", "speed": 5,
                             "distance": 1}, expected="error")
                assert abs(x() - start - 1) < 0.001, "wrong-mode jog moved the axis"
                report["wrong_mode_rejected"] = True
                command(ws, {"cmd": "mode", "mode": "manual"})
                start = x()
                command(ws, {"cmd": "jog_increment", "axis": "X", "speed": 0.5,
                             "distance": 1})
                # No jog_keepalive: a 2 s increment must stop after the 0.4 s lease.
                wait(lambda: not gateway.snapshot()[1]["jog_active"])
                wait(lambda: bool(status.joint[0]["inpos"]))
                stopped = x()
                assert 0.05 < stopped - start < 0.5, (start, stopped)
                time.sleep(0.15)
                assert abs(x() - stopped) < 0.001, "expired increment continued"
                report["increment_deadman_mm"] = stopped - start
                start = x()
                command(ws, {"cmd": "jog", "axis": "X", "speed": 5})
                wait(lambda: x() > start + 0.1)
            # Server must cancel the owner's continuous motion when its WS closes.
            wait(lambda: not gateway.snapshot()[1]["jog_active"])
            wait(lambda: bool(status.joint[0]["inpos"]))
            stopped = x()
            time.sleep(0.2)
            assert abs(x() - stopped) < 0.001, "jog continued after disconnect"
            report["disconnect_stop_mm"] = stopped
            assert gateway.snapshot()[1]["jog_stop_pending"] == []
    finally:
        gateway.stop()
        control.abort()
    Path(output).write_text(json.dumps(report, indent=2) + "\n")
    print("WEBHMI_LIVE_PASS " + json.dumps(report))


if __name__ == "__main__":
    run(sys.argv[1])
