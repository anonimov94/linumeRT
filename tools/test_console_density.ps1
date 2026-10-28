# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Codex
param([switch]$Child, [string]$OutputPath)
$ErrorActionPreference = 'Stop'
if ($Child) {
    $env:WT_SESSION = '' # This child was explicitly launched in a classic conhost.
    Add-Type -Path (Join-Path $PSScriptRoot 'ConsoleDensity.cs')
    $baseline = @([Console]::WindowWidth, [Console]::WindowHeight)
    if ([LiteConsoleDensity]::Apply(1).Applied) { throw 'Gestosc 1 nie powinna zmieniac konsoli.' }
    $sessions = @()
    for ($iteration = 0; $iteration -lt 2; $iteration++) {
        $state = $null
        try {
            $state = [LiteConsoleDensity]::Apply(2)
            if (-not $state.Applied) { throw $state.Message }
            if ([Console]::WindowWidth -lt 2 * $baseline[0] -or
                [Console]::WindowHeight -lt 2 * $baseline[1]) { throw 'Siatka mniejsza niz 2x.' }
            $sessions += @{
                Before = @($state.BeforeColumns, $state.BeforeRows)
                During = @($state.AfterColumns, $state.AfterRows)
                Font = @($state.Font.Cell.X, $state.Font.Cell.Y)
            }
            # The second pass exercises finally restoration after an interrupted display.
            if ($iteration -eq 1) { throw [OperationCanceledException]::new('test') }
        }
        catch [OperationCanceledException] { }
        finally { [LiteConsoleDensity]::Restore($state) }
        if ([Console]::WindowWidth -ne $baseline[0] -or
            [Console]::WindowHeight -ne $baseline[1]) { throw 'Nie przywrocono siatki.' }
    }
    if (Compare-Object $sessions[0].Font $sessions[1].Font) { throw 'Nie przywrocono czcionki.' }
    @{Before=$baseline; Passes=$sessions; Restored=$true} | ConvertTo-Json -Depth 4 |
        Set-Content -Encoding UTF8 -LiteralPath $OutputPath
    return
}
$repo = Split-Path -Parent $PSScriptRoot
$out = Join-Path $repo ('build\console-density-' + [Guid]::NewGuid().ToString('N') + '.json')
[IO.Directory]::CreateDirectory((Split-Path -Parent $out)) | Out-Null
$arguments = @('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
    ('"' + $PSCommandPath + '"'), '-Child', '-OutputPath', ('"' + $out + '"'))
$process = Start-Process -FilePath "$env:WINDIR\System32\conhost.exe" -ArgumentList $arguments `
    -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $out)) { throw 'Test HD nieudany.' }
$report = Get-Content -Raw -LiteralPath $out | ConvertFrom-Json
if (-not $report.Restored) { throw 'Test przywracania nieudany.' }
$report | ConvertTo-Json -Depth 4
