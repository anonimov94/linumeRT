"""Skrypty maszyn wirtualnych bez VirtualBoxa (sesja 025, docs/VM.md).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 025.

Składnia (`bash -n`, shellcheck, PSScriptAnalyzer, jeśli są), brak sekretów, zgodność parametrów
`tools/vm/vm.conf` ↔ `docs/VM.md` ↔ skrypty, plant.yaml generowany dla VM-B (wczytanie przez
`load_plant_config`), kopia INI dla VM-A oraz `create-vms.ps1` z atrapą VBoxManage (z `pwsh`).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VM = ROOT / "tools" / "vm"
DOC = ROOT / "docs" / "VM.md"
SHELL = sorted(VM.glob("*.sh"))
PS1 = sorted(VM.glob("*.ps1"))
OURS = ["lib.sh", "post-install-ctl.sh", "post-install-plant.sh", "create-vms.ps1",
        "preseed-plant.cfg", "lrtnet_probe.py", "vm.conf"]


def conf() -> dict[str, str]:
    out = {}
    for line in (VM / "vm.conf").read_text(encoding="utf-8").splitlines():
        m = re.fullmatch(r"([A-Z][A-Z0-9_]*)=(\S+)", line)
        if m:
            out[m[1]] = m[2]
    return out


def doc() -> str:
    return DOC.read_text(encoding="utf-8")


def bash(script: str, env: dict[str, str] | None = None) -> str:
    full = {**os.environ, **(env or {})}
    return subprocess.run(["bash", "-c", script], cwd=ROOT, env=full, check=True,
                          capture_output=True, text=True).stdout


# ---- składnia i analiza statyczna --------------------------------------------------------------

@pytest.mark.parametrize("path", SHELL, ids=lambda p: p.name)
def test_bash_syntax(path: Path) -> None:
    subprocess.run(["bash", "-n", str(path)], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="brak shellcheck")
def test_shellcheck_clean() -> None:
    r = subprocess.run(["shellcheck", "-x", *map(str, SHELL)], cwd=ROOT, capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def _pwsh() -> str | None:
    return shutil.which("pwsh") or os.environ.get("LRT_PWSH")


def _psscriptanalyzer() -> str | None:
    """Ścieżka modułu PSScriptAnalyzer (zmienna LRT_PSSA albo moduł zainstalowany w pwsh)."""
    return os.environ.get("LRT_PSSA")


@pytest.mark.skipif(_pwsh() is None, reason="brak pwsh")
@pytest.mark.parametrize("path", PS1, ids=lambda p: p.name)
def test_powershell_parses(path: Path) -> None:
    cmd = ("$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
           f"'{path}', [ref]$null, [ref]$e); "
           "if ($e) { $e | ForEach-Object { $_.ToString() }; exit 1 }")
    r = subprocess.run([_pwsh(), "-NoLogo", "-NoProfile", "-Command", cmd], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(_pwsh() is None, reason="brak pwsh")
@pytest.mark.parametrize("path", PS1, ids=lambda p: p.name)
def test_psscriptanalyzer_clean(path: Path) -> None:
    module = _psscriptanalyzer() or "PSScriptAnalyzer"
    settings = VM / "PSScriptAnalyzerSettings.psd1"
    cmd = (f"try {{ Import-Module '{module}' -ErrorAction Stop }} catch {{ exit 77 }}; "
           f"$r = @(Invoke-ScriptAnalyzer -Path '{path}' -Settings '{settings}'); "
           "$r | ForEach-Object { \"$($_.RuleName):$($_.Line) $($_.Message)\" }; exit $r.Count")
    r = subprocess.run([_pwsh(), "-NoLogo", "-NoProfile", "-Command", cmd], capture_output=True,
                       text=True)
    if r.returncode == 77:
        pytest.skip("brak modułu PSScriptAnalyzer")
    assert r.returncode == 0, r.stdout + r.stderr


def test_ps1_with_polish_text_has_bom() -> None:
    # Windows PowerShell 5.1 czyta plik bez BOM jako ANSI: polskie komunikaty by się popsuły.
    for path in PS1:
        data = path.read_bytes()
        if any(b > 0x7F for b in data):
            assert data.startswith(b"\xef\xbb\xbf"), path.name


# ---- bezpieczeństwo i licencja ----------------------------------------------------------------

def test_no_secrets_in_vm_files() -> None:
    pattern = re.compile(r"(passw(or)?d|haslo|hasło)\s*[:=]\s*['\"]?[A-Za-z0-9!@#$%^&*]{4,}", re.I)
    for name in OURS:
        text = (VM / name).read_text(encoding="utf-8-sig")
        assert not pattern.search(text), name
    preseed = (VM / "preseed-plant.cfg").read_text(encoding="utf-8")
    for line in preseed.splitlines():
        if re.match(r"d-i passwd/user-password", line):
            assert line.rstrip().endswith("@@VBOX_INSERT_USER_PASSWORD@@"), line
    assert "passwd/root-login boolean false" in preseed


def test_headers() -> None:
    for name in ("lib.sh", "post-install-ctl.sh", "post-install-plant.sh", "create-vms.ps1",
                 "lrtnet_probe.py"):
        text = (VM / name).read_text(encoding="utf-8-sig")
        assert "SPDX-License-Identifier: GPL-2.0-or-later" in text, name
        assert "Model-Author: Claude" in text, name


# ---- zgodność vm.conf ↔ docs/VM.md ↔ skrypty -----------------------------------------------------

def test_vm_conf_table_in_doc() -> None:
    rows = dict(re.findall(r"^\| `([A-Z0-9_]+)` \| `([^`]+)` \|", doc(), re.M))
    assert rows == conf()


def test_vm_conf_matches_session_prompt_and_plant_spec() -> None:
    c = conf()
    assert 2 <= int(c["CTL_CPUS"]) <= 4 and int(c["CTL_RAM_MB"]) == 4096  # sesja-025.md
    assert int(c["PLANT_CPUS"]) == 2 and int(c["PLANT_RAM_MB"]) == 2048
    assert (c["LRTNET_NAME"], c["PANEL_PORT"]) == ("lrtnet", "8080")
    plant = (ROOT / "docs" / "PLANT.md").read_text(encoding="utf-8")
    assert "lrtnet` (10.77.0.0/24)" in plant
    assert c["LRTNET_CTL_IP"].startswith("10.77.0.") and c["LRTNET_PLANT_IP"].startswith("10.77.0.")
    ini = (ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz_vfd.ini").read_text()
    assert f"DEVICE = {c['VFD_DEVICE']}" in ini
    assert re.search(rf"^PORT = {c['LRTNET_PORT']}$", ini, re.M)


def test_doc_values_follow_vm_conf() -> None:
    c, text = conf(), doc()
    for key in ("LRTNET_CTL_IP", "LRTNET_PLANT_IP", "LRTNET_PORT", "PANEL_PORT", "VFD_BRIDGE_PORT",
                "VFD_DEVICE", "REPO_URL", "REPO_DIR", "VM_USER", "CTL_NAME", "PLANT_NAME"):
        # każda wartość pojawia się w treści instrukcji poza tabelą parametrów
        body = text[: text.index("## 11.")]
        assert c[key] in body, key


def test_doc_script_options_exist() -> None:
    text = doc()
    for script in ("post-install-ctl.sh", "post-install-plant.sh"):
        source = (VM / script).read_text(encoding="utf-8")
        options = set(re.findall(r"^\s+(--[a-z-]+)\)", source, re.M))
        used = set(re.findall(rf"{re.escape(script)}((?: --[a-z-]+)*)", text))
        for group in used:
            for opt in group.split():
                assert opt in options, f"{script} {opt}"
    ps = (VM / "create-vms.ps1").read_text(encoding="utf-8-sig")
    params = set(re.findall(r"\[(?:string|switch)\]\$(\w+)", ps)) | {"Only"}
    for name in re.findall(r"(?<![\w-])-([A-Z]\w+)", text):
        if name in {"Scope", "ExecutionPolicy"}:
            continue
        assert name in params, f"create-vms.ps1 -{name}"
    for name in re.findall(r"tools/vm/([\w.-]+\.(?:sh|ps1|py|cfg|conf))", text):
        assert (VM / name).exists(), name


def _exec_start(script: str, unit: str) -> str:
    text = (VM / script).read_text(encoding="utf-8")
    block = text[text.index(f"/etc/systemd/system/{unit}"):]
    return re.search(r"^ExecStart=(.+)$", block, re.M).group(1)


def test_doc_socat_commands_are_service_commands() -> None:
    # Polecenia w docs/VM.md §7 = ExecStart usług po podstawieniu wartości z vm.conf (1:1).
    c, text = conf(), doc()
    for script, unit in (("post-install-plant.sh", "linumert-vfd-bridge.service"),
                         ("post-install-ctl.sh", "linumert-vfd-link.service")):
        cmd = _exec_start(script, unit)
        for key, value in c.items():
            cmd = cmd.replace(f"${key}", value)
        assert "$" not in cmd
        assert cmd in text, cmd


def test_doc_mentions_unverified_and_hyperv() -> None:
    text = doc()
    assert "NIEZWERYFIKOWANE W VIRTUALBOX" in text and "NIEZWERYFIKOWANE NA SPRZĘCIE" in text
    assert "Hyper-V" in text and "bcdedit /set hypervisorlaunchtype" in text
    assert "nie daje prawdziwego RT" in text


def test_vm_readme_lists_scripts() -> None:
    readme = (VM / "README.md").read_text(encoding="utf-8")
    for path in sorted(VM.iterdir()):
        if path.is_file() and path.name != "README.md":
            assert f"`{path.name}`" in readme, path.name


# ---- wygenerowane pliki ----------------------------------------------------------------------

@pytest.mark.parametrize("vfd", [0, 1])
def test_generated_plant_yaml_loads(tmp_path: Path, vfd: int) -> None:
    from linumert_plant.server import load_plant_config

    text = bash(f". tools/vm/lib.sh; load_conf; plant_yaml {vfd}", {"REPO_DIR": str(ROOT)})
    path = tmp_path / "plant.yaml"
    path.write_text(text, encoding="utf-8")
    cfg = load_plant_config(path)
    c = conf()
    assert cfg.mode == "realtime" and cfg.listen == c["LRTNET_PLANT_IP"]
    assert cfg.port == int(c["LRTNET_PORT"]) and cfg.panel_port == int(c["PANEL_PORT"])
    assert cfg.panel_listen == "0.0.0.0" and cfg.machine.exists()
    assert (cfg.vfd is not None) == bool(vfd)
    if vfd:
        assert str(cfg.vfd.device) == c["VFD_DEVICE"]
    # Te same pola co wzór dla LinuxCNC (plant.yaml / plant_vfd.yaml), poza siecią, trybem i stanem.
    import yaml

    ref = yaml.safe_load((ROOT / "config/plant/linumert_plant_xyz" /
                          ("plant_vfd.yaml" if vfd else "plant.yaml")).read_text(encoding="utf-8"))
    gen = yaml.safe_load(text)
    for key in ("timing", "seed", "oracle"):
        assert gen[key] == ref[key], key
    assert Path(gen["machine"]).name == Path(ref["machine"]).name


def test_ctl_ini_copy_points_to_plant(tmp_path: Path) -> None:
    # Ta sama komenda sed co w post-install-ctl.sh, na kopii INI.
    source = (VM / "post-install-ctl.sh").read_text(encoding="utf-8")
    sed = re.search(r"sed -e (\".*?\") \\\n\s+-e (\".*?\") \\", source)
    assert sed
    c = conf()
    exprs = [e.strip('"').replace("$LRTNET_PLANT_IP", c["LRTNET_PLANT_IP"])
             .replace("$LRTNET_PORT", c["LRTNET_PORT"]) for e in sed.groups()]
    ini = ROOT / "config/plant/linumert_plant_xyz/linumert_plant_xyz.ini"
    out = subprocess.run(["sed", "-e", exprs[0], "-e", exprs[1], str(ini)], check=True,
                         capture_output=True, text=True).stdout
    def split(text: str) -> tuple[str, str]:
        head, rest = text.split("[PLANT]", 1)
        section, _, tail = rest.partition("\n[")
        return section, head + tail

    plant, other = split(out)
    assert f"IP = {c['LRTNET_PLANT_IP']}" in plant and f"PORT = {c['LRTNET_PORT']}" in plant
    assert other == split(ini.read_text())[1]  # poza sekcją [PLANT] bez zmian


def test_vm_ini_copies_are_ignored_by_git() -> None:
    r = subprocess.run(["git", "check-ignore", "-q",
                        "config/plant/linumert_plant_xyz/linumert_plant_xyz_vm.ini"], cwd=ROOT)
    assert r.returncode == 0


# ---- create-vms.ps1 z atrapą VBoxManage -------------------------------------------------------

FAKE_VBOX = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$(dirname "$0")/calls.log"
case "$1 $2" in
  "list hostonlyifs") echo "Name:            VirtualBox Host-Only Ethernet Adapter";;
esac
exit 0
"""


