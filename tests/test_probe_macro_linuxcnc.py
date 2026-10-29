# SPDX-License-Identifier: GPL-2.0-or-later
"""Makro sondowania ``o<lrt_probe>`` na LinuxCNC + Plant (wygenerowany).

Model-Author: Claude · 2026-10-28. Jedno wywołanie MDI: G38.2, zapis offsetu G10 L20 w punkcie
styku i odjazd. Sprawdzamy offset G54 zapisany przez makro na celu sondy z ``machine.yaml``
(górna ściana Z i ściana X min), przywrócenie trybu G90/G91 oraz to, że wynik nie zależy od
hamowania za punktem styku (G10 L20 liczy względem ``#5061…#5063``). Wymaga LinuxCNC RIP
(marker ``linuxcnc``). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from linumert.programs.probe_macro import PROBE_MACRO, probe_call
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
ABS_TOL = 0.02   # [mm] jak test 033: luz modelu napędu 0,01 + sprężystość
Z_VALUE = 5.0    # współrzędna górnej ściany w G54 po sondowaniu
X_VALUE = -3.0   # współrzędna ściany X min w G54 po sondowaniu
RETRACT = 2.0

DRIVER = r"""
out = {"on": on, "homed": homed}
mdi("G21 G90 G49 G54 G10 L2 P1 X0 Y0 Z0 R0")
mdi("G53 G0 Z-5")
mdi("G53 G0 X300 Y400")
mdi("@CALL_Z@", timeout=180)
s.poll()
out["z"] = {"offset": list(s.g5x_offset[:3]), "tripped": s.probe_tripped,
            "probed": list(s.probed_position[:3]), "actual": list(s.actual_position[:3]),
            "gcodes": [g for g in s.gcodes if g > 0]}
mdi("G53 G0 Z-5")
mdi("G53 G0 X200 Y400")
mdi("G53 G0 Z-40")
mdi("G91")                                   # makro ma przywrócić G91 wywołującego
mdi("@CALL_X@", timeout=180)
s.poll()
out["x"] = {"offset": list(s.g5x_offset[:3]), "tripped": s.probe_tripped,
            "probed": list(s.probed_position[:3]), "actual": list(s.actual_position[:3]),
            "gcodes": [g for g in s.gcodes if g > 0]}
mdi("G90")
mdi("G53 G0 Z-5")
# Ponowne sondowanie Z przy aktywnym, niezerowym offsecie G54: wynik nie może się zmienić.
mdi("G53 G0 X300 Y400")
mdi("@CALL_Z@", timeout=180)
s.poll()
out["z2"] = {"offset": list(s.g5x_offset[:3]), "tripped": s.probe_tripped}
# P=2 przy aktywnym G54: offset trafia do G55, aktywny układ się nie zmienia.
mdi("G53 G0 Z-5")
mdi("@CALL_Z55@", timeout=180)
s.poll()
out["active_after_p2"] = s.g5x_index
mdi("G55")
s.poll()
out["g55"] = list(s.g5x_offset[:3])
mdi("G54")
mdi("G53 G0 Z-5")
# Zly argument (kierunek 2): makro odmawia przed ruchem, offset i pozycja bez zmian.
s.poll()
before_off, before_pos = list(s.g5x_offset[:3]), list(s.actual_position[:3])
ech = linuxcnc.error_channel()
mdi("o<lrt_probe> call [2] [2] [10] [100] [1] [0] [2]", timeout=30)
s.poll()
errors = []
for _ in range(5):
    err = ech.poll()
    if err:
        errors.append(str(err[1]))
out["bad_arg_errors"] = errors
out["bad_arg"] = {"offset_same": before_off == list(s.g5x_offset[:3]),
                  "moved": max(abs(a - b) for a, b in zip(before_pos, s.actual_position[:3]))}
