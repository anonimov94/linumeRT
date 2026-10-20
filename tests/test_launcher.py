"""Starter aplikacji `tools/linumert-start.sh` bez podmana (atrapa). Model-Author: Claude.

SPDX-License-Identifier: GPL-2.0-or-later

Sprawdza: składnię i shellcheck, przebieg z atrapą `podman` (repozytorium, pliki robocze LinuxCNC
jako skip-worktree, skróty w menu, budowa obrazu tylko gdy brak, polecenie uruchomienia dla trybu
symulatora i Plant), opcje opisane w README. Część wykonywaną w kontenerze sprawdzono ręcznie
z LinuxCNC RIP (PR, dziennik); test pełnego obrazu wymaga sieci do linuxcnc.org.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "linumert-start.sh"

FAKE = """#!/bin/bash
echo "podman $*" >> "$FAKE_LOG"
if [ "$1 $2" = "image exists" ]; then [ -n "$FAKE_IMAGE" ] && exit 0 || exit 1; fi
[ "$1" = build ] && cat > /dev/null
exit 0
"""


def test_syntax() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    assert os.access(SCRIPT, os.X_OK)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="brak shellcheck")
def test_shellcheck() -> None:
    r = subprocess.run(["shellcheck", "-x", str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def _clone(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(ROOT), str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-B", "main"], check=True)
    shutil.copy(SCRIPT, repo / "tools" / "linumert-start.sh")  # wersja z drzewa roboczego
    return repo


def _run(tmp_path: Path, repo: Path, *args: str, image: bool = False) -> tuple[str, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "podman"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    log = tmp_path / "podman.log"
    log.unlink(missing_ok=True)
    env = {"HOME": str(tmp_path / "home"), "PATH": f"{bin_dir}:/usr/bin:/bin", "DISPLAY": ":0",
           "FAKE_LOG": str(log), "FAKE_IMAGE": "1" if image else ""}
    r = subprocess.run(["bash", str(repo / "tools" / "linumert-start.sh"), "--no-update", *args],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, log.read_text().splitlines() if log.exists() else []


def test_sim_run_with_fake_podman(tmp_path: Path) -> None:
    repo = _clone(tmp_path)
    out, calls = _run(tmp_path, repo)
    assert any(c.startswith("podman build -t linumert-app:bookworm-") for c in calls)
    run = next(c for c in calls if c.startswith("podman run"))
    assert "--userns=keep-id" in run and f"-v {repo}:/work" in run
    assert run.endswith("linuxcnc /work/config/sim/linumert_xyz/linumert_xyz.ini")
    assert "LINUMERT_SHELL=1" in run
    apps = tmp_path / "home" / ".local" / "share" / "applications"
    desktop = (apps / "linumert.desktop").read_text()
    launcher = apps.parent / "linumert" / "launcher.sh"
    assert f'Exec=bash "{launcher}" --dir "{repo}"' in desktop
    assert launcher.read_bytes() == SCRIPT.read_bytes()
    assert (apps / "linumert-plant.desktop").read_text().count("--plant") == 1
    assert "--classic" in (apps / "linumert-qtdragon.desktop").read_text()
    assert Path(re.search(r"^Icon=(.+)$", desktop, re.M).group(1)).exists()
    flags = subprocess.run(["git", "-C", str(repo), "ls-files", "-v", "config/plant"],
                           capture_output=True, text=True, check=True).stdout
    assert "S config/plant/linumert_plant_xyz/linumert.var" in flags  # skip-worktree
    assert "wersja:" in out


def test_plant_run_and_existing_image(tmp_path: Path) -> None:
    repo = _clone(tmp_path)
    _out, calls = _run(tmp_path, repo, "--plant", "--vfd", image=True)
    assert not any(c.startswith("podman build") for c in calls)  # obraz już jest
    run = next(c for c in calls if c.startswith("podman run"))
    assert "-p 127.0.0.1:8080:8080" in run
    log = "\n".join(calls)  # skrypt kontenera (bash -c) zajmuje wiele linii
    assert "config/plant/linumert_plant_xyz linumert_plant_xyz_vfd.ini plant_vfd.yaml 8080" in log
    assert "--panel-listen 0.0.0.0" in log
    _out, calls = _run(tmp_path, repo, "--classic", image=True)
    assert "LINUMERT_SHELL=0" in next(c for c in calls if c.startswith("podman run"))


def test_bad_option_and_vfd_without_plant(tmp_path: Path) -> None:
    for args in (["--nieznana"], ["--vfd"]):
        r = subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
        assert r.returncode != 0 and "BŁĄD" in r.stderr


def test_container_script_matches_repo() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for comp in re.findall(r"for c in ([\w ]+); do halcompile", text)[0].split():
        assert (ROOT / "hal" / f"{comp}.comp").exists(), comp
    for path in ("config/sim/linumert_xyz/linumert_xyz.ini",
                 "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini",
                 "config/plant/linumert_plant_xyz/linumert_plant_xyz_vfd.ini",
                 "config/plant/linumert_plant_xyz/plant.yaml",
                 "config/plant/linumert_plant_xyz/plant_vfd.yaml"):
        assert (ROOT / path).exists(), path
    assert "EEDD0D29F81DCAA0D258661F3CB9FD148F374FEF" in text  # klucz linuxcnc.org sprawdzany


def test_readme_documents_launcher() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "tools/linumert-start.sh" in readme
    text = SCRIPT.read_text(encoding="utf-8")
    for opt in re.findall(r"^\s+(--[a-z-]+)\)", text, re.M):
        if opt in ("--help",):
            continue
        assert opt in readme or opt in text.split("set -euo")[0], opt


def test_desktop_install_does_not_run_container_or_update(tmp_path):
    repo = _clone(tmp_path)
    out, calls = _run(tmp_path, repo, "--desktop")
    assert not calls and "linumert-qtdragon.desktop" in out


def test_existing_git_worktree_is_not_cloned_again(tmp_path):
    repo = _clone(tmp_path)
    work = tmp_path / "worktree"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(work)],
                   check=True, capture_output=True)
    # Skrypt z drzewa roboczego jest kopią bieżącej wersji, niezależnie od HEAD testu.
    shutil.copy(SCRIPT, work / "tools/linumert-start.sh")
    assert (work / ".git").is_file()
    _out, calls = _run(tmp_path, work, "--desktop", "--dir", str(work))
    assert not calls


def test_desktop_exec_passes_special_paths_as_literal_arguments(monkeypatch):
    gi = pytest.importorskip("gi")
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    # Uploader artefaktów CI odrzuca nazwy z cudzysłowami; sprzątamy także po błędzie.
    with tempfile.TemporaryDirectory(prefix="linumert-desktop-") as folder:
        base = Path(folder) / 'folder with space $cash `ticks` "quote" 50% \\slash'
        base.mkdir()
        repo = _clone(base)
        _run(base, repo, "--desktop")
        desktop = base / "home/.local/share/applications/linumert.desktop"
        text = desktop.read_text().replace("Terminal=true", "Terminal=false")
        desktop.write_text(text)
        target = base / "argv"
        fake = base / "bin/bash"
        fake.write_text('#!/bin/bash\nprintf "%s\\0" "$@" > "$LINUMERT_TEST_ARGV"\n')
        fake.chmod(0o755)
        monkeypatch.setenv("PATH", f"{base / 'bin'}:/usr/bin:/bin")
        monkeypatch.setenv("LINUMERT_TEST_ARGV", str(target))
        app = Gio.DesktopAppInfo.new_from_filename(str(desktop))
        assert app is not None and app.launch([], None)
        expected = [str(base / "home/.local/share/linumert/launcher.sh"), "--dir", str(repo)]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if target.exists() and target.read_bytes().split(b"\0")[:-1] == [
                    arg.encode() for arg in expected]:
                break
            time.sleep(0.01)
        assert target.read_bytes().split(b"\0")[:-1] == [arg.encode() for arg in expected]


@pytest.mark.skipif(shutil.which("desktop-file-validate") is None,
                    reason="brak desktop-file-validate")
def test_generated_desktop_entries_are_valid(tmp_path):
    repo = _clone(tmp_path)
    _run(tmp_path, repo, "--desktop")
    for path in (tmp_path / "home/.local/share/applications").glob("linumert*.desktop"):
        result = subprocess.run(["desktop-file-validate", str(path)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
