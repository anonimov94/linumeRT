# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
"""Console replay must reflect measured Plant telemetry and scenario outcomes."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from console_demo import main  # noqa: E402


@pytest.mark.parametrize("scenario,alarm", [("first_motion", "ALARMY: brak"),
                                           ("estop_mid_program", "E-1100")])
def test_console_replays_real_plant_and_expected_stop(scenario, alarm, capsys):
    from linumert_plant.core_binding import PlantCoreUnavailable, load_library

    try:
        load_library()
    except PlantCoreUnavailable as exc:
        pytest.skip(str(exc))
    assert main(["--scenario", scenario, "--plain"]) == 0
    output = capsys.readouterr().out
    assert "ODTWARZANIE" in output and "drv_x" in output
    assert "@" in output and "WYNIK SCENARIUSZA: PASS" in output
    assert alarm in output and "\033[" not in output


def test_alarm_replay_accounts_for_drive_boot_time():
    from console_demo import frame
    from linumert_plant.core_binding import PlantCoreUnavailable, load_library
    from linumert_plant.scenario import load_scenario, run_mock

    try:
        load_library()
    except PlantCoreUnavailable as exc:
        pytest.skip(str(exc))
    result = run_mock(load_scenario(ROOT / "plant/scenarios/estop_mid_program.yaml"))
    # The model already passed 1 s during drive boot; the E-STOP is still in the future.
    index = next(i for i, stamp in enumerate(result.telemetry["t"]) if stamp >= 1.1)
    before = frame(result, index)
    assert "E-1100" not in before
    assert "E-1100" in frame(result, len(result.telemetry["t"]) - 1)
