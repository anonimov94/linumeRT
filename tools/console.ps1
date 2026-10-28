# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
param(
    [ValidateSet('first_motion', 'estop_mid_program')]
    [string]$Scenario = 'first_motion',
    [string]$Distro = 'linumeRT-Debian12'
)
$ErrorActionPreference = 'Stop'
$liteRoot = Split-Path -Parent $PSScriptRoot
$mappedRoot = & wsl.exe -d $Distro -- wslpath -u $liteRoot.Replace('\', '/')
if ($LASTEXITCODE -ne 0 -or -not $mappedRoot) {
    throw 'Nie mozna odczytac sciezki projektu w WSL.'
}
$linuxRoot = ($mappedRoot | Out-String).Trim()
& wsl.exe -d $Distro --cd $linuxRoot -- test -x .venv-linux/bin/python
if ($LASTEXITCODE -ne 0) {
    & wsl.exe -d $Distro --cd $linuxRoot -- python3 -m venv .venv-linux
    if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie utworzyc venv Linux.' }
}
& wsl.exe -d $Distro --cd $linuxRoot -- .venv-linux/bin/python -m pip show linumert-lite *> $null
if ($LASTEXITCODE -ne 0) {
    & wsl.exe -d $Distro --cd $linuxRoot -- .venv-linux/bin/python -m pip install -c requirements-dev.lock -e .
    if ($LASTEXITCODE -ne 0) { throw 'Nie udalo sie zainstalowac zaleznosci lite.' }
}
& wsl.exe -d $Distro --cd $linuxRoot -- .venv-linux/bin/python tools/console_demo.py --scenario $Scenario
exit $LASTEXITCODE
