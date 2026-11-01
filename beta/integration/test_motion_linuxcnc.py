# SPDX-License-Identifier: GPL-2.0-or-later
"""Odbior API beta na LinuxCNC RIP + Plant; uruchamiaj pod wspolna blokada linuxcnc.

Model-Author: Codex. Korzysta z harnessu repozytorium; bez sprzetu i bez GUI.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

BETA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BETA.parent / "tests"))
import plant_session  # noqa: E402
import rip_support  # noqa: E402

DRIVER = r'''
from pathlib import Path
from linumert_headless.app import build_application
from linumert_headless.config import AppConfig
app = build_application(AppConfig(root=Path.cwd(), backend="linuxcnc", autostart=False))
out = {"on": on, "homed": homed}
def call(name, params):
    reply = app.call_json(name, params)
    cmd = app.backend._cmd()
    serial = cmd.serial
    assert wait(lambda: s.echo_serial_number >= serial, 10), name
    assert wait(idle, 180), name
    time.sleep(0.4)
    s.poll()
    return reply
assert on and homed
assert mdi("G21 G90 G49 G54 G10 L2 P1 X0 Y0 Z0 R0")
# Baza beta waliduje numer; tabela LinuxCNC zawiera rzeczywista korekcje Z80.
table = linuxcnc.ini(os.environ["INI_FILE_NAME"]).find("EMCIO", "TOOL_TABLE")
call("tool.import_tbl", {"text": Path(table).read_text()})
out["change"] = call("machine.tool_change", {"tool": 2, "confirm": True})
out["tool"] = [s.tool_in_spindle, s.tool_offset[2]]
out["remove"] = call("machine.tool_change", {"tool": 0, "confirm": True})
out["empty"] = [s.tool_in_spindle, s.tool_offset[2]]
assert mdi("G53 G0 Z-5")
assert mdi("G53 G0 X300 Y400")
out["probe_reply"] = call("offset.probe_run", {
    "axis": "Z", "direction": -1, "distance": 100, "feed": 100,
    "offset": "G54", "value": 5, "retract": 2, "confirm": True})
out["z"] = {"offset": s.g5x_offset[2], "probed": s.probed_position[2],
            "actual": s.actual_position[2], "tripped": s.probe_tripped,
            "gcodes": list(s.gcodes)}
# Dwa rzeczywiste pomiary wzorca, potem niezalezny przejazd po kalibracji.
measured = [out["z"]["probed"]]
assert mdi("G53 G0 Z-5")
assert mdi("G10 L2 P1 Z0")
call("offset.probe_run", {"axis": "Z", "direction": -1, "distance": 100,
     "feed": 100, "offset": "G54", "value": 5, "confirm": True})
measured.append(s.probed_position[2])
out["calibration"] = app.call_json("offset.probe_calibrate", {
    "axis": "Z", "direction": -1, "measured": measured, "true_value": @TOP@})
assert mdi("G53 G0 Z-5")
assert mdi("G10 L2 P1 Z0")
assert mdi("G91")
call("offset.probe_run", {"axis": "Z", "direction": -1, "distance": 100,
     "feed": 100, "offset": "G54", "value": 5, "confirm": True})
out["calibrated"] = {"offset": s.g5x_offset[2], "probed": s.probed_position[2],
                     "gcodes": list(s.gcodes), "samples": measured}
assert mdi("G90")
assert mdi("G53 G0 Z-5")
assert mdi("G53 G0 X100 Y100")
before = s.g5x_offset[2]
call("offset.probe_run", {"axis": "Z", "direction": -1, "distance": 1,
     "feed": 100, "offset": "G54", "value": 17, "confirm": True})
out["air"] = {"before": before, "after": s.g5x_offset[2],
              "tripped": s.probe_tripped, "errors": app.call_json("machine.state")["errors"]}
print("RESULT " + json.dumps(out))
'''


@pytest.mark.linuxcnc
@pytest.mark.timeout(420)
def test_beta_motion_macros_on_linuxcnc_plant(tmp_path, monkeypatch):
    monkeypatch.setattr(plant_session, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "ROOT", BETA)
    monkeypatch.setattr(rip_support, "HAL", BETA / "hal")
    # Doklejane do PYTHONPATH z rip-environment: bez niego kierowca nie ma modułu linuxcnc.
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(
        filter(None, [str(BETA / "src"), os.environ.get("PYTHONPATH", "")])))
    machine = BETA / "config/machines/mill_servo_table.yaml"
    probe = yaml.safe_load(machine.read_text())["probe"]
    top = probe["target"]["max"][2] + probe["tip_length"]
    driver = DRIVER.replace("@TOP@", repr(top))
    result, log, _ = plant_session.run_generated_plant(
        tmp_path, machine, driver,
        port=47857, timeout=300, copy_macros=False)
    if os.environ.get("LINUMERT_BETA_REPORT"):
        Path(os.environ["LINUMERT_BETA_REPORT"]).write_text(
            json.dumps(result, indent=2), encoding="utf-8")
    assert result["on"] and result["homed"], result
    assert result["tool"] == pytest.approx([2, 80], abs=1e-6), result
    assert result["empty"] == pytest.approx([0, 0], abs=1e-6), result
    z = result["z"]
    assert z["tripped"], result
    assert z["offset"] == pytest.approx(z["probed"] - 5, abs=1e-4), result
    assert z["actual"] == pytest.approx(z["probed"] + 2, abs=0.02), result
    assert 900 in z["gcodes"], result
    assert abs(result["calibrated"]["offset"] - (top - 5)) < 0.001, result
    assert 910 in result["calibrated"]["gcodes"], result
    assert not result["air"]["tripped"], result
    assert result["air"]["after"] == result["air"]["before"], result
    assert result["air"]["errors"], (result, log)
