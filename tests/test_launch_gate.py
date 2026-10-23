# SPDX-License-Identifier: GPL-2.0-or-later
"""Rzeczywista granica exec z atrapą CNC, bez HAL/napędów. Model-Author: Codex."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from linumert.machine.launch import main, preflight
from test_deployment_cli import INI
from test_hal_audit_offline import HAL

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def hardware(tmp_path):
    ini = tmp_path / "machine.ini"
    ini.write_text(INI)
    for name in ("first.hal", "second.hal", "post.hal"):
        (tmp_path / name).write_text(HAL if name == "first.hal" else "# empty\n")
    return ini


def invoke(ini, tmp_path, *args):
    binary = tmp_path / "linuxcnc"
    binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$START_LOG"\nexit 37\n')
    binary.chmod(0o755)
    log = tmp_path / "started"
    env = dict(os.environ, PYTHONPATH=str(ROOT / "core"), START_LOG=str(log),
               PATH=f"{tmp_path}:{os.environ['PATH']}")
    result = subprocess.run([sys.executable, "-m", "linumert.machine.launch", *args, str(ini)],
                            env=env, text=True, capture_output=True, timeout=10)
    return result, log


def test_complete_hardware_reaches_only_fake_cnc(hardware, tmp_path):
    result, log = invoke(hardware, tmp_path)
    assert result.returncode == 37  # Kod atrapy zachowany przez exec.
    assert log.read_text().strip() == str(hardware.resolve())
    report = json.loads(result.stderr)
    assert report["declaration_complete"] and report["static_hal_passed"]
    assert report["hardware_verified"] is False


@pytest.mark.parametrize("mutation", [
    "missing_declaration", "unknown_profile", "missing_profile", "missing_ini", "bad_utf8",
    "bypass", "missing_hal", "dynamic_path", "tcl", "inline_command", "loop",
    "bad_source", "cycle", "duplicate", "include", "default", "invalid_hal",
    "section_comment", "symlink_cycle",
])
def test_refuses_before_exec(hardware, tmp_path, mutation):
    text = hardware.read_text()
    if mutation == "missing_declaration":
        text = text.replace("PHYSICAL_RESET=1", "")
    elif mutation == "unknown_profile":
        text = text.replace("MACHINE_PROFILE=hardware", "MACHINE_PROFILE=other")
    elif mutation == "missing_profile":
        text = text.replace("MACHINE_PROFILE=hardware", "")
    elif mutation == "bypass":
        text = text.replace("MACHINE_PROFILE=hardware",
                            "MACHINE_PROFILE=hardware\nHMI_ESTOP_BYPASS=1")
    elif mutation == "dynamic_path":
        text = text.replace("first.hal", "$UNRESOLVED/main.hal")
    elif mutation == "tcl":
        text = text.replace("first.hal", "first.tcl")
        (tmp_path / "first.tcl").write_text(HAL)
    elif mutation == "inline_command":
        text += "HALCMD=setp iocontrol.0.emc-enable-in 1\n"
    elif mutation == "duplicate":
        text = text.replace("PHYSICAL_RESET=1", "PHYSICAL_RESET=0\nPHYSICAL_RESET=1")
    elif mutation == "include":
        text += "#INCLUDE hidden.ini\n"
    elif mutation == "section_comment":
        text += "[OTHER]\nvalue=1\n[HAL] # ambiguous\nHALFILE=absent.hal\n"
    elif mutation == "default":
        text += "[DEFAULT]\nMACHINE_PROFILE=sim\n"
    elif mutation in ("loop", "bad_source", "cycle", "invalid_hal"):
        extra = {"loop": "net safety iocontrol.0.user-enable-out\n",
                 "bad_source": "source absent.hal\n", "cycle": "source first.hal\n",
                 "invalid_hal": "unlinkp hm2.in-01\n"}[mutation]
        (tmp_path / "first.hal").write_text(HAL + extra)
    hardware.write_text(text)
    if mutation == "missing_ini":
        hardware.unlink()
    elif mutation == "symlink_cycle":
        hardware.unlink()
        hardware.symlink_to(hardware.name)
    elif mutation == "bad_utf8":
        hardware.write_bytes(b"\xff")
    elif mutation == "missing_hal":
        (tmp_path / "post.hal").unlink()
    try:
        result, log = invoke(hardware, tmp_path)
    finally:
        if mutation == "symlink_cycle":
            hardware.unlink(missing_ok=True)
    assert result.returncode == 2, result.stderr
    assert not log.exists()
    assert json.loads(result.stderr)["errors"]


@pytest.mark.parametrize("profile", ["sim", "plant"])
def test_virtual_profiles_skip_physical_audit_and_preserve_exec(tmp_path, profile):
    ini = tmp_path / "virtual.ini"
    ini.write_text(f"[LINUMERT]\nMACHINE_PROFILE={profile}\nHMI_ESTOP_BYPASS=1\n"
                   "[HAL]\nHALFILE=unavailable.hal\n")
    result, log = invoke(ini, tmp_path, "--expect-profile", profile)
    assert result.returncode == 37 and log.exists()
    report = json.loads(result.stderr)
    assert report["static_hal_checked"] is False
    assert report["static_hal_passed"] is None


def test_profile_mismatch_and_check_only_never_execute(hardware, tmp_path):
    for args, code in [(["--expect-profile", "sim"], 2), (["--check-only"], 0)]:
        result, log = invoke(hardware, tmp_path, *args)
        assert result.returncode == code
        assert not log.exists()


def test_all_shipped_virtual_configurations_have_explicit_profile():
    for pattern, profile in [("config/sim/**/*.ini", "sim"), ("config/plant/**/*.ini", "plant")]:
        for path in ROOT.glob(pattern):
            report = preflight(path, profile)
            assert not report["errors"], (path, report)


def test_cnc_unavailable_is_explicit_failure(hardware, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(hardware.parent / "absent"))
    assert main([str(hardware)]) == 2
    assert "Nie uruchomiono LinuxCNC" in capsys.readouterr().err


def test_resolve_failure_is_structured_refusal(hardware, monkeypatch, capsys):
    def fail_resolve(self):
        raise RuntimeError("Symlink loop (Python 3.11)")

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    assert main([str(hardware)]) == 2
    report = json.loads(capsys.readouterr().err)
    assert report["errors"] == ["Symlink loop (Python 3.11)"]
    assert report["hardware_verified"] is False
