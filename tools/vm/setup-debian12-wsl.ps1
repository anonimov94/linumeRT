# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
[CmdletBinding()]
param(
    [string]$Distro = 'linumeRT-Debian12',
    [string]$BootstrapDistribution = 'Ubuntu-24.04',
    [string]$RootfsTar,
    [string]$InstallLocation = (Join-Path $env:LOCALAPPDATA 'linumeRT/WSL/Debian12')
)
$ErrorActionPreference = 'Stop'
function Invoke-WslChecked {
    & wsl.exe @args
    if ($LASTEXITCODE -ne 0) { throw "WSL failed (exit $LASTEXITCODE)." }
}
$existing = (& wsl.exe --list --quiet) -replace "`0", ''
if ($Distro -notin ($existing | ForEach-Object { $_.Trim() })) {
    if (-not $RootfsTar) {
        $repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
        $RootfsTar = Join-Path $repo 'state/debian12-rootfs.tar'
        if (-not (Test-Path -LiteralPath $RootfsTar)) {
            $bootstrap = (& wsl.exe -d $BootstrapDistribution --exec wslpath -u "$PSScriptRoot/bootstrap-bookworm.sh".Replace('\', '/')).Trim()
            $output = (& wsl.exe -d $BootstrapDistribution --exec wslpath -u $RootfsTar.Replace('\', '/')).Trim()
            Invoke-WslChecked -d $BootstrapDistribution -u root -- bash $bootstrap $output
        }
    }
    $RootfsTar = (Resolve-Path -LiteralPath $RootfsTar).Path
    if ((Test-Path -LiteralPath $InstallLocation) -and
        (Get-ChildItem -LiteralPath $InstallLocation -Force | Select-Object -First 1)) {
        throw "Choose an unused installation directory: $InstallLocation"
    }
    New-Item -ItemType Directory -Force -Path $InstallLocation | Out-Null
    Invoke-WslChecked --import $Distro $InstallLocation $RootfsTar --version 2
}
# Do not trust the Store's rolling Debian image or the name of an existing distro.
$release = (& wsl.exe -d $Distro -u root --exec cat /etc/os-release) -join "`n"
if ($LASTEXITCODE -ne 0 -or $release -notmatch '(?m)^ID=debian$' -or
    $release -notmatch '(?m)^VERSION_ID="12"$') { throw 'The distro must be Debian 12.' }
& wsl.exe -d $Distro -u root --exec id codex 2>$null
if ($LASTEXITCODE -ne 0) {
    Invoke-WslChecked -d $Distro -u root --exec /usr/sbin/useradd -m -s /bin/bash codex
}
Write-Host "Ready: $Distro (Debian 12). Run builds as: wsl -d $Distro -u codex"
