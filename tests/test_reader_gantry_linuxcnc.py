# SPDX-License-Identifier: GPL-2.0-or-later
"""Czytnik i brama web na portalu: LinuxCNC 2.9 RIP + Plant, mill_servo_table (jointy X Y Y Z).

Model-Author: Claude. Odbiór błędu z bety: oś Z czytała joint 2 (Y2), więc niezbazowany Z dawał
``all_homed``, a ``home("Z")`` bazował Y2. Marker `linuxcnc`. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from plant_session import run_generated_plant

pytestmark = pytest.mark.linuxcnc

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config/machines/mill_servo_table.yaml"

DRIVER = rf'''
sys.path[:0] = [{str(ROOT / "core")!r}, {str(ROOT / "webhmi/server")!r}]
from linumert.cnc import Mode
from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert_webhmi.backend import LinuxCNCBackend

reader = LinuxCNCReader()
backend = LinuxCNCBackend(reader=reader)
def state():
    x = backend.snapshot()
    return {{"homed": {{a.name: a.homed for a in x.axes}}, "all": x.all_homed}}
def settled():
    quiet = [0]
    def still():
        ok = abs(s.current_vel) < 1e-4 and s.inpos
        quiet[0] = quiet[0] + 1 if ok else 0
        return quiet[0] >= 15
    return wait(still, 60)

out = {{"on": on, "prelude_homed": homed, "joints": s.joints}}
out["all_homed"] = state()
out["map"] = {{k: list(v) for k, v in reader.joint_map(["X", "Y", "Z"]).items()}}

backend.set_mode(Mode.MANUAL)
c.teleop_enable(0); c.wait_complete()
c.unhome(3); c.wait_complete()
out["z_unhomed_stat"] = wait(lambda: not s.homed[3] and s.homed[2], 10)
out["z_unhomed"] = state()

try:
    backend.jog("Y", 5.0)
except Exception as error:
    out["y_jog_unhomed"] = str(error)

backend.home("Z")
out["home_z_stat"] = wait(lambda: s.homed[3] and s.homed[2], 120)
settled()
out["home_z"] = state()

s.poll()
start = list(s.position[:3]), list(s.joint_actual_position[:4])
backend.jog_increment("Y", 5.0, 1.0)
wait(lambda: abs(s.position[1] - start[0][1]) > 0.5, 30)
settled()
out["jog_axes"] = [round(b - a, 3) for a, b in zip(start[0], s.position[:3])]
out["jog_joints"] = [round(b - a, 2) for a, b in zip(start[1], s.joint_actual_position[:4])]
print("RESULT " + json.dumps(out))
'''


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("gantry")
    return run_generated_plant(tmp, MACHINE, DRIVER, port=48787)[0]


def test_map_comes_from_real_ini(result):
    assert result["on"] and result["prelude_homed"] and result["joints"] == 4
    assert result["map"] == {"X": [0], "Y": [1, 2], "Z": [3]}
    assert result["all_homed"] == {"homed": {"X": True, "Y": True, "Z": True}, "all": True}


def test_unhomed_z_is_visible_and_blocks_all_homed(result):
    assert result["z_unhomed_stat"], result
    assert result["z_unhomed"] == {"homed": {"X": True, "Y": True, "Z": False}, "all": False}


def test_gantry_y_jog_before_full_homing_is_refused(result):
    assert "bazowania" in result["y_jog_unhomed"]


def test_webhmi_home_z_homes_joint_3_and_y_jog_moves_both_joints(result):
    assert result["home_z_stat"], result
    assert result["home_z"]["all"]
    assert result["jog_axes"] == pytest.approx([0.0, 1.0, 0.0], abs=0.01)
    assert result["jog_joints"] == pytest.approx([0.0, 1.0, 1.0, 0.0], abs=0.15)
