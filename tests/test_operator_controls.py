# SPDX-License-Identifier: GPL-2.0-or-later
"""Obsługa alarmów i sterowania operatora. Model-Author: Codex."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "screens/linumert"))


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("PyQt5.QtWidgets")
    yield qt.QApplication.instance() or qt.QApplication([])


def test_alarm_panel_last_three_and_persistent_causes(app):
    from linumert_alarm_panel import AlarmPanel
    shell = SimpleNamespace(reset_alarms=Mock())
    panel = AlarmPanel(shell)
    for n in range(4):
        panel.add("err", f"alarm {n}", f"cause {n}")
    assert [r.text() for r in panel.rows] == ["alarm 3", "alarm 2", "alarm 1"]
    panel.active = {"cause 1"}
    panel.acknowledge()
    assert [r.text() for r in panel.rows] == ["alarm 1", "—", "—"]
    panel.active.clear()
    panel.acknowledge()
    assert all(r.text() == "—" for r in panel.rows)
    panel.reset.click()
    panel.reset.click()
    shell.reset_alarms.assert_called_once_with(True)
    panel.close()
