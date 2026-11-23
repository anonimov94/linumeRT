# SPDX-License-Identifier: GPL-2.0-or-later
"""Regresje identyfikatora żądania i wyłączenia potwierdzenia HAL."""

from linumert_webhmi.hal_link import (
    TOOL_ACK,
    TOOL_ACK_LIMIT_S,
    TOOL_NUMBER,
    TOOL_REQUEST,
    ManualToolChange,
)


def test_repeated_tool_number_requires_new_request_id():
    pins = {TOOL_REQUEST: True, TOOL_NUMBER: 2}
    change = ManualToolChange(pins.__getitem__, pins.__setitem__)
    first = change.observe(0, True)
    assert change.resolve(first["id"], 0, confirm=False) == 2
    assert not pins[TOOL_ACK]

    pins[TOOL_REQUEST] = False
    assert change.observe(0.1, True) is None
    pins[TOOL_REQUEST] = True
    second = change.observe(0.2, True)
    assert second["tool"] == 2
    assert second["id"] != first["id"]
    assert change.resolve(first["id"], 0.2, confirm=True) is None
    assert not pins[TOOL_ACK]
    assert change.resolve(second["id"], 0.2, confirm=True) == 2
    assert pins[TOOL_ACK]


def test_confirmation_expires_once_and_does_not_rearm_the_same_request():
    pins = {TOOL_REQUEST: True, TOOL_NUMBER: 3}
    change = ManualToolChange(pins.__getitem__, pins.__setitem__)
    request = change.observe(0, True)
    assert change.resolve(request["id"], 0, confirm=True) == 3
    assert pins[TOOL_ACK]
    assert change.observe(TOOL_ACK_LIMIT_S, True) is None
    assert not pins[TOOL_ACK]
    assert change.resolve(request["id"], TOOL_ACK_LIMIT_S, confirm=True) is None


def test_lost_heartbeat_releases_confirmation():
    pins = {TOOL_REQUEST: True, TOOL_NUMBER: 0}
    change = ManualToolChange(pins.__getitem__, pins.__setitem__)
    request = change.observe(0, True)
    assert change.resolve(request["id"], 0, confirm=True) == 0
    assert change.observe(0.1, False) is None
    assert not pins[TOOL_ACK]
