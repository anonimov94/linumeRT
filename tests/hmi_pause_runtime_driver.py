# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise the actual QtVCP process, pause widgets and HAL. Model-Author: Codex."""
import os
from pathlib import Path
from unittest.mock import patch

import pydantic
from linumert_shell_selftest import ACTION, SelfTest
from PyQt5 import QtWidgets

import hal

PROGRAM = ''';@STOCK BOX X20 Y20 Z5 ORIGIN=TOP_FRONT_LEFT OFFSET=G54
G21 G90 G17 G94 G40 G49 G80
M61 Q1
S3000 M3
G0 Z-5
G0 X100 Y100
G1 Z-20 F600
G1 X250 F600
G0 Z-5
M5
M2
'''


class RuntimeProbe(SelfTest):
    def __init__(self, shell, out):
        super().__init__(shell, out)
        Path(self.program).write_text(PROGRAM)
        self.panel = shell.production.retract_panel
        self.report = Path(out) / 'paused-report.html'

    def _plan(self):
        s, b = self.shell.s, self.shell.buttons
        return [
            ('01_runtime', self._runtime, None, 1),
            ('02_estop', lambda: self._start_action('estop'), lambda: not s.estop, 10),
            ('03_power', lambda: self._start_action('power'), lambda: s.machine_on, 10),
            ('04_home', lambda: self._start_action('homed'), lambda: s.all_homed, 90),
            ('05_program', lambda: ACTION.OPEN_PROGRAM(self.program),
             lambda: s.file == self.program, 10),
            ('06_auto', lambda: self._click(b['mode_auto']), lambda: s.mode == 'auto', 10),
            ('07_run', lambda: self._click(b['start']),
             lambda: s.interp == 'run' and self.shell.positions[0][0] > 125, 40),
            ('08_pause', lambda: self._click(b['pause']), lambda: s.interp == 'paused', 10),
            ('09_ready', None, lambda: self.panel.withdraw.isEnabled(), 10),
            ('10_preview', self._preview, None, 1),
            ('11_report', self._report, lambda: self.report.exists(), 10),
            ('12_withdraw', self._withdraw,
             lambda: self.shell.retract.model.phase == 'retracted', 10),
            ('13_return', lambda: self._click(self.panel.return_button),
             lambda: not self.shell.retract.model.active, 10),
            ('14_verify', self._verify_return, None, 1),
            ('15_resume', lambda: self._click(b['pause']), lambda: s.interp == 'idle', 45),
        ]

    def _runtime(self):
        assert self.shell.s.virtual, 'This probe is only for the shipped simulation profile'
        assert int(pydantic.__version__.split('.')[0]) >= 2
        assert self.shell.cycles is not None, 'Cycles failed to import in actual QtVCP'
        self.shell.select_area('start')

    def _preview(self):
        self.shell.select_area('sim')
        # Force the successful callback that crashed the operator's actual Qt process.
        # Geometry planning itself is covered by test_resume_preview.py.
        self.shell.sim.on_message({'ev': 'resume_preview', 'ok': True, 'text': 'Podgląd testowy',
                                   'overlap': 2, 'feed': 100,
                                   'points': [(125, 100, -18), (126, 100, -20),
                                              (127, 100, -20)]})
        dialog = self.shell.sim._resume_dialog
        QtWidgets.QApplication.processEvents()
        assert dialog.isVisible()
        assert dialog.grab().save(os.path.join(self.out, 'preview-dialog.png'))
        dialog.close()

    def _report(self):
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName',
                          return_value=(str(self.report), '')):
            self.shell.sim.export_report()

    def _withdraw(self):
        self.shell.select_area('production')
        self.panel.height.setValue(2)
        self.panel.feed.setValue(300)
        self._click(self.panel.withdraw)
        assert self.shell.retract.model.active, self.shell.retract.model.message

    def _verify_return(self):
        assert self.shell.s.interp == 'paused'
        assert abs(hal.get_value('axis.z.eoffset')) < 1e-6
        assert abs(hal.get_value('axis.z.eoffset-request')) < 1e-6
        assert 'data:image/png;base64,' in self.report.read_text()

    def _record(self, name, ok):
        super()._record(name, ok)
        self.steps[-1].update(offset=hal.get_value('axis.z.eoffset'),
                              phase=self.shell.retract.model.phase,
                              pydantic=pydantic.__version__)
