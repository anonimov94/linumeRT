# SPDX-License-Identifier: GPL-2.0-or-later
"""D38: histereza dotrzymania pozycji napędów przed wycofaniem Z. Model-Author: Claude."""

import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(not importlib.util.find_spec("PyQt5"),
                                reason="PyQt5 niedostępne")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screens" / "linumert"))


def test_settled_has_hysteresis_against_standstill_noise():
    from linumert_pause_retract import RetractControl

    control = SimpleNamespace(_settled=False, native=1.0)
    check = RetractControl.settled_now.__get__(control)
    joints = lambda *fe: [{"ferror_current": v} for v in fe]  # noqa: E731
    assert not check(joints(0.0, 0.007))         # 7 µm: jeszcze nie dotrzymane
    assert check(joints(0.001, 0.004))           # wejście ≤ 5 µm
    assert check(joints(0.001, -0.008))          # szum do 10 µm nie przełącza stanu
    assert not check(joints(0.0, 0.011))         # wyjście > 10 µm
    assert not check(joints(0.0, 0.007))         # po wyjściu znów próg 5 µm
    assert not check(joints(float("nan")))
    inch = SimpleNamespace(_settled=False, native=1 / 25.4)
    assert RetractControl.settled_now.__get__(inch)(joints(0.004 / 25.4))
