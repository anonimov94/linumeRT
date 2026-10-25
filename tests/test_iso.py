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
           ISO / "config/includes.chroot/usr/local/bin/linumert", ISO / "test-live-login.sh",
           ISO / "config/includes.chroot/usr/local/bin/linumert-gui"]


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
            "python3-pyqtgraph", "python3-yaml", "python3-numpy", "build-essential",
            "user-setup", "sudo"} <= pkgs
    hook = SCRIPTS[1].read_text()
    for comp in ("lrt_net", "lrt_cia402", "lrt_hardstop_home", "lrt_estop2"):
        assert comp in hook and (ROOT / "hal" / f"{comp}.comp").is_file()


def test_live_login_configuration() -> None:
    build = SCRIPTS[0].read_text()
    hook = SCRIPTS[1].read_text()
    # Debian ma już grupę systemową operator; adduser odmawia utworzenia tego konta.
    assert "username=linumert" in build
    assert "username=operator" not in build
    assert "test -x /usr/lib/user-setup/user-setup-apply" in hook
    assert "[Seat:*]\nautologin-user=linumert\nautologin-user-timeout=0" in hook


def test_launcher_paths_exist() -> None:
    text = SCRIPTS[2].read_text()
    assert "config/sim/linumert_xyz/linumert_xyz.ini" in text
    assert "--expect-profile sim" in text
    assert "--expect-profile plant" in text
    assert "linumert.machine.launch" in text
    assert "--monitor" in text and "tools/dev/skin-monitor.py" in text
    assert (ROOT / "config/sim/linumert_xyz/linumert_xyz.ini").is_file()
    assert (ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini").is_file()
    desktops = ISO / "config/includes.chroot/usr/share/applications"
    for desktop in desktops.glob("*.desktop"):
        body = desktop.read_text()
        assert "Exec=/usr/local/bin/linumert" in body and "Type=Application" in body
    monitor = (desktops / "linumert-monitor.desktop").read_text()
    assert "--monitor" in monitor and "read-only" in monitor
    neon = (desktops / "linumert-neon.desktop").read_text()
    assert "--neon" in neon and "read-only" in neon
    assert "--neon)" in text and "--theme neon-punk" in text


def test_workflow_builds_and_publishes() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/iso.yml").read_text())
    on = wf.get("on") or wf.get(True)
    assert "workflow_dispatch" in on and on["push"]["tags"] == ["v*"]
    steps = " ".join(str(s) for s in wf["jobs"]["iso"]["steps"])
    for word in ("tools/iso/build.sh", "--privileged", "gh release upload", "--prerelease"):
        assert word in steps
    release_step = next(s for s in wf["jobs"]["iso"]["steps"]
                        if s.get("name") == "Wydanie testowe (obraz roboczy, na stałe)")
    assert release_step["if"] == "github.event_name == 'workflow_dispatch'"


def test_desktop_shortcuts_and_restart_flags() -> None:
    """Skróty na pulpicie (symulator, Plant, Neon, stop); launcher zna --restart i --stop."""
    desk = ISO / "config/includes.chroot/etc/skel/Desktop"
    names = {p.name for p in desk.glob("*.desktop")}
    assert names == {"linumert-sim.desktop", "linumert-plant.desktop", "linumert-neon.desktop",
                     "linumert-stop.desktop", "linumert-panel-plant.desktop"}
    for p in desk.glob("*.desktop"):
        body = p.read_text()
        assert "Type=Application" in body and "Exec=" in body
        assert p.stat().st_mode & 0o111, f"{p.name}: skrót bez prawa wykonania"
    assert "--restart --plant" in (desk / "linumert-plant.desktop").read_text()
    launcher = SCRIPTS[2].read_text()
    assert "--restart" in launcher and "--stop" in launcher and "stop_all" in launcher
    hook = SCRIPTS[1].read_text()
    assert "chmod 755 /etc/skel/Desktop/*.desktop" in hook


def test_wifi_and_browser_packages() -> None:
    """Obraz buduje się bez zalecanych pakietów, więc Wi-Fi i przeglądarka muszą być jawne."""
    pkgs = {ln.strip() for ln in (ISO / "config/package-lists/linumert.list.chroot").read_text()
            .splitlines() if ln.strip() and not ln.startswith("#")}
    assert {"network-manager", "network-manager-gnome", "wpasupplicant", "policykit-1", "rfkill",
            "firmware-iwlwifi", "firmware-realtek", "firmware-atheros", "firmware-brcm80211",
            "firmware-misc-nonfree", "firefox-esr"} <= pkgs
    assert "non-free-firmware" in SCRIPTS[0].read_text()
    assert "--apt-recommends false" in SCRIPTS[0].read_text()
