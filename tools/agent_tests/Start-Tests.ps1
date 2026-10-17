# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
[CmdletBinding()]
param(
    [ValidateSet('Codex', 'Claude', 'Manual')][string]$Model = 'Manual',
    [string]$Distribution = 'Ubuntu-24.04',
    [ValidateRange(1, 999)][int]$DisplayNumber = 9,
    [switch]$NoVnc
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$linuxRoot = & wsl.exe -d $Distribution --exec wslpath -a -u $projectRoot.Replace('\', '/')
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve project directory in WSL.' }
$linuxRoot = $linuxRoot.Trim()
if ($NoVnc) {
    & wsl.exe -d $Distribution --exec test -x "$linuxRoot/.venv/bin/python"
    $testPython = if ($LASTEXITCODE -eq 0) { "$linuxRoot/.venv/bin/python" } else { 'python3' }
    & wsl.exe -d $Distribution --exec $testPython "$linuxRoot/tools/agent_tests/run.py" --model $Model
} else {
    & wsl.exe -d $Distribution --exec env "LRT_TEST_MODEL=$Model" "LRT_VNC_DISPLAY=$DisplayNumber" bash "$linuxRoot/tools/vm/start-vnc.sh"
}
exit $LASTEXITCODE
