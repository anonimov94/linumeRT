"""Dwukanałowy E-STOP NC (model logiki `hal/lrt_estop2.comp`). Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

from linumert.diag.estop2 import Estop2

DT = 0.001


def _run(e, a, b, reset=False, seconds=0.01):
    for _ in range(round(seconds / DT)):
        e.step(a, b, reset, DT)
    return e


def test_both_closed_is_ok_and_short_difference_tolerated():
    e = _run(Estop2(), True, True)
    assert e.ok and not e.fault
    _run(e, True, False, seconds=0.05)  # przełączanie styków: różnica < 0,1 s
    assert not e.ok and not e.fault  # kanał otwarty = brak zezwolenia, ale bez błędu
    _run(e, True, True)
    assert e.ok


def test_pressing_mushroom_opens_both_without_fault():
    e = _run(Estop2(), True, True)
    _run(e, False, False, seconds=0.5)
    assert not e.ok and not e.fault
    assert _run(e, True, True).ok


def test_discrepancy_latches_and_needs_circuit_test():
    e = _run(Estop2(), True, True)
    _run(e, True, False, seconds=0.2)
    assert e.fault and not e.ok
    _run(e, True, True)
    _run(e, True, True, reset=True)
    assert e.fault, "reset bez testu obwodu nie kasuje błędu"
    _run(e, True, True, reset=False)
    _run(e, False, False)          # test: oba otwarte
    _run(e, True, True)            # oba zamknięte
    assert e.test_done and not e.ok
    _run(e, True, True, reset=True)
    assert e.ok and not e.fault


def test_reset_with_channel_still_different_does_nothing():
    e = _run(Estop2(), True, True)
    _run(e, False, True, seconds=0.2)
    _run(e, False, False)
    _run(e, True, False, reset=True, seconds=0.05)
    assert e.fault and not e.ok
