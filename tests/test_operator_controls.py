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


def test_controls_keyboard_jog_units_mdi_and_tool_change(app, monkeypatch):
    import linumert_shell_model as model
    from linumert_operator_controls import OperatorControls
    from PyQt5 import QtCore, QtWidgets
    shell = SimpleNamespace(s=model.ShellState(estop=False, machine_on=True,
                                               homed={"X", "Y", "Z"}),
                            action=Mock(), info=SimpleNamespace(MACHINE_IS_METRIC=False),
                            _allowed=Mock(return_value=True), set_specialist=Mock(),
                            sim=SimpleNamespace(tools={1: {}, 5: {}, 12: {}}))
    panel = OperatorControls(shell)
    panel.speed.setValue(100)
    panel.jog("X", 1)
    assert shell.action.JOG.call_args.args == (0, 1, 100 / 25.4, 0)
    panel.jog("X", 0)
    assert shell.action.JOG.call_args.args[1] == 0
    panel.mdi.setText("G0 X10")
    panel.buttons["mdi"].click()
    shell.action.CALL_MDI.assert_called_with("G0 X10")
    panel.tool.setValue(1)
    panel.buttons["next"].click()
    assert panel.tool.value() == 5
    QtCore.QTimer.singleShot(50, lambda: app.activeModalWidget().button(
        QtWidgets.QMessageBox.Yes).click())
    panel.buttons["m6"].click()
    shell.action.CALL_MDI.assert_called_with("T5 M6")
    panel.buttons["m3"].click()
    shell.action.SET_SPINDLE_ROTATION.assert_called_with(1, 1000)
    shell.s.specialist = True
    panel.refresh()
    assert panel.buttons["jog_X1"].isEnabled()
    assert not panel.buttons["m3"].isEnabled() and not panel.buttons["m6"].isEnabled()
    shell.s.estop = True
    panel.refresh()
    assert not panel.buttons["jog_X1"].isEnabled()
    panel.close()


def test_virtual_reset_requires_explicit_config_and_closed_safety(app, tmp_path, monkeypatch):
    import linumert_shell_model as model
    from linumert_virtual_session import VirtualSession, virtual_config
    from PyQt5 import QtWidgets
    ini = tmp_path / "machine.ini"
    ini.write_text("[LINUMERT]\n")
    assert not virtual_config(ini)
    ini.write_text("[LINUMERT]\nVIRTUAL_MODE=1\n")
    assert virtual_config(ini)
    shell = SimpleNamespace(s=model.ShellState(virtual=True), action=Mock(),
                            sim=SimpleNamespace(reset_stock=Mock(), client=Mock()),
                            reset_alarms=Mock(), show_alarm=Mock())
    session = VirtualSession(shell)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a: QtWidgets.QMessageBox.Yes)
    session.start()
    shell.action.reset_mock()
    session.tick()
    assert not shell.action.mock_calls  # otwarte safety nie włącza napędów
    shell.s.estop = False
    session.tick()
    shell.action.SET_MACHINE_STATE.assert_called_once_with(True)
    shell.s.machine_on = True
    session.tick()
    shell.action.SET_MACHINE_HOMING.assert_called_once_with(-1)
    session.finish()
    shell.sim.client.send.assert_called_with(cmd="recovery", on=False)


def test_legacy_simulation_commands_cannot_enable_safety_control():
    from linumert_sim.live import Live

    live = Live.__new__(Live)
    for cmd in ("recovery", "estop"):
        assert live.command({"cmd": cmd, "on": True})
    # Starszy ekran nie może odtworzyć usuniętego kanału sterowania.
    assert not vars(live)


def test_alarm_panel_preserves_controller_and_estop_codes(app):
    from linumert_alarm_panel import AlarmPanel

    panel = AlarmPanel(SimpleNamespace(reset_alarms=Mock()))
    panel.add("err", "Obwód E-STOP otwarty", "safety")
    assert panel.rows[0].text().startswith("E-1100 ·")
    panel.add("err", "Błąd interpretera", "controller")
    assert panel.rows[0].text().startswith("E-1000 ·")
    panel.add("err", "K-305 · kolizja", "K-305")
    assert panel.rows[0].text() == "K-305 · kolizja"
    panel.close()
