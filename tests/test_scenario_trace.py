"""HAL trace must be passive and reject lost evidence. Model-Author: Codex."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from linumert_plant.scenario_trace import channels, inspect_trace, prepare


def test_sampler_appended_after_control_files_and_uses_existing_nets(tmp_path):
    ini = tmp_path / "test.ini"
    ini.write_text("[HAL]\nHALFILE = drives.hal\nHALFILE = safety.hal\n\n[TRAJ]\nSPINDLES = 1\n")
    prepare(ini)
    text = ini.read_text()
    assert text.index("safety.hal") < text.index("servo_trace.hal") < text.index("[TRAJ]")
    hal = (tmp_path / "servo_trace.hal").read_text()
    assert hal.splitlines()[-1] == "addf sampler.0 servo-thread"
    assert "net linumert.j3.pos-cmd => sampler.0.pin." in hal
    assert "joint.3.f-error-lim => sampler.0.pin." in hal
    assert "lrt-cia402.3.enabled => sampler.0.pin." in hal
    assert not any(line.startswith(("sets ", "setp ")) for line in hal.splitlines())
    assert len({c[0] for c in channels()}) == len(channels())
    assert len(channels()) <= 21


def _row(number):
    return str(number) + " " + " ".join("0" for _ in channels()) + "\n"


@pytest.mark.parametrize("rows,continuous", [
    (_row(7) + _row(8), True),
    (_row(7) + _row(9), False),
    (_row(7) + _row(7), False),
    ("overrun\n" + _row(7), False),
    ("7 0\n", False),
    (_row(7).replace("0", "nan", 1), False),
    ("", False),
])
def test_trace_integrity_detects_gaps_and_fifo_loss(tmp_path, rows, continuous):
    path = tmp_path / "trace.txt"
    path.write_text(rows)
    assert inspect_trace(path)["continuous"] is continuous


@pytest.mark.parametrize("overruns,collector_code,valid", [("0", 0, True), ("1", 0, False),
                                                       ("0", 1, False)])
def test_recorder_drains_and_closes_before_reporting_integrity(
        monkeypatch, tmp_path, overruns, collector_code, valid):
    from linumert_plant.scenario_trace import Recorder

    calls = []

    def command(root, cmd, cwd):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout=overruns if cmd.endswith("overruns") else "0")

    def launch(args, *, stdout, stderr):
        stdout.write(_row(0) + _row(1))
        return SimpleNamespace(returncode=collector_code,
                               terminate=lambda: calls.append("terminate"),
                               wait=lambda timeout: collector_code)

    monkeypatch.setattr("linumert_plant.scenario_trace.subprocess.Popen", launch)
    ini = tmp_path / "cnc.ini"
    ini.write_text("[HAL]\nHALFILE = machine.hal\n")
    recorder = Recorder(Path("/rip"), ini, tmp_path, SimpleNamespace(rip_run=command))
    recorder.start()
    recorder.stop()
    result = json.loads((tmp_path / "servo_trace.json").read_text())
    assert result["valid"] is valid and result["samples"] == 2
    assert calls.index("halcmd setp sampler.0.enable false") < calls.index("terminate")
    assert recorder.output.closed and recorder.errors.closed


@pytest.mark.linuxcnc
def test_servo_trace_with_real_sampler(monkeypatch, tmp_path):
    from linumert_plant.scenario import load_scenario
    from linumert_plant.scenario_linuxcnc import ROOT, run_linuxcnc
    from rip_support import leftovers, rip_root

    rip_root()
    if leftovers():
        pytest.skip("another LinuxCNC process is active")
    evidence = tmp_path / "evidence"
    monkeypatch.setenv("LINUMERT_SCENARIO_DIAGNOSTICS", str(evidence))
    monkeypatch.setenv("LINUMERT_SCENARIO_SERVO_TRACE", "1")
    result = run_linuxcnc(load_scenario(ROOT / "plant/scenarios/first_motion.yaml"), port=47826)
    meta = json.loads(next(evidence.glob("*/servo_trace.json")).read_text())
    assert meta["valid"], meta
    assert meta["samples"] > 100 and "j3.sw" in meta["columns"]
    assert result.passed, (result.criteria, result.log)
