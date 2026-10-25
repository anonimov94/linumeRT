"""ISO safe graphics must retain a usable legacy Qt context. Model-Author: Codex."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "tools/iso/config/includes.chroot/usr/local/bin/linumert"


def test_safe_launcher_keeps_software_context_for_qtdragon(tmp_path):
    if not shutil.which("xvfb-run"):
        pytest.skip("requires Xvfb for real Qt context")
    pytest.importorskip("PyQt5.QtOpenGL")
    app = tmp_path / "app"
    runtime = tmp_path / "runtime/bin"
    commands = tmp_path / "commands"
    app.mkdir()
    runtime.mkdir(parents=True)
    commands.mkdir()
    pgrep = commands / "pgrep"
    pgrep.write_text("#!/bin/sh\nexit 1\n")  # never inspect or stop another user's CNC
    pgrep.chmod(0o755)
    result = tmp_path / "environment.json"
    fake_python = runtime / "python"
    fake_python.write_text(f"#!{sys.executable}\nimport os,json\n"
                           f"open({str(result)!r},'w').write(json.dumps(dict(os.environ)))\n")
    fake_python.chmod(0o755)
    launcher = tmp_path / "launcher"
    launcher.write_text(LAUNCHER.read_text().replace("/opt/linumeRT", str(app))
                        .replace("/opt/linumert/bin", str(runtime)))
    env = {**os.environ, "PATH": f"{commands}:{os.environ['PATH']}"}
    run = subprocess.run(["bash", str(launcher), "--safe"], env=env,
                         capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stdout + run.stderr
    captured = json.loads(result.read_text())
    assert captured["LIBGL_ALWAYS_SOFTWARE"] == "1"
    assert captured["LINUMERT_NO_GL"] == "1"
    probe = ("from PyQt5 import QtWidgets,QtOpenGL; "
             "a=QtWidgets.QApplication([]); w=QtOpenGL.QGLWidget(); "
             "w.resize(200,200); w.show(); a.processEvents(); "
             "print('CONTEXT',w.isValid()); w.close()")
    run = subprocess.run(["xvfb-run", "-a", sys.executable, "-c", probe], env=captured,
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "CONTEXT True" in run.stdout, run.stdout + run.stderr
