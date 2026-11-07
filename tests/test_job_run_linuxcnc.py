"""Actual bound Start/pause/resume and interruptions on private LinuxCNC + Plant.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex. Verification is a constructed contract fixture; not offline proof.
"""

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest
import rip_support as rip
from test_job_instance import configuration as configuration
from test_job_instance import package as package
from websockets.sync.client import connect

pytestmark = pytest.mark.linuxcnc
TERMINAL = {"completed_observed", "aborted", "estop", "fault", "start_timeout",
            "resume_timeout", "settle_timeout", "unavailable", "client_lost"}


class Operator:
    """Authenticated real HTTP commands and a drained live WebSocket, no HAL bypass."""

    def __init__(self, record):
        self.port, self.token = record["port"], record["token"]
        self.alive = threading.Event()
        self.alive.set()
        self.stop = threading.Event()
        self.opened = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self.browser, daemon=True)
        self.thread.start()
        assert self.opened.wait(5) and self.error is None, self.error

    def browser(self):
        try:
            with connect(f"ws://127.0.0.1:{self.port}/ws", open_timeout=3, close_timeout=1) as ws:
                ws.send(json.dumps({"auth": self.token}))
                assert json.loads(ws.recv(timeout=3))["type"] == "state"
                self.opened.set()
                while not self.stop.is_set():
                    if self.alive.is_set():
                        ws.send('{"alive":1}')
                    try:
                        ws.recv(timeout=.1)
                    except TimeoutError:
                        pass
                    self.stop.wait(.05)
        except Exception as error:  # noqa: BLE001 - surface worker failures to the test
            self.error = repr(error)
            self.opened.set()

    def request(self, path, data=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/{path}",
            data=json.dumps(data).encode() if data is not None else None,
            headers={"X-Linumert-Token": self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)

    def command(self, cmd, **kwargs):
        assert self.request("command", {"cmd": cmd, **kwargs})["ok"]

    def wait(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        state = None
        while time.monotonic() < deadline:
            assert self.error is None, self.error
            state = self.request("state")["state"]
            if predicate(state):
                return state
            time.sleep(.03)
        pytest.fail(f"Condition not observed: {state}")

    def ready(self):
        self.wait(lambda s: s["task_state"] == "estop" and not s["all_homed"]
                  and s["execution"]["checks"]["controller"]["status"] == "passed"
                  and s["heartbeat"])
        self.command("reset", double=True)
        self.wait(lambda s: s["task_state"] in ("off", "estop_reset"))
        self.command("power_on")
        self.wait(lambda s: s["task_state"] == "on"
                  and s["execution"]["checks"]["hal"]["status"] == "passed")
        self.command("home")
        self.wait(lambda s: s["all_homed"], timeout=90)
        self.command("mode", mode="mdi")
        self.wait(lambda s: s["mode"] == "mdi")
        self.command("mdi", text="G49 G90 G53 G0 Z-5")
        self.wait(lambda s: s["interp_state"] == "idle"
                  and abs(s["axes"][2]["position"] + 5) < .001)
        self.command("mdi", text="G90 G53 G0 X200 Y200")
        self.wait(lambda s: s["interp_state"] == "idle"
                  and all(abs(a["position"] - 200) < .001 for a in s["axes"][:2]), timeout=30)
        self.command("open", name="program.ngc")
        self.command("mode", mode="auto")
        self.wait(lambda s: s["execution"]["can_start"])

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive()


@pytest.mark.parametrize("outcome", ["aborted", "estop", "client_lost"])
def test_bound_job_pause_resume_and_distinct_interruptions(configuration, tmp_path, outcome):
    root = rip.rip_root()
    if rip.leftovers():
        pytest.skip("another LinuxCNC process is active")
    work = tmp_path / "instance"
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}"}
    operator = None
    with rip.installed_modules(root, tmp_path, ("lrt_net", "lrt_cia402", "lrt_estop2")):
        with (tmp_path / "host.log").open("w") as log:
            host = subprocess.Popen([sys.executable, "-m", "linumert_webhmi.job_instance",
                str(configuration), "--out", str(work), "--port", "8795"],
                env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    assert host.poll() is None, (tmp_path / "host.log").read_text()
                    try:
                        record = json.loads((work / "instance.json").read_text())
                        probe = urllib.request.Request("http://127.0.0.1:8795/api/state",
                            headers={"X-Linumert-Token": record["token"]})
                        with urllib.request.urlopen(probe, timeout=1) as response:
                            json.load(response)
                        operator = Operator(record)
                        break
                    except (OSError, ValueError):
                        time.sleep(.1)
                assert operator is not None
                operator.ready()
                operator.command("run")
                operator.wait(lambda s: s["execution"]["run"]["phase"] == "running"
                              and s["execution"]["run"]["elapsed_s"] > 4)
                operator.command("pause")
                paused = operator.wait(lambda s: s["execution"]["can_resume"])
                assert paused["tool"] == 1 and not paused["execution"]["can_start"]
                operator.command("resume")
                operator.wait(lambda s: s["execution"]["run"]["phase"] == "running")
                if outcome == "client_lost":
                    operator.alive.clear()  # keep socket open, emulate a stalled browser
                else:
                    operator.command("stop" if outcome == "aborted" else "estop")
                state = operator.wait(lambda s: s["execution"]["run"]["phase"] in TERMINAL)
                assert state["execution"]["run"]["phase"] == outcome, state
                result = json.loads(next((work / "runs").glob("*/result.json")).read_text())
                assert result["status"] == outcome and result["job_id"] == record["job_id"]
                assert result["samples"] > 3 and result["last_line"] > 0
                assert not result["servo_trace"] and result["source"] == "linuxcnc.stat"
                assert result["settled_position_observed"] == (outcome == "aborted")
                assert not state["execution"]["can_resume"]
                saved = urllib.request.Request("http://127.0.0.1:8795/api/execution/report",
                    headers={"X-Linumert-Token": record["token"]})
                with urllib.request.urlopen(saved, timeout=10) as response:
                    report = json.load(response)
                assert report["run_id"] == result["run_id"]
                assert report["execution_status"] == outcome
                assert report["joint_following_error"]["status"] == "available"
                assert len(report["joint_following_error"]["joints"]) == 4
            finally:
                try:
                    if operator:
                        operator.close()
                finally:
                    host.terminate()
                    host.wait(timeout=45)
        assert not rip.leftovers(), rip.leftovers()
