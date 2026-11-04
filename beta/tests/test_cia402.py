"""Testy bezsprzętowego dekodera diagnostyki CiA 402.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT (koordynacja: Claude)
"""

from __future__ import annotations

import pytest

from linumert.diag.cia402 import CiA402State, decode_statusword, describe_error_code


@pytest.mark.parametrize(
    ("state", "statusword"),
    [
        (CiA402State.NOT_READY_TO_SWITCH_ON, 0x00),
        (CiA402State.SWITCH_ON_DISABLED, 0x40),
        (CiA402State.READY_TO_SWITCH_ON, 0x21),
        (CiA402State.SWITCHED_ON, 0x23),
        (CiA402State.OPERATION_ENABLED, 0x27),
        (CiA402State.QUICK_STOP_ACTIVE, 0x07),
        (CiA402State.FAULT_REACTION_ACTIVE, 0x0F),
        (CiA402State.FAULT, 0x08),
    ],
)
@pytest.mark.parametrize("ignored_bits", [0x0000, 0x0280])
def test_each_state_ignores_warning_and_remote(state, statusword, ignored_bits):
    result = decode_statusword(statusword | ignored_bits)
    assert result.state is state
    assert result.description
    assert result.description != CiA402State.UNKNOWN.value


@pytest.mark.parametrize("word", [0x0022, 0x006F, 0xFFFF])
def test_unrecognized_state(word):
    result = decode_statusword(word)
    assert result.state is CiA402State.UNKNOWN
    assert "Nie rozpoznano" in result.description


@pytest.mark.parametrize(
    ("name", "bit"),
    [
        ("voltage_enabled", 4),
        ("warning", 7),
        ("remote", 9),
        ("target_reached", 10),
        ("internal_limit_active", 11),
    ],
)
def test_each_status_flag_is_independent(name, bit):
    base = decode_statusword(0x0027)
    changed = decode_statusword(0x0027 | (1 << bit))
    assert getattr(base, name) is False
    assert getattr(changed, name) is True
    assert changed.state is CiA402State.OPERATION_ENABLED


@pytest.mark.parametrize("raw", [0x0000, 0x1000, 0x2000, 0x3000])
def test_bits_12_and_13_are_returned_without_mode_interpretation(raw):
    result = decode_statusword(0x0027 | raw)
    assert result.bits_12_13 == raw
    assert result.state is CiA402State.OPERATION_ENABLED


@pytest.mark.parametrize("word", [-1, 0x10000, 1.5, "0x0027", None, True])
def test_statusword_range_and_type_validation(word):
    with pytest.raises(ValueError, match="Słowo stanu.*0\\.\\.0xFFFF"):
        decode_statusword(word)


@pytest.mark.parametrize(
    ("code", "description_part"),
    [
        (0x0000, "Brak zgłoszonego błędu"),
        (0x1000, "ogólny"),
        (0x2101, "prądem"),
        (0x2201, "prądem"),
        (0x2301, "prądem"),
        (0x3101, "napięcie"),
        (0x3201, "napięcie"),
        (0x3301, "napięcie"),
        (0x4201, "temperaturą"),
        (0x4301, "temperaturą"),
        (0x5001, "sprzętem"),
        (0x5501, "pamięcią"),
        (0x6101, "oprogramowaniem"),
        (0x6201, "oprogramowaniem"),
        (0x6301, "oprogramowaniem"),
        (0x7101, "dodatkowym"),
        (0x7301, "enkoderem"),
        (0x8101, "komunikacją"),
        (0x8611, "nadążania"),
        (0x8701, "synchronizacją"),
        (0xFF01, "producenta"),
    ],
)
def test_error_code_groups_include_hex(code, description_part):
    result = describe_error_code(code)
    assert description_part in result
    assert f"0x{code:04X}" in result


def test_unknown_error_group_keeps_hex():
    assert describe_error_code(0xBEEF) == "Nierozpoznana grupa błędów napędu (0xBEEF)"


@pytest.mark.parametrize("code", [-1, 0x10000, 1.5, "0x8611", None, False])
def test_error_code_range_and_type_validation(code):
    with pytest.raises(ValueError, match="Kod błędu.*0\\.\\.0xFFFF"):
        describe_error_code(code)


def test_largest_valid_values_are_accepted():
    assert decode_statusword(0xFFFF).state is CiA402State.UNKNOWN
    assert "0xFFFF" in describe_error_code(0xFFFF)


@pytest.mark.parametrize("code", [0x0001, 0x00FF])
def test_nonzero_reserved_error_never_reports_no_error(code):
    result = describe_error_code(code)
    assert "Brak zgłoszonego błędu" not in result
    assert f"0x{code:04X}" in result
