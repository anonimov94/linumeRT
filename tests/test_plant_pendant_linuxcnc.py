# SPDX-License-Identifier: GPL-2.0-or-later
"""Test Plant pendant inputs and wheel jogging on a simulated axis.

Model-Author: Codex
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from plant_session import DRIVER_PRELUDE, run_generated_plant

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
reader = hal.component("lrt-test-mpg-reader")
reader.ready()

if JOG:
    assert on and homed, "Cannot test wheel jog without power and homing"
    s.poll()
    assert s.motion_mode == linuxcnc.TRAJ_MODE_TELEOP
    def coordinates():
        s.poll()
        return tuple(s.actual_position[:3]), tuple(s.position[:3])

    def settled_at_home():
        actual, commanded = coordinates()
        return abs(s.current_vel) < 1e-4 and all(
            abs(a - c) < 0.001 for a, c in zip(actual, commanded, strict=True)
        )

    wait(settled_at_home, True, timeout=10)
    _, origin = coordinates()

    def at_displacement(y_mm):
        s.poll()
        expected = (origin[0], origin[1] + y_mm, origin[2])
        return all(abs(actual - target) < 0.001
                   for actual, target in zip(s.actual_position[:3], expected, strict=True))


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
    observed, travel = [], []
    for detents, expected, y_mm in ((100, 400, 1.0), (-100, 0, 0.0)):
        missed_before = hal.get_value("lrt-net.0.missed")
        post("mpg", {"detents": detents})
        wait(lambda: desk_state()["mpg_pending"], 0)
        assert desk_state()["mpg_edges"] == expected
        wait(lambda: pins(20, 21), (False, False))
        # Allow for the final Plant frame to reach LinuxCNC before sampling counts.
        try:
            observed.append(wait(counts, expected, timeout=2))
        except AssertionError as error:
            missed = hal.get_value("lrt-net.0.missed") - missed_before
            raise AssertionError(f"{error}; detents={detents}; missed cycles={missed}") from error

        if JOG:
            try:
                wait(lambda: at_displacement(y_mm), True, timeout=10)
            except AssertionError as error:
                actual, commanded = coordinates()
                pins_y = {name: hal.get_value("axis.y." + name) for name in (
                    "jog-enable", "jog-scale", "jog-counts", "wheel-jog-active",
                )}
                raise AssertionError(
                    f"Y delta={y_mm}, origin={origin}, actual={actual}, "
                    f"commanded={commanded}, task_state={s.task_state}, "
                    f"motion_mode={s.motion_mode}, HAL={pins_y}"
                ) from error
            travel.append(s.actual_position[1] - origin[1])

    assert hal.get_value("lrt-net.0.connected")
    print("RESULT " + json.dumps({"selected": selected, "counts": observed, "travel": travel}))
"""


def run_pendant(tmp_path, *, jog):
    example = yaml.safe_load((ROOT / "config/plant/plant.example.yaml").read_text(encoding="utf-8"))
    plant = tmp_path / "plant.yaml"
    desk = {**example["desk"], "mpg_ack": [20, 21]}
    plant.write_text(json.dumps({"machine": str(MILL), "desk": desk}), encoding="utf-8")

    # Private generated Plant configuration for the integration test.
    hal_setup = tmp_path / "mpg_test.hal"
    wiring = (
        "loadrt encoder names=lrt-test-mpg\n"
        "addf encoder.update-counters servo-thread\n"
        "addf encoder.capture-position servo-thread\n"
        "setp lrt-test-mpg.x4-mode true\n"
        "net lrt-test-mpg-a lrt-net.0.din-20 => lrt-test-mpg.phase-A lrt-net.0.dout-20\n"
        "net lrt-test-mpg-b lrt-net.0.din-21 => lrt-test-mpg.phase-B lrt-net.0.dout-21\n"
    )
    if jog:
        # Step 10 = 0.010 mm per detent, with four encoder counts per detent.
        wiring += (
            "net lrt-test-mpg-counts lrt-test-mpg.counts => axis.y.jog-counts\n"
            "net lrt-test-mpg-y lrt-net.0.din-23 => axis.y.jog-enable\n"
            "setp axis.y.jog-scale 0.0025\n"
        )
    hal_setup.write_text(wiring, encoding="utf-8")
    prelude = DRIVER_PRELUDE if jog else ""
    prelude += f"HAL_SETUP = {str(hal_setup)!r}\nPANEL_PORT = {PORT}\nJOG = {jog!r}\n"
    result, _, _ = run_generated_plant(
        tmp_path, MILL, DRIVER, port=PORT, timeout=360 if jog else 60,
        prelude=prelude, hmi_bypass=jog,
        plant_config=plant, plant_args=("--panel", str(PORT), "--state-dir", str(tmp_path)),
    )
    assert result["selected"] == [False, True, False, False, True, False]
    assert result["counts"] == [400, 0]
    return result["travel"]


@pytest.mark.linuxcnc
def test_plant_pendant_inputs_reach_linuxcnc(tmp_path):
    assert run_pendant(tmp_path, jog=False) == []


@pytest.mark.linuxcnc
def test_plant_pendant_jogs_simulated_axis_y(tmp_path):
    assert run_pendant(tmp_path, jog=True) == pytest.approx([1.0, 0.0], abs=0.001)
