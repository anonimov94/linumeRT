"""Odczyt stanu i grup błędów napędu CiA 402, bez zależności od HMI.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: ChatGPT (koordynacja: Claude)

Dekoder służy wyłącznie do diagnostyki, nie do sterowania ani funkcji bezpieczeństwa.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CiA402State(StrEnum):
    """Rozpoznawalne stany maszyny stanów napędu."""

    NOT_READY_TO_SWITCH_ON = "not_ready_to_switch_on"
    SWITCH_ON_DISABLED = "switch_on_disabled"
    READY_TO_SWITCH_ON = "ready_to_switch_on"
    SWITCHED_ON = "switched_on"
    OPERATION_ENABLED = "operation_enabled"
    QUICK_STOP_ACTIVE = "quick_stop_active"
    FAULT_REACTION_ACTIVE = "fault_reaction_active"
    FAULT = "fault"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StatuswordInfo:
    """Wynik dekodowania 0x6041.

    `bits_12_13` to surowa maska 0x3000 (bez przesuwania i interpretowania trybu).
    """

    state: CiA402State
    description: str
    voltage_enabled: bool
    warning: bool
    remote: bool
    target_reached: bool
    internal_limit_active: bool
    bits_12_13: int


# Kolejność nie zmienia wyniku: wzorce stanów są rozłączne.
_STATE_PATTERNS: tuple[tuple[CiA402State, int, int], ...] = (
    (CiA402State.NOT_READY_TO_SWITCH_ON, 0x4F, 0x00),
    (CiA402State.SWITCH_ON_DISABLED, 0x4F, 0x40),
    (CiA402State.READY_TO_SWITCH_ON, 0x6F, 0x21),
    (CiA402State.SWITCHED_ON, 0x6F, 0x23),
    (CiA402State.OPERATION_ENABLED, 0x6F, 0x27),
    (CiA402State.QUICK_STOP_ACTIVE, 0x6F, 0x07),
    (CiA402State.FAULT_REACTION_ACTIVE, 0x4F, 0x0F),
    (CiA402State.FAULT, 0x4F, 0x08),
)

_STATE_DESCRIPTIONS: dict[CiA402State, str] = {
    CiA402State.NOT_READY_TO_SWITCH_ON: "Napęd przygotowuje się do uruchomienia.",
    CiA402State.SWITCH_ON_DISABLED: "Załączenie napędu jest obecnie zablokowane.",
    CiA402State.READY_TO_SWITCH_ON: "Napęd oczekuje na polecenie załączenia.",
    CiA402State.SWITCHED_ON: "Napęd jest załączony, ale ruch nie jest jeszcze dozwolony.",
    CiA402State.OPERATION_ENABLED: "Napęd zgłasza gotowość do pracy.",
    CiA402State.QUICK_STOP_ACTIVE: "Napęd wykonuje procedurę szybkiego zatrzymania.",
    CiA402State.FAULT_REACTION_ACTIVE: "Napęd reaguje na wykryty błąd.",
    CiA402State.FAULT: "Napęd zgłasza błąd wymagający diagnostyki.",
    CiA402State.UNKNOWN: "Nie rozpoznano stanu napędu; sprawdź dane diagnostyczne.",
}

_ERROR_GROUPS: dict[int, str] = {
    0x10: "Błąd ogólny napędu",
    0x21: "Problem z prądem napędu",
    0x22: "Problem z prądem napędu",
    0x23: "Problem z prądem napędu",
    0x31: "Nieprawidłowe napięcie napędu",
    0x32: "Nieprawidłowe napięcie napędu",
    0x33: "Nieprawidłowe napięcie napędu",
    0x42: "Problem z temperaturą napędu",
    0x43: "Problem z temperaturą napędu",
    0x50: "Problem ze sprzętem napędu",
    0x55: "Problem z pamięcią napędu",
    0x61: "Problem z oprogramowaniem napędu",
    0x62: "Problem z oprogramowaniem napędu",
    0x63: "Problem z oprogramowaniem napędu",
    0x71: "Problem z modułem dodatkowym",
    0x73: "Problem z czujnikiem położenia lub enkoderem",
    0x81: "Problem z komunikacją napędu",
    0x86: "Problem z położeniem lub błędem nadążania",
    0x87: "Problem z synchronizacją napędu",
    0xFF: "Błąd zdefiniowany przez producenta napędu",
}


def _check_uint16(value: int, label: str) -> None:
    if type(value) is not int or not 0 <= value <= 0xFFFF:
        raise ValueError(f"{label} musi być liczbą całkowitą z zakresu 0..0xFFFF.")


def decode_statusword(word: int) -> StatuswordInfo:
    """Dekoduje słowo stanu 0x6041, zachowując niezależne bity informacyjne."""
    _check_uint16(word, "Słowo stanu")
    state = CiA402State.UNKNOWN
    for candidate, mask, expected in _STATE_PATTERNS:
        if word & mask == expected:
            state = candidate
            break

    return StatuswordInfo(
        state=state,
        description=_STATE_DESCRIPTIONS[state],
        voltage_enabled=bool(word & (1 << 4)),
        warning=bool(word & (1 << 7)),
        remote=bool(word & (1 << 9)),
        target_reached=bool(word & (1 << 10)),
        internal_limit_active=bool(word & (1 << 11)),
        bits_12_13=word & 0x3000,
    )


def describe_error_code(code: int) -> str:
    """Opisuje grupę kodu błędu 0x603F; nie zgaduje znaczenia dolnego bajtu."""
    _check_uint16(code, "Kod błędu")
    description = ("Brak zgłoszonego błędu" if code == 0 else
                   _ERROR_GROUPS.get(code >> 8, "Nierozpoznana grupa błędów napędu"))
    return f"{description} (0x{code:04X})"
