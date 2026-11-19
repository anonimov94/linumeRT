# SPDX-License-Identifier: GPL-2.0-or-later
"""Test the virtual pendant input path before binding it to axis jog.

Model-Author: Codex
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
PORT = 47742

DRIVER = r"""
import json
import subprocess
import time

import hal
import httpx


def wait(read, expected, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        observed = read()
        if observed == expected:
            return observed
        if time.monotonic() >= deadline:
            raise AssertionError(f"Expected {expected!r}, got {observed!r}")
        time.sleep(0.02)


def pins(*channels):
    return tuple(hal.get_value(f"lrt-net.0.din-{channel:02d}") for channel in channels)


def counts():
    return hal.get_value("lrt-test-mpg.counts")


subprocess.run(["halcmd", "-f", HAL_SETUP], check=True)

with httpx.Client(base_url=f"http://127.0.0.1:{PANEL_PORT}", trust_env=False, timeout=3) as client:
    def post(path, body):
        return client.post("/api/desk/" + path, json=body).raise_for_status().json()

    def desk_state():
        return client.get("/api/state").raise_for_status().json()["desk"]

    wait(lambda: hal.get_value("lrt-net.0.connected"), True)
    wait(lambda: pins(22, 23, 24, 25, 26, 27), (True, False, False, True, False, False))
    post("axis", {"axis": "Y"})
    post("step", {"step": 10})
    selected = wait(lambda: pins(22, 23, 24, 25, 26, 27),
                    (False, True, False, False, True, False))

    assert counts() == desk_state()["mpg_edges"] == 0
    observed = []
    for detents, expected in ((100, 400), (-100, 0)):
        post("mpg", {"detents": detents})
        wait(lambda: desk_state()["mpg_pending"], 0)
        assert desk_state()["mpg_edges"] == expected
        wait(lambda: pins(20, 21), (False, False))
        observed.append(wait(counts, expected))

    assert hal.get_value("lrt-net.0.connected")
    print("RESULT " + json.dumps({"selected": selected, "counts": observed}))
"""


@pytest.mark.linuxcnc
def test_plant_pendant_inputs_reach_linuxcnc(tmp_path):
    example = yaml.safe_load((ROOT / "config/plant/plant.example.yaml").read_text(encoding="utf-8"))
    plant = tmp_path / "plant.yaml"
    plant.write_text(json.dumps({"machine": str(MILL), "desk": example["desk"]}), encoding="utf-8")

    # Install only the decoder for this test. There is no connection to motion pins.
    hal_setup = tmp_path / "mpg_test.hal"
    hal_setup.write_text(
        "loadrt encoder names=lrt-test-mpg\n"
        "addf encoder.update-counters servo-thread\n"
        "addf encoder.capture-position servo-thread\n"
        "setp lrt-test-mpg.x4-mode true\n"
        "net lrt-test-mpg-a lrt-net.0.din-20 => lrt-test-mpg.phase-A\n"
        "net lrt-test-mpg-b lrt-net.0.din-21 => lrt-test-mpg.phase-B\n",
        encoding="utf-8",
    )
    prelude = f"HAL_SETUP = {str(hal_setup)!r}\nPANEL_PORT = {PORT}\n"
    result, _, _ = run_generated_plant(
        tmp_path, MILL, DRIVER, port=PORT, timeout=60, prelude=prelude, hmi_bypass=False,
        plant_config=plant, plant_args=("--panel", str(PORT), "--state-dir", str(tmp_path)),
    )
    assert result == {
        "selected": [False, True, False, False, True, False],
        "counts": [400, 0],
    }
