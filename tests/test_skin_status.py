# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only boundary and loss/recovery tests. Model-Author: Codex."""

import json
import sys
import time
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'screens/linumert'))
from linumert_skin_status import decode_sample, read_status  # noqa: E402


def fake_status():
    api = SimpleNamespace(MODE_MANUAL=1, MODE_MDI=3, MODE_AUTO=2, STATE_ESTOP=1,
                          STATE_ESTOP_RESET=2, STATE_OFF=3, STATE_ON=4,
                          INTERP_IDLE=1, INTERP_READING=2, INTERP_PAUSED=3, INTERP_WAITING=4)
    status = SimpleNamespace(poll=lambda: None, actual_position=(1, 2, 3, 4, 5, 6, 7, 8, 9),
                             linear_units=1.0, angular_units=1.0, axis_mask=511,
                             task_mode=1, task_state=1, interp_state=1, estop=1, enabled=False)
    return status, api


def test_read_only_normalizes_all_axes_and_retains_estop():
    status, api = fake_status()
    status.linear_units = 1 / 25.4
    status.angular_units = 2
    sample = decode_sample(json.dumps(read_status(status, api)).encode(), time.monotonic())
    assert sample.positions == pytest.approx((25.4, 50.8, 76.2, 2, 2.5, 3, 177.8, 203.2, 228.6))
    assert sample.estop and not sample.enabled
    assert sample.mode == 'MODE_MANUAL'
    with pytest.raises(FrozenInstanceError):
        sample.estop = False
    status.axis_mask = 5
    assert read_status(status, api)['positions'][1] is None


@pytest.mark.parametrize(('field', 'value'), [
    ('linear_units', 0), ('angular_units', float('nan')), ('axis_mask', 0),
    ('axis_mask', True), ('axis_mask', 512), ('actual_position', (0,)),
    ('actual_position', (float('inf'),) * 9), ('task_mode', 99),
    ('task_state', True), ('estop', 2), ('enabled', 'yes'),
])
def test_malformed_status_is_not_presented(field, value):
    status, api = fake_status()
    setattr(status, field, value)
    with pytest.raises(ValueError):
        read_status(status, api)


def test_status_exception_and_expiry():
    status, api = fake_status()
    payload = read_status(status, api)
    stamp = payload['acquired_at']
    assert decode_sample(json.dumps(payload).encode(), stamp).fresh(stamp)
    for now in (stamp - .001, stamp + .501):
        with pytest.raises(ValueError, match='expired'):
            decode_sample(json.dumps(payload).encode(), now)
    payload['estop'] = 0
    with pytest.raises(ValueError):
        decode_sample(json.dumps(payload).encode(), stamp)
    with pytest.raises(ValueError):
        decode_sample(b'x' * 4097, stamp)
    def failure():
        raise RuntimeError('NML disconnected')
    status.poll = failure
    with pytest.raises(RuntimeError, match='disconnected'):
        read_status(status, api)


def test_all_skins_show_and_clear_real_data_without_commands():
    pytest.importorskip('PyQt5')
    from linumert_skin_contract import SKIN_IDS, THEME_IDS, PresentationPreferences
    from linumert_skin_monitor import SkinMonitor
    from linumert_skin_readouts import AxisReadout
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    status, api = fake_status()
    for skin in SKIN_IDS:
        window = SkinMonitor(PresentationPreferences(skin=skin))
        window.reader.timer.stop()
        window.show()
        app.processEvents()
        try:
            sample = decode_sample(json.dumps(read_status(status, api)).encode(), time.monotonic())
            window.present(sample, 'sampled')
            dro = window.workspace.findChild(AxisReadout)
            assert dro.display_value('X') == '1.000'
            assert 'ACTIVE' in window.status.text()
            assert 'G53' in dro.accessibleName()
            assert not window.workspace.findChild(QtWidgets.QPlainTextEdit).toPlainText()
            assert all(not b.isEnabled() for b in window.controls.values())
            # A layout rebuild must preserve the snapshot and command restrictions.
            window.select('theme', THEME_IDS[1])
            dro = window.workspace.findChild(AxisReadout)
            assert dro.display_value('X') == '1.000'
            window.present(None, 'read-failed')
            assert dro.display_value('X') == '—.———'
            assert 'E-STOP: —' in window.status.text()
            window.present(sample, 'sampled')
            assert dro.display_value('X') == '1.000'
        finally:
            window.close()
            app.processEvents()


def test_reader_deadline_clears_a_previously_valid_sample():
    pytest.importorskip('PyQt5')
    from linumert_skin_monitor import StatusReader
    from PyQt5 import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    reader = StatusReader()
    reader.timer.stop()
    seen = []
    reader.changed.connect(lambda sample, reason: seen.append((sample, reason)))
    status, api = fake_status()
    reader.sample = decode_sample(json.dumps(read_status(status, api)).encode(), time.monotonic())
    reader.process.start(sys.executable, ['-c', 'import time; time.sleep(10)'])
    try:
        assert reader.process.waitForStarted(1000)
        reader.started = time.monotonic() - .6
        reader.tick()
        assert reader.sample is None
        assert (None, 'reader-timeout') in seen
        assert reader.process.waitForFinished(1000)
        app.processEvents()
        assert reader.process.state() == QtCore.QProcess.NotRunning
        # A successful but malformed response must also clear old data.
        reader.process.start(sys.executable, ['-c', 'print("{}")'])
        assert reader.process.waitForFinished(1000)
        assert (None, 'invalid-status') in seen
    finally:
        reader.stop()
