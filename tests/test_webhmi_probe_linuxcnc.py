# SPDX-License-Identifier: GPL-2.0-or-later
"""Sonda w WebHMI na LinuxCNC 2.9 + Plant: polecenie ``probe`` bramy → ``o<lrt_probe>``.

Model-Author: Claude · 2026-11-05. Brama dostaje to samo polecenie co przycisk „Sonduj”
w przeglądarce; makro z #204 wykonuje G38.2, G10 L20 w aktywnym układzie i odjazd.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
ABS_TOL = 0.02  # [mm] jak test makra (#204): luz modelu napędu 0,01 + sprężystość
VALUE = 5.0  # współrzędna górnej ściany celu w G54 po sondowaniu
pytestmark = pytest.mark.linuxcnc

DRIVER = r"""
from linumert_webhmi import Command, Gateway
from linumert_webhmi.backend import LinuxCNCBackend
out = {"on": on, "homed": homed}
mdi("G21 G90 G94 G49 G54 G10 L2 P1 X0 Y0 Z0 R0")
mdi("G53 G0 Z-5")
mdi("G53 G0 X300 Y400")
gateway = Gateway(LinuxCNCBackend(module=linuxcnc))
for _ in range(5):
    gateway.step()
    time.sleep(0.05)
gateway.execute(Command(cmd="probe", axis="Z", direction=-1, probe_distance=100,
                        probe_value=@VALUE@))
started = wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 10)
quiet = [0]
def settled():
    still = abs(s.current_vel) < 1e-4 and idle()
    quiet[0] = quiet[0] + 1 if still else 0
    return quiet[0] >= 15
done = wait(settled, 180)
gateway.step()
s.poll()
out["probe"] = {"started": started, "done": done, "tripped": s.probe_tripped,
                "offset": list(s.g5x_offset[:3]), "probed": list(s.probed_position[:3]),
                "actual": list(s.actual_position[:3]), "task": s.task_state,
                "alarms": [a["code"] for a in gateway.snapshot()[1]["alarms"]]}
print("RESULT " + json.dumps(out), flush=True)
"""


def test_webhmi_probe_sets_work_offset_on_plant(tmp_path, monkeypatch):  # REQ-QA-02
    path = os.pathsep.join([str(ROOT / "core"), str(ROOT / "webhmi/server"),
                            os.environ.get("PYTHONPATH", "")])
    monkeypatch.setenv("PYTHONPATH", path)
    result, log, _ = run_generated_plant(tmp_path, MILL, DRIVER.replace("@VALUE@", str(VALUE)),
                                         port=47855, timeout=300)
    assert result["on"] and result["homed"], result
    probe = yaml.safe_load(MILL.read_text(encoding="utf-8"))["probe"]
    top_z = probe["target"]["max"][2] + probe["tip_length"]  # Z wrzeciona przy styku
    r = result["probe"]
    assert r["started"] and r["done"] and r["tripped"], (r, log[-2000:])
    assert r["offset"][2] == pytest.approx(top_z - VALUE, abs=ABS_TOL), r
    assert r["offset"][2] == pytest.approx(r["probed"][2] - VALUE, abs=1e-4), r
    assert r["actual"][2] == pytest.approx(r["probed"][2] + 2.0, abs=ABS_TOL), r  # odjazd 2 mm
    assert r["task"] == 4 and r["alarms"] == [], r  # STATE_ON, bez alarmów
