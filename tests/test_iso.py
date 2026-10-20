"""Obraz live USB / ISO (sesja 077): skrypty, pakiety, skróty, workflow. Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later
Budowa samego obrazu: GitHub Actions (.github/workflows/iso.yml, root + --privileged).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ISO = ROOT / "tools" / "iso"
SCRIPTS = [ISO / "build.sh", ISO / "config/hooks/normal/9000-linumert.hook.chroot",
           ISO / "config/includes.chroot/usr/local/bin/linumert"]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_scripts_syntax_and_mode(script: Path) -> None:
    assert script.stat().st_mode & 0o111, f"{script} bez prawa wykonania"
    shell = "sh" if script.read_text().startswith("#!/bin/sh") else "bash"
    assert subprocess.run([shell, "-n", str(script)]).returncode == 0
    if shutil.which("shellcheck"):
        r = subprocess.run(["shellcheck", str(script)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout


def test_packages_cover_runtime() -> None:
    pkgs = {ln.strip() for ln in (ISO / "config/package-lists/linumert.list.chroot").read_text()
            .splitlines() if ln.strip() and not ln.startswith("#")}
    assert {"linux-image-rt-amd64", "linuxcnc-uspace", "linuxcnc-uspace-dev", "calamares",
            "python3-pyqtgraph", "python3-yaml", "python3-numpy", "build-essential"} <= pkgs
    hook = SCRIPTS[1].read_text()
    for comp in ("lrt_net", "lrt_cia402", "lrt_hardstop_home", "lrt_estop2"):
        assert comp in hook and (ROOT / "hal" / f"{comp}.comp").is_file()


def test_launcher_paths_exist() -> None:
    text = SCRIPTS[2].read_text()
    assert "config/sim/linumert_xyz/linumert_xyz.ini" in text
    assert (ROOT / "config/sim/linumert_xyz/linumert_xyz.ini").is_file()
    assert (ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini").is_file()
    for desktop in (ISO / "config/includes.chroot/usr/share/applications").glob("*.desktop"):
        body = desktop.read_text()
        assert "Exec=/usr/local/bin/linumert" in body and "Type=Application" in body


def test_workflow_builds_and_publishes() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/iso.yml").read_text())
    on = wf.get("on") or wf.get(True)
    assert "workflow_dispatch" in on and on["push"]["tags"] == ["v*"]
    steps = " ".join(str(s) for s in wf["jobs"]["iso"]["steps"])
    for word in ("tools/iso/build.sh", "--privileged", "gh release upload", "--prerelease"):
        assert word in steps
