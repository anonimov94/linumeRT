# SPDX-License-Identifier: GPL-2.0-or-later
"""Wygenerowana konfiguracja Plant uruchomiona bezpośrednio w LinuxCNC (sesja 062, odbiór).

Model-Author: Claude · 2026-10-25. `linumert-config build --target plant` → LinuxCNC RIP + serwer
Plant (lockstep, localhost, `lrt_net`) → włączenie, bazowanie wszystkich osi na wirtualnych
czujnikach i ruch MDI. Wcześniej wynik sprawdzano tylko przez równość z ręczną konfiguracją.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"

DRIVER = r"""
home_pos = [round(v, 3) for v in s.joint_actual_position[:s.joints]]
mdi("G21 G90 G53 G1 X50 F1200", 60)
s.poll()
print("RESULT " + json.dumps({"on": on, "homed": homed, "joints": s.joints, "home": home_pos,
      "moved": abs(s.actual_position[0] - 50) < 0.05, "x": round(s.actual_position[0], 3),
      "estop": s.estop}))
"""


# REQ-VM-01
@pytest.mark.linuxcnc
def test_generated_plant_config_runs_homes_and_moves_in_linuxcnc(tmp_path):
    result, _, _ = run_generated_plant(tmp_path, MILL, DRIVER, port=47851)
    assert result["on"] and result["homed"], result
    assert result["moved"] and result["x"] == pytest.approx(50, abs=0.05), result
    assert not result["estop"], result
