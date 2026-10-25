"""Forensic artifacts must survive the failure they are meant to explain.

Model-Author: Codex. No LinuxCNC instance required.
"""

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from linumert_plant.scenario_linuxcnc import _capture, _workspace


def test_diagnostic_workspace_survives_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("LINUMERT_SCENARIO_DIAGNOSTICS", str(tmp_path / "evidence"))
    with pytest.raises(RuntimeError, match="driver interrupted"):
        with _workspace() as work:
            _capture(io.StringIO("T0\nKeyboardInterrupt\n"), work / "driver.log")
            raise RuntimeError("driver interrupted")
    assert (work / "driver.log").read_text() == "T0\nKeyboardInterrupt\n"
    with _workspace() as another:
        assert another != work


def test_normal_workspace_is_cleaned_on_exception(monkeypatch):
    monkeypatch.delenv("LINUMERT_SCENARIO_DIAGNOSTICS", raising=False)
    with pytest.raises(RuntimeError):
        with _workspace() as work:
            raise RuntimeError
    assert not work.exists()


def test_relative_diagnostics_path_survives_driver_chdir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LINUMERT_SCENARIO_DIAGNOSTICS", "build/evidence")
    with _workspace() as work:
        assert work.is_absolute()
        assert work.parent == tmp_path / "build/evidence"


@pytest.mark.parametrize("diagnostics,hal_available", [(False, True), (True, True), (True, False)])
def test_setup_error_evidence_before_program_clock(monkeypatch, capsys, diagnostics, hal_available):
    from linumert_plant.scenario_linuxcnc import DRIVER

    messages = [(1, "joint 3 following error"), None]
    joints = [{"ferror_current": 0.0, "homing": 1} for _ in range(4)]
    joints[3]["ferror_current"] = 0.3
    status = SimpleNamespace(poll=lambda: None, task_state=7, joint=joints)

    def read_hal(name):
        if not hal_available:
            raise RuntimeError("pin unavailable")
        return 1

    monkeypatch.setitem(sys.modules, "hal", SimpleNamespace(
        component=lambda name: SimpleNamespace(ready=lambda: None), get_value=read_hal))
    monkeypatch.setitem(sys.modules, "linuxcnc", SimpleNamespace(
        command=lambda: None, stat=lambda: status,
        error_channel=lambda: SimpleNamespace(poll=lambda: messages.pop(0))))
    monkeypatch.setattr(sys, "argv", ["driver.py", json.dumps({"diagnostics": diagnostics})])
    namespace = {}
    # Execute the actual embedded driver definitions without starting the machine.
    exec(DRIVER.split('out["machine_on"] = machine_on()', 1)[0], namespace)
    namespace["poll"]()
    out = namespace["out"]
    assert out["setup_errors"] == [[0.0, "joint 3 following error"]]
    if diagnostics:
        sample = out["setup_samples"][0]
        assert sample["joints"][3]["ferror_current"] == 0.3
        assert sample["joints"][3]["homing"] == 1
        assert sample["read_finished"] >= sample["elapsed"] >= 0
        assert ("hal_read_error" in sample) is not hal_available
        assert "SETUP_ERROR " in capsys.readouterr().out
        joints[3]["ferror_current"] = 0.0
        assert sample["joints"][3]["ferror_current"] == 0.3  # snapshot, not mutable status
    else:
        assert "setup_samples" not in out and not capsys.readouterr().out
    messages.extend([(1, "later program error"), None])
    namespace["T0"] = namespace["time"].time()
    namespace["poll"]()
    assert len(out.get("setup_samples", [])) == int(diagnostics)
    assert out["errors"][0][1] == "later program error"


@pytest.mark.parametrize("console", [False, True])
def test_linuxcnc_console_controls_launcher_redirection(monkeypatch, console):
    import rip_support

    calls = []
    monkeypatch.setattr(rip_support, "cleanup_linuxcnc", lambda *args: None)
    monkeypatch.setattr(rip_support.subprocess, "Popen", lambda args, **kw: calls.append(args))
    rip_support.start_linuxcnc(Path("/rip"), Path("/work/test.ini"), console=console)
    assert ("linuxcnc -r " in calls[0][-1]) is console
