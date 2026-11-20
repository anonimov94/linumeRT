# SPDX-License-Identifier: GPL-2.0-or-later
"""Test Plant pendant inputs and wheel jogging on the simulated XYZ axes.

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
AXES = "XYZ"
STEPS_UM = (1, 10, 100)

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

    def settled():
        actual, commanded = coordinates()
        return abs(s.current_vel) < 1e-4 and all(
            abs(a - c) < 0.001 for a, c in zip(actual, commanded, strict=True)
        )

    def at_target(target):
        actual, commanded = coordinates()
        return (s.task_state == linuxcnc.STATE_ON
                and s.motion_mode == linuxcnc.TRAJ_MODE_TELEOP
                # The planner settles within its finite position resolution.
                # Keep the command tolerance smaller than one count at the finest scale.
                and all(abs(a - t) < 0.001 and abs(c - t) < 0.0001
                        for a, c, t in zip(actual, commanded, target, strict=True)))


with httpx.Client(base_url=f"http://127.0.0.1:{PANEL_PORT}", trust_env=False, timeout=3) as client:
    def post(path, body):
        return client.post("/api/desk/" + path, json=body).raise_for_status().json()

    def desk_state():
        return client.get("/api/state").raise_for_status().json()["desk"]

    wait(lambda: hal.get_value("lrt-net.0.connected"), True)
    wait(lambda: pins(22, 23, 24, 25, 26, 27), (True, False, False, True, False, False))
    def select(axis, step):
        post("axis", {"axis": axis})
        post("step", {"step": step})
        return wait(lambda: pins(22, 23, 24, 25, 26, 27),
                    tuple(axis == candidate for candidate in AXES)
                    + tuple(step == candidate for candidate in STEPS_UM))

    def turn(detents, expected):
        missed_before = hal.get_value("lrt-net.0.missed")
        post("mpg", {"detents": detents})
        wait(lambda: desk_state()["mpg_pending"], 0)
        assert desk_state()["mpg_edges"] == expected
        wait(lambda: pins(20, 21), (False, False))
        try:
            return wait(counts, expected, timeout=2)
        except AssertionError as error:
            missed = hal.get_value("lrt-net.0.missed") - missed_before
            raise AssertionError(f"{error}; detents={detents}; missed cycles={missed}") from error

    assert counts() == desk_state()["mpg_edges"] == 0
    if JOG:
        travel = []
        for axis_index, axis in enumerate(AXES):
            for step in STEPS_UM:
                select(axis, step)
                axis_pin = "axis." + axis.lower() + "."
                wait(lambda: hal.get_value(axis_pin + "jog-scale"), step / 4000)
                wait(settled, True)
                _, origin = coordinates()
                detents = -100 if axis == "Z" else 100
                distance = detents * step / 1000
                moved = list(origin)
                moved[axis_index] += distance
                samples = []
                for requested, expected, target in ((detents, 4 * detents, moved),
                                                     (-detents, 0, origin)):
                    turn(requested, expected)
                    try:
                        wait(lambda: at_target(target), True)
                    except AssertionError as error:
                        actual, commanded = coordinates()
                        jog_pins = {name: hal.get_value(axis_pin + name) for name in (
                            "jog-enable", "jog-scale", "jog-counts", "wheel-jog-active",
                        )}
                        raise AssertionError(
                            f"{axis} step={step}, target={target}, actual={actual}, "
                            f"commanded={commanded}, task_state={s.task_state}, "
                            f"motion_mode={s.motion_mode}, HAL={jog_pins}"
                        ) from error
                    samples.append([a - b for a, b in zip(s.actual_position[:3], origin,
                                                         strict=True)])
                travel.append({"axis": axis, "step": step, "samples": samples})
        result = {"travel": travel}
    else:
        result = {"selected": select("Y", 10), "counts": [turn(100, 400), turn(-100, 0)]}

    assert hal.get_value("lrt-net.0.connected")
    print("RESULT " + json.dumps(result))
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
        axis_pins = tuple(f"axis.{axis.lower()}" for axis in AXES)
        scale_pins = " ".join(pin + ".jog-scale" for pin in axis_pins)
        count_pins = " ".join(pin + ".jog-counts" for pin in axis_pins)
        wiring += (
            "loadrt mux4 names=lrt-test-mpg-scale\n"
            "addf lrt-test-mpg-scale servo-thread\n"
            "net lrt-test-mpg-step-10 lrt-net.0.din-26 => lrt-test-mpg-scale.sel0\n"
            "net lrt-test-mpg-step-100 lrt-net.0.din-27 => lrt-test-mpg-scale.sel1\n"
            f"net lrt-test-mpg-distance lrt-test-mpg-scale.out => {scale_pins}\n"
            f"net lrt-test-mpg-counts lrt-test-mpg.counts => {count_pins}\n"
        )
        for index, step in enumerate(STEPS_UM):
            # A detent contains four encoder counts. HAL uses machine units (mm).
            wiring += f"setp lrt-test-mpg-scale.in{index} {step / 4000}\n"
        for axis, pin in zip(AXES, axis_pins, strict=True):
            wiring += f"net lrt-test-mpg-{axis.lower()} lrt-net.0.din-{desk['axis'][axis]:02d}"
            wiring += f" => {pin}.jog-enable\n"
    hal_setup.write_text(wiring, encoding="utf-8")
    prelude = DRIVER_PRELUDE if jog else ""
    prelude += (f"HAL_SETUP = {str(hal_setup)!r}\nPANEL_PORT = {PORT}\nJOG = {jog!r}\n"
                f"AXES = {AXES!r}\nSTEPS_UM = {STEPS_UM!r}\n")
    result, _, _ = run_generated_plant(
        tmp_path, MILL, DRIVER, port=PORT, timeout=360 if jog else 60,
        prelude=prelude, hmi_bypass=jog,
        plant_config=plant, plant_args=("--panel", str(PORT), "--state-dir", str(tmp_path)),
    )
    return result


@pytest.mark.linuxcnc
def test_plant_pendant_inputs_reach_linuxcnc(tmp_path):
    assert run_pendant(tmp_path, jog=False) == {
        "selected": [False, True, False, False, True, False],
        "counts": [400, 0],
    }


@pytest.mark.linuxcnc
def test_plant_pendant_jogs_simulated_xyz_at_each_scale(tmp_path):
    travel = run_pendant(tmp_path, jog=True)["travel"]
    assert [(entry["axis"], entry["step"]) for entry in travel] == [
        (axis, step) for axis in AXES for step in STEPS_UM
    ]
    for entry in travel:
        moved = [0.0] * len(AXES)
        direction = -1 if entry["axis"] == "Z" else 1
        moved[AXES.index(entry["axis"])] = direction * entry["step"] / 10
        assert entry["samples"][0] == pytest.approx(moved, abs=0.001)
        assert entry["samples"][1] == pytest.approx([0.0] * len(AXES), abs=0.001)
