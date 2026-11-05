"""Piny HAL bramy WebHMI: grzyb, sygnał życia i potwierdzenie E-STOP (D35, D37).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-04

Brama tworzy komponent ``linumert`` z tymi samymi pinami co ekran Qt
(``screens/linumert/linumert_handler.py``), więc łańcuch z ``config/hal/linumert_hmi_estop.hal``
działa bez zmian; sieci łączy ``config/hal/linumert_webhmi_postgui.hal``.

- ``hmi-heartbeat`` przełącza się w każdym obiegu bramy (50 Hz), ale tylko gdy co najmniej jedna
  przeglądarka odezwała się w ciągu ``HEARTBEAT_S``. Zamknięta karta, zawieszona przeglądarka,
  zawieszona albo zabita brama → brak zboczy → ``watchdog`` HAL po
  ``[LINUMERT]HMI_HEARTBEAT_TIMEOUT`` otwiera łańcuch E-STOP.
- ``hmi-wd-enable``: zbocze narastające uzbraja watchdog. Brama uzbraja go raz po starcie
  i przy potwierdzeniu E-STOP (podwójny Reset), jak ekran Qt. Samo uzbrojenie nie zamyka łańcucha:
  zatrzask ``lrt_hmi_ack`` kasuje każde wejście w E-STOP, a ustawia tylko ``hmi-ack``.
- ``hmi-estop-ok`` = 1 (WebHMI nie ma zatrzaskiwanego grzyba; ``estop`` to polecenie LinuxCNC).
- ``hmi-ack``: impuls potwierdzenia przy podwójnym Resecie (D37). Fizycznie otwarty obwód
  safety nadal blokuje maszynę, bo zatrzask E-STOP w HAL go nie omija.

To nie jest funkcja bezpieczeństwa (CLAUDE.md §6). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

from collections.abc import Callable

COMPONENT = "linumert"
PINS = {"ok": "hmi-estop-ok", "hb": "hmi-heartbeat", "wd": "hmi-wd-enable", "ack": "hmi-ack"}
ARM_DELAY_S = 0.4  # po starcie: najpierw kilka zboczy sygnału życia, potem uzbrojenie
PULSE_S = 0.1  # szerokość impulsu ack i przerwy wd przed ponownym uzbrojeniem


class HalPins:
    """Stan pinów HMI; ``write(name, value)`` zapisuje pin (HAL albo atrapa w testach)."""

    def __init__(self, write: Callable[[str, bool], None], now: float):
        self._write = write
        self._hb = False
        self._arm_at: float | None = now + ARM_DELAY_S
        self._release_at: float | None = None
        for key in ("wd", "ack", "hb"):
            write(PINS[key], False)
        write(PINS["ok"], True)

    def tick(self, now: float, alive: bool) -> None:
        """Jeden obieg bramy: zbocze sygnału życia tylko przy żywej przeglądarce."""
        if alive:
            self._hb = not self._hb
            self._write(PINS["hb"], self._hb)
        if self._release_at is not None and now >= self._release_at:
            self._release_at = None
            self._write(PINS["ack"], False)
            self._arm_at = now
        if self._arm_at is not None and now >= self._arm_at:
            self._arm_at = None
            self._write(PINS["wd"], True)

    def acknowledge(self, now: float) -> None:
        """Podwójny Reset: impuls ``hmi-ack`` i ponowne uzbrojenie watchdoga (zbocze wd)."""
        self._write(PINS["wd"], False)
        self._write(PINS["ack"], True)
        self._arm_at = None
        self._release_at = now + PULSE_S


def open_hal(now: float) -> tuple[HalPins, object]:
    """Komponent HAL ``linumert`` z pinami HMI (wymaga ``hal`` z LinuxCNC i działającego HAL)."""
    import hal  # noqa: PLC0415 - moduł LinuxCNC, tylko z --hal

    comp = hal.component(COMPONENT)
    for name in PINS.values():
        comp.newpin(name, hal.HAL_BIT, hal.HAL_OUT)
    comp.ready()

    def write(name: str, value: bool) -> None:
        comp[name] = bool(value)

    return HalPins(write, now), comp
