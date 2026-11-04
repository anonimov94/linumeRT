# SPDX-License-Identifier: GPL-2.0-or-later
"""WebHMI z pinami HAL na LinuxCNC 2.9 + Plant: łańcuch HMI (D35) bez obejścia.

Model-Author: Claude · 2026-11-04. Sprawdza: start w E-STOP, pojedynczy Reset nie zwalnia,
podwójny Reset potwierdza zatrzask HAL i pozwala włączyć maszynę; milcząca przeglądarka
i zawieszona brama → E-STOP z ``watchdog`` HAL w ``[LINUMERT]HMI_HEARTBEAT_TIMEOUT``.
Kierowca: ``tests/webhmi_watchdog_driver.py``. NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from plant_session import run_generated_plant

ROOT = Path(__file__).resolve().parents[1]
MILL = ROOT / "config/machines/mill_servo_table.yaml"
POSTGUI = ROOT / "config/hal/linumert_webhmi_postgui.hal"
TIMEOUT_S = 2.0  # [LINUMERT]HMI_HEARTBEAT_TIMEOUT w wygenerowanej konfiguracji Plant
pytestmark = pytest.mark.linuxcnc


def _acknowledged(step: dict) -> None:
    assert step["single_reset"] == "ok"
    assert step["after_single"] == "estop", step  # pojedynczy Reset nie zwalnia E-STOP
    assert step["double_reset"] == "ok"
    assert step["to_estop_reset_s"] is not None, step
    assert step["power_on"] == "ok", step
    assert step["to_on_s"] is not None, step
    assert step["wd_ok"] == "TRUE" and step["hmi_chain"] == "TRUE", step


def test_webhmi_heartbeat_drives_hal_watchdog(tmp_path, monkeypatch):  # REQ-QA-03
    path = os.pathsep.join([str(ROOT / "core"), str(ROOT / "webhmi/server"),
                            os.environ.get("PYTHONPATH", "")])
    monkeypatch.setenv("PYTHONPATH", path)
    body = (ROOT / "tests/webhmi_watchdog_driver.py").read_text(encoding="utf-8")
    body = body.replace("@POSTGUI@", str(POSTGUI))
    r, log, cfg = run_generated_plant(tmp_path, MILL, body, port=47733, timeout=180,
                                      prelude="", hmi_bypass=False)
    ini = next(cfg.glob("*.ini")).read_text(encoding="utf-8")
    assert f"HMI_HEARTBEAT_TIMEOUT = {TIMEOUT_S}" in ini
    assert r["postgui_rc"] == 0, r["postgui_err"]
    assert r["start"] == {"task": "estop", "wd_ok": r["start"]["wd_ok"], "bypass": "FALSE",
                          "hmi_hal": True}, r
    _acknowledged(r["ack1"])
    # Milcząca karta: brama gasi sygnał po HEARTBEAT_S (1 s), watchdog po TIMEOUT_S.
    assert r["silent_to_estop_s"] is not None, r
    assert TIMEOUT_S + 0.8 <= r["silent_to_estop_s"] <= TIMEOUT_S + 2.5, r
    assert r["silent_wd_ok"] == "FALSE"
    _acknowledged(r["ack2"])  # po powrocie przeglądarki: znowu podwójny Reset
    # Zawieszona brama: E-STOP bez udziału bramy.
    assert r["frozen_task"] == 1, r  # linuxcnc.STATE_ESTOP
    assert r["frozen_to_estop_s"] <= TIMEOUT_S + 1.0, r
    assert r["frozen_wd_ok"] == "FALSE"
