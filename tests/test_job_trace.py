"""Cross-interface agreement and strict rejection of incomplete arc geometry.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import pytest
from linumert.programs.job_trace import compare_motion
from linumert.programs.limits import analyze_canon


def test_rounding_tolerance_is_only_for_agreement_not_for_limit_calculation():
    rounded = "1 N5 STRAIGHT_FEED(50.0000, 0, 0, 0, 0, 0)\n"
    precise = "1 N5 STRAIGHT_FEED(50.00004, 0, 0, 0, 0, 0)\n"
    compare_motion(rounded, precise)
    assert analyze_canon(precise, {"X": (0, 50)}, strict=True).violations
    with pytest.raises(ValueError, match="niezgodny tor"):
        compare_motion(rounded, precise.replace("50.00004", "50.0002"))
    with pytest.raises(ValueError, match="niezgodny tor"):
        compare_motion(rounded, precise.replace("N5", "N6"))
    with pytest.raises(ValueError, match="liczba ruchów"):
        compare_motion(rounded, precise + precise)


def test_agreement_normalizes_units_without_reducing_precise_values():
    rounded = ("1 N1 USE_LENGTH_UNITS(CANON_UNITS_INCHES)\n"
               "2 N5 STRAIGHT_FEED(1.0000, 0, 0, 0, 0, 0)\n")
    precise = "1 N5 STRAIGHT_FEED(25.400001, 0, 0, 0, 0, 0)\n"
    compare_motion(rounded, precise)


def test_strict_arcs_do_not_silently_fall_back_to_endpoint_checks():
    canon = ("1 N1 STRAIGHT_TRAVERSE(1, 0, 0, 0, 0, 0)\n"
             "2 N7 ARC_FEED(0, 1.0002, 0, 0, 1, 0, 0, 0, 0)\n")
    with pytest.raises(ValueError, match="linia 7.*niekołowy łuk"):
        analyze_canon(canon, {"X": (-10, 10), "Y": (-10, 10)}, strict=True)
