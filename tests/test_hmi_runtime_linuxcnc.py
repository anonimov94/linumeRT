# SPDX-License-Identifier: GPL-2.0-or-later
"""Actual QtVCP must use starter dependencies while pausing/retracting. Model-Author: Codex."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from rip_support import stop_linuxcnc

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.linuxcnc


def test_launcher_runtime_in_actual_hmi_pause_preview_report_and_retract(tmp_path):
    if not shutil.which('linuxcnc') or not os.environ.get('DISPLAY'):
        pytest.skip('LinuxCNC and X11/Xvfb required')
    work = tmp_path / 'cfg'
    shutil.copytree(ROOT / 'config/sim/linumert_xyz', work, symlinks=True)
    for path in work.glob('linumert.var*'):
        path.unlink()
    screen = work / 'qtvcp/screens/linumert'
    screen.unlink()
    screen.symlink_to(ROOT / 'screens/linumert')
    out = tmp_path / 'runtime'
    out.mkdir()
    override = work / 'runtime_probe.py'
    driver = ROOT / 'tests/hmi_pause_runtime_driver.py'
    nc_files = ROOT / 'config/sim/nc_files'
    override.write_text('import runpy\n'
                        f'_probe = runpy.run_path({str(driver)!r})\n'
                        f'self._runtime_probe = _probe["RuntimeProbe"](self.shell, {str(out)!r})\n'
                        'self._runtime_probe.start()\n')
    ini = work / 'linumert_xyz.ini'
    ini.write_text(ini.read_text().replace('[DISPLAY]\n',
                   f'[DISPLAY]\nUSER_COMMAND_FILE = {override}\n').replace(
                   '../../hal/', str(ROOT / 'config/hal') + '/').replace(
                   'PROGRAM_PREFIX = ../nc_files', f'PROGRAM_PREFIX = {nc_files}'))
    env = {**os.environ, 'LINUMERT_SHELL': '1', 'PYTHONPATH': os.pathsep.join(filter(None, (
        str(ROOT / 'core'), os.environ.get('PYTHONPATH'))))}
    log = tmp_path / 'linuxcnc.log'
    with log.open('w') as stream:
        proc = subprocess.Popen([sys.executable, '-m', 'linumert.machine.launch',
                                 '--expect-profile', 'sim', str(ini)], cwd=work, env=env,
                                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        result = out / 'wynik.json'
        try:
            deadline = time.monotonic() + 150
            while not result.exists() and time.monotonic() < deadline:
                assert proc.poll() is None, log.read_text()[-12000:]
                time.sleep(0.25)
            assert result.exists(), log.read_text()[-12000:]
        finally:
            stop_linuxcnc(proc, cwd=work)
    data = json.loads(result.read_text())
    assert not data['errors'], data
    steps = {s['step']: s for s in data['steps']}
    assert all(s['ok'] for s in data['steps']), data
    assert steps['12_withdraw']['offset'] == pytest.approx(2, abs=1e-6)
    assert steps['13_return']['offset'] == pytest.approx(0, abs=1e-6)
    assert steps['14_verify']['interp'] == 'paused'
    assert steps['15_resume']['interp'] == 'idle'
    assert 'ModuleNotFoundError' not in log.read_text()
