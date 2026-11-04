# SPDX-License-Identifier: GPL-2.0-or-later
"""Bramka G2: scenariusz operatora WebHMI na LinuxCNC 2.9 + Plant (wygenerowana konfiguracja).

Model-Author: Claude · 2026-11-03. Kroki: włączenie po resecie E-STOP w HAL, bazowanie, JOG
(przyrost i deadman), zero detalu, wczytanie programu, AUTO, alarm i Reset. Kierowca:
``tests/g2_webhmi_driver.py``. Zrzuty z przeglądarki: ``docs/raporty/G2/G2_WEBHMI_2026-11-03.md``.
NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
pytestmark = pytest.mark.linuxcnc


def test_g2_operator_scenario_through_webhmi(tmp_path, monkeypatch):
    path = os.pathsep.join([str(ROOT / "core"), str(ROOT / "webhmi/server"),
                            os.environ.get("PYTHONPATH", "")])
    monkeypatch.setenv("PYTHONPATH", path)
    body = (ROOT / "tests/g2_webhmi_driver.py").read_text(encoding="utf-8")
    result, log, _ = run_generated_plant(tmp_path, MILL, body, port=47731, timeout=420,
                                         prelude="")
    steps = result["steps"]
    assert list(steps) == ["1_wlaczenie", "2_bazowanie", "3_jog", "4_zero_detalu",
                           "5_program", "6_auto", "7_alarm_reset"], (steps, log[-2000:])
    assert "E-STOP" in steps["1_wlaczenie"]["refused_in_estop"]
    assert steps["1_wlaczenie"]["task_state"] == "on"
    assert abs(steps["3_jog"]["increment_mm"] - 1.0) < 0.001
    assert steps["4_zero_detalu"]["work_offset"] == "G54"
    assert steps["5_program"]["program"].endswith("linumert_g2_odbior.ngc")
    assert steps["7_alarm_reset"]["task_state"] == "on"