def _run_ps(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    vbox = tmp_path / "VBoxManage"
    vbox.write_text(FAKE_VBOX)
    vbox.chmod(0o755)
    env = {**os.environ, "LRT_VBOXMANAGE": str(vbox)}
    r = subprocess.run([_pwsh(), "-NoLogo", "-NoProfile", "-File", str(VM / "create-vms.ps1"),
                        *args], env=env, capture_output=True, text=True, timeout=120)
    log = tmp_path / "calls.log"
    return r, (log.read_text().splitlines() if log.exists() else [])


@pytest.mark.skipif(_pwsh() is None, reason="brak pwsh")
def test_create_vms_with_fake_vboxmanage(tmp_path: Path) -> None:
    c = conf()
    ctl, plant = tmp_path / "ctl.iso", tmp_path / "plant.iso"
    ctl.write_bytes(b"linuxcnc" * 100)
    plant.write_bytes(b"debian" * 100)
    (tmp_path / "SHA256SUMS").write_text(
        f"{hashlib.sha256(plant.read_bytes()).hexdigest()}  plant.iso\n")
    pw = tmp_path / "pw"
    pw.write_text("x")
    r, calls = _run_ps(tmp_path, "-CtlIso", str(ctl), "-CtlIsoSha256",
                       hashlib.sha256(ctl.read_bytes()).hexdigest(), "-PlantIso", str(plant),
                       "-PasswordFile", str(pw), "-VmRoot", str(tmp_path / "vms"), "-Start")
    assert r.returncode == 0, r.stdout + r.stderr
    text = "\n".join(calls)
    for name, cpus, ram in ((c["CTL_NAME"], c["CTL_CPUS"], c["CTL_RAM_MB"]),
                            (c["PLANT_NAME"], c["PLANT_CPUS"], c["PLANT_RAM_MB"])):
        assert f"createvm --name {name} --ostype Debian_64" in text
        assert f"modifyvm {name} --cpus {cpus} --memory {ram}" in text
    assert text.count(f"--nic2 intnet --intnet2 {c['LRTNET_NAME']}") == 2
    assert text.count("--nic1 nat") == 2 and text.count("--nic3 hostonly") == 2
    assert f"storageattach {c['CTL_NAME']} --storagectl SATA --port 1" in text  # ISO LinuxCNC
    unattended = next(line for line in calls if line.startswith("unattended install"))
    assert f"--user={c['VM_USER']}" in unattended and f"--password-file={pw}" in unattended
    assert "--script-template=" in unattended and "preseed-plant.cfg" in unattended
    assert f"startvm {c['CTL_NAME']} --type gui" in text
    assert pw.exists()  # plik hasła podany przez użytkownika zostaje


@pytest.mark.skipif(_pwsh() is None, reason="brak pwsh")
def test_create_vms_rejects_bad_checksum(tmp_path: Path) -> None:
    ctl = tmp_path / "ctl.iso"
    ctl.write_bytes(b"x" * 10)
    r, calls = _run_ps(tmp_path, "-Only", "ctl", "-CtlIso", str(ctl), "-CtlIsoSha256", "00" * 32)
    assert r.returncode != 0 and "SHA-256" in (r.stdout + r.stderr)
    assert calls == []  # nic nie utworzono
