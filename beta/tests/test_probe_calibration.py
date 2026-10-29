# SPDX-License-Identifier: GPL-2.0-or-later
"""Kalibracja sondy na wzorcu (sesja 033). Model-Author: Claude · 2026-10-25."""

import json

import pytest

from linumert.programs.probe_calibration import CalibrationError, ProbeCalibration


def test_calibrate_apply_and_roundtrip(tmp_path):
    cal = ProbeCalibration(feed=10.0)
    assert cal.calibrate("Z", -1, [-30.0109, -30.0109], -30.0) == pytest.approx(0.0109)
    assert cal.calibrate("x", 1, [250.0158, 250.0159], 250.0) == pytest.approx(-0.01585)
    assert cal.apply("Z", -1, -40.0109) == pytest.approx(-40.0)
    assert cal.apply("X", 1, 300.0158) == pytest.approx(299.99995, abs=1e-4)
    path = tmp_path / "probe_cal.json"
    cal.save(path)
    again = ProbeCalibration.load(path)
    assert again.corrections == cal.corrections and again.feed == 10.0
    assert not list(tmp_path.glob("*.tmp"))


def test_direction_axis_and_feed_are_not_mixed():
    cal = ProbeCalibration(feed=10.0)
    cal.calibrate("X", 1, [250.0158], 250.0)
    with pytest.raises(CalibrationError, match="brak kalibracji"):
        cal.apply("X", -1, 350.0)          # inny kierunek wymaga własnej poprawki
    with pytest.raises(CalibrationError, match="brak kalibracji"):
        cal.apply("Y", 1, 350.0)
    with pytest.raises(CalibrationError, match="posuwu"):
        cal.check_feed(100.0)
    cal.check_feed(10.0)


@pytest.mark.parametrize(("measured", "true", "message"), [
    ([], 0.0, "brak odczytów"),
    ([1.0, 1.02], 1.0, "rozrzut"),
    ([5.0], 5.5, "poza"),
    ([float("nan")], 0.0, "skończonej"),
    ([1.0], float("inf"), "skończonej"),
])
def test_bad_calibration_is_refused(measured, true, message):
    cal = ProbeCalibration(feed=10.0)
    with pytest.raises(CalibrationError, match=message):
        cal.calibrate("Z", -1, measured, true)
    assert cal.corrections == {}


@pytest.mark.parametrize("args", [("Q", 1), ("XY", 1), ("X", 0), ("X", 2)])
def test_invalid_key_is_refused(args):
    with pytest.raises(CalibrationError):
        ProbeCalibration(feed=1.0).calibrate(*args, [0.0], 0.0)


@pytest.mark.parametrize("text", [
    "nie json", "[]", json.dumps({"version": 2, "units": "mm", "feed": 1, "corrections": {},
                                  "spread": {}}),
    json.dumps({"version": 1, "units": "in", "feed": 1, "corrections": {}, "spread": {}}),
    json.dumps({"version": 1, "units": "mm", "feed": 1, "corrections": {"X?": 0.0},
                "spread": {}}),
    json.dumps({"version": 1, "units": "mm", "feed": 1, "corrections": {"X+": 9.0},
                "spread": {}}),
    json.dumps({"version": 1, "units": "mm", "feed": 1, "corrections": {}, "spread": {},
                "x": 1}),
])
def test_corrupted_file_is_refused(text):
    with pytest.raises(CalibrationError):
        ProbeCalibration.from_json(text)