out["estop"] = s.estop
print("RESULT " + json.dumps(out))
"""


def test_macro_file_matches_core() -> None:
    for path in ("config/sim/linumert_xyz/macros/lrt_probe.ngc",
                 "config/plant/linumert_plant_xyz/macros/lrt_probe.ngc"):
        assert (ROOT / path).read_text(encoding="utf-8") == PROBE_MACRO, path


# REQ-QA-02
@pytest.mark.linuxcnc
def test_lrt_probe_sets_work_offset_on_plant(tmp_path) -> None:
    call_z = probe_call("Z", -1, 100, 100, "G54", Z_VALUE, RETRACT)
    call_x = probe_call("X", 1, 100, 100, "G54", X_VALUE, RETRACT)
    call_z55 = probe_call("Z", -1, 100, 100, "G55", Z_VALUE, RETRACT)
    driver = (DRIVER.replace("@CALL_Z55@", call_z55).replace("@CALL_Z@", call_z)
              .replace("@CALL_X@", call_x))
    result, _, _ = run_generated_plant(tmp_path, MILL, driver, port=47853)
    assert result["on"] and result["homed"] and not result["estop"], result

    probe = yaml.safe_load(MILL.read_text(encoding="utf-8"))["probe"]
    top_z = probe["target"]["max"][2] + probe["tip_length"]   # Z wrzeciona przy styku: -30
    wall_x = probe["target"]["min"][0]                       # ściana X min: 250

    z, x = result["z"], result["x"]
    if os.environ.get("LINUMERT_PROBE_REPORT"):
        Path(os.environ["LINUMERT_PROBE_REPORT"]).write_text(json.dumps(
            {"calls": [call_z, call_x], "expected_offset": {"z": top_z - Z_VALUE,
                                                            "x": wall_x - X_VALUE},
             "z": z, "x": x}, indent=1))
    assert z["tripped"] and x["tripped"], result
    # Punkt styku dostał zadaną wartość: offset = pozycja styku - wartość.
    assert z["offset"][2] == pytest.approx(top_z - Z_VALUE, abs=ABS_TOL), z
    assert x["offset"][0] == pytest.approx(wall_x - X_VALUE, abs=ABS_TOL), x
    # Offset liczony z punktu styku (#5063), nie z pozycji po hamowaniu: zgodny z probed.
    assert z["offset"][2] == pytest.approx(z["probed"][2] - Z_VALUE, abs=1e-4), z
    assert x["offset"][0] == pytest.approx(x["probed"][0] - X_VALUE, abs=1e-4), x
    # Odjazd od powierzchni o RETRACT w kierunku przeciwnym do sondowania.
    assert z["actual"][2] == pytest.approx(z["probed"][2] + RETRACT, abs=ABS_TOL), z
    assert x["actual"][0] == pytest.approx(x["probed"][0] - RETRACT, abs=ABS_TOL), x
    # Tryb odległości wywołującego przywrócony (G90 = 900, G91 = 910 w stat.gcodes).
    assert 900 in z["gcodes"] and 910 not in z["gcodes"], z
    assert 910 in x["gcodes"] and 900 not in x["gcodes"], x
    # #5061…#5063 są w układzie aktywnym (jak #<_x>): sondowanie przy offsecie −35 daje to samo.
    assert result["z2"]["tripped"], result
    assert result["z2"]["offset"][2] == pytest.approx(z["offset"][2], abs=0.01), result
    # P=2 przy aktywnym G54: G55 dostaje offset, aktywny układ zostaje G54 (index 1).
    assert result["active_after_p2"] == 1, result
    assert result["g55"][2] == pytest.approx(top_z - Z_VALUE, abs=ABS_TOL), result
    # Odmowa to komunikat interpretera (abort), nie E-STOP: maszyna zostaje włączona.
    assert any("kierunek" in e for e in result["bad_arg_errors"]), result
    assert result["bad_arg"]["offset_same"] and result["bad_arg"]["moved"] < 1e-3, result
    # Drugie sondowanie nie zmieniło Z zapisanego przez pierwsze.
    assert x["offset"][2] == pytest.approx(z["offset"][2], abs=1e-6), (z, x)
