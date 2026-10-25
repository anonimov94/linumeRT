"""Forensic artifacts must survive the failure they are meant to explain.

Model-Author: Codex. No LinuxCNC instance required.
"""

import io

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
