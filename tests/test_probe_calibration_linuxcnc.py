# SPDX-License-Identifier: GPL-2.0-or-later
"""Kalibracja sondy na wzorcu, LinuxCNC + Plant (sesja 033).

Model-Author: Claude · 2026-10-25. Wzorzec = przygotówka w celu sondy Plant (`probe.target`),
której ściany są znane z `machine.yaml`. Kalibrujemy pięć par oś/kierunek w jednym miejscu
ściany, a poprawki sprawdzamy w innym miejscu tych samych ścian (przesunięcie stycznie o 20 mm).
Model napędów bez zmian.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from linumert.programs.probe_calibration import ProbeCalibration
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
FEED = 10.0
SHIFT = 20.0
TOL = 0.01                    # mm, kryterium sesji po kalibracji

DRIVER = r"""
mdi("G21 G90 G49 G54")
def probe(axis, sign, repeats):
    # szybki F100, odjazd 1 mm, dokładne przejazdy F10 (repeats razy)
    d = "" if sign > 0 else "-"
    back = "-" if sign > 0 else ""
    mdi("G91 G38.2 %s%s100 F100" % (axis, d))
    mdi("G91 G1 %s%s1 F300" % (axis, back))
    fine = []
    for _ in range(repeats):
        mdi("G91 G38.2 %s%s2 F10" % (axis, d))
        s.poll()
        assert s.probe_tripped, "sonda nie zadziałała"
        fine.append(s.probed_position["XYZ".index(axis)])
        mdi("G91 G1 %s%s1 F300" % (axis, back))
    mdi("G90")
    return fine
def go(x, y, z):
    mdi("G53 G0 Z-5"); mdi("G53 G0 X%.3f Y%.3f" % (x, y)); mdi("G53 G0 Z%.3f" % z)
def faces(t, repeats):
    # t = przesunięcie styczne względem miejsca kalibracji
    r = {}
    go(300 + t, 400 + t, -5);           r["Z-"] = probe("Z", -1, repeats)     # górna ściana
    go(200, 400 + t, -40);              r["X+"] = probe("X", +1, repeats)     # ściana X min
    go(400, 400 + t, -40);              r["X-"] = probe("X", -1, repeats)     # ściana X max
    go(300 + t, 300, -40);              r["Y+"] = probe("Y", +1, repeats)     # ściana Y min
    go(300 + t, 500, -40);              r["Y-"] = probe("Y", -1, repeats)     # ściana Y max
    return r
out = {"on": on, "homed": homed}
out["cal"] = faces(0, 2)
out["val"] = faces(@SHIFT@, 1)
mdi("G53 G0 Z-5")
out["estop"] = s.estop
print("RESULT " + json.dumps(out))
"""


# REQ-QA-02
@pytest.mark.linuxcnc
def test_probe_calibration_removes_systematic_error_on_plant(tmp_path):
    result, _, _ = run_generated_plant(tmp_path, MILL, DRIVER.replace("@SHIFT@", str(SHIFT)),
                                       port=47854, timeout=560)
    assert result["on"] and result["homed"] and not result["estop"], result
    target = yaml.safe_load(MILL.read_text(encoding="utf-8"))["probe"]
    lo, hi, tip = target["target"]["min"], target["target"]["max"], target["tip_length"]
    true = {"Z-": hi[2] + tip, "X+": lo[0], "X-": hi[0], "Y+": lo[1], "Y-": hi[1]}

    cal = ProbeCalibration(feed=FEED)
    for k, pos in true.items():
        cal.calibrate(k[0], +1 if k[1] == "+" else -1, result["cal"][k], pos)
    path = tmp_path / "probe_calibration.json"
    cal.save(path)
    cal = ProbeCalibration.load(path)                     # sprawdzamy to, co trafi na dysk

    report = {}
    for k, pos in true.items():
        direction = +1 if k[1] == "+" else -1
        raw = result["val"][k]
        fixed = [cal.apply(k[0], direction, v) for v in raw]
        report[k] = {"raw_error": [v - pos for v in raw],
                     "corrected_error": [v - pos for v in fixed],
                     "correction": cal.corrections[k]}
        assert all(abs(v - pos) <= TOL for v in fixed), (k, report[k])
    if os.environ.get("LINUMERT_PROBE_REPORT"):
        Path(os.environ["LINUMERT_PROBE_REPORT"]).write_text(json.dumps(report, indent=1))
