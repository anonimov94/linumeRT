# SPDX-License-Identifier: GPL-2.0-or-later
"""LinuxCNC's fixed Python shebang must retain the launcher's venv dependencies.

Model-Author: Codex.
"""
import json
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_system_python_child_can_import_launchers_venv_dependencies(tmp_path):
    runtime = tmp_path / 'runtime'
    venv.EnvBuilder(with_pip=False).create(runtime)
    python = runtime / 'bin/python'
    purelib = Path(subprocess.check_output(
        [str(python), '-c', 'import sysconfig; print(sysconfig.get_path("purelib"))'],
        text=True).strip())
    (purelib / 'lrt_runtime_probe.py').write_text('value = "venv-only"\n')
    existing = tmp_path / 'existing'
    existing.mkdir()
    (existing / 'lrt_existing_probe.py').write_text('value = "existing-path"\n')
    probe = tmp_path / 'gui.py'
    probe.write_text('import json, sys\nimport lrt_runtime_probe, lrt_existing_probe\n'
                     'print(json.dumps([lrt_runtime_probe.value, lrt_existing_probe.value, '
                     'sys.prefix == sys.base_prefix]))\n')
    binary = tmp_path / 'linuxcnc'
    binary.write_text('#!/bin/sh\nexec "$LRT_TEST_BASE_PYTHON" "$LRT_TEST_GUI_PROBE"\n')
    binary.chmod(0o755)
    ini = tmp_path / 'sim.ini'
    ini.write_text('[LINUMERT]\nMACHINE_PROFILE=sim\n')
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(ROOT / 'core'), str(existing)]),
           'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'],
           'LRT_TEST_BASE_PYTHON': sys._base_executable, 'LRT_TEST_GUI_PROBE': str(probe)}
    run = subprocess.run([str(python), '-m', 'linumert.machine.launch', '--expect-profile',
                          'sim', str(ini)], env=env, text=True, capture_output=True, timeout=15)
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout) == ['venv-only', 'existing-path', True]
    assert json.loads(run.stderr)['profile'] == 'sim'


def test_non_venv_keeps_environment_and_check_does_not_mutate_it(monkeypatch):
    from linumert.machine import launch

    monkeypatch.setattr(launch.sys, 'prefix', sys.base_prefix)
    monkeypatch.setenv('PYTHONPATH', '/caller/core:/caller/custom')
    before = dict(os.environ)
    env = launch.cnc_environment()
    assert env == before
    env['PYTHONPATH'] = 'child-only'
    assert dict(os.environ) == before
