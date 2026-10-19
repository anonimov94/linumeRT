# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · sesja 025
<#
.SYNOPSIS
    Tworzy w VirtualBox dwie maszyny linumeRT: VM-A linumert-ctl (LinuxCNC 2.9 + ekran) i VM-B
    linumert-plant (Debian 12 + Plant). Parametry: tools/vm/vm.conf. Instrukcja: docs/VM.md.

.DESCRIPTION
    - Sprawdza sumy SHA-256 obrazów ISO (pobierasz je sam, sumy z linuxcnc.org i debian.org).
    - VM-A: obraz LinuxCNC 2.9 w napędzie, instalacja ręczna z pulpitu obrazu (docs/VM.md §3).
    - VM-B: instalacja nienadzorowana Debiana 12 netinst (VBoxManage unattended + preseed-plant.cfg);
      hasło użytkownika podajesz przy uruchomieniu (albo -PasswordFile), nie trafia do repozytorium.
    - Karty: 1 = NAT (internet), 2 = sieć wewnętrzna lrtnet (LRT-NET), 3 = host-only (SSH, panel 8080).
    Skrypt nie usuwa istniejących maszyn: maszyna o tej samej nazwie = błąd.

.EXAMPLE
    .\tools\vm\create-vms.ps1 -CtlIso D:\iso\linuxcnc_2.9.x-amd64.hybrid.iso `
        -CtlIsoSha256 <suma z linuxcnc.org> -PlantIso D:\iso\debian-12.x-amd64-netinst.iso `
        -PlantIsoSha256 <suma z SHA256SUMS> -Start
#>
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingPlainTextForPassword', 'PasswordFile',
    Justification = 'ścieżka pliku z hasłem dla VBoxManage --password-file, nie samo hasło')]
[CmdletBinding()]
param(
    [string]$CtlIso,
    [string]$CtlIsoSha256,
    [string]$PlantIso,
    [string]$PlantIsoSha256,
    [ValidateSet('both', 'ctl', 'plant')] [string]$Only = 'both',
    [string]$VmRoot = (Join-Path $HOME 'VirtualBox VMs'),
    [string]$HostOnlyAdapter,
    [string]$TimeZone = 'Europe/Warsaw',
    [string]$PasswordFile,
    [switch]$NoUnattended,
    [switch]$Start
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$confPath = Join-Path $PSScriptRoot 'vm.conf'
$conf = (Get-Content -Raw -Encoding UTF8 $confPath) | ConvertFrom-StringData

function Find-VBoxManage {
    $candidates = @()
    if ($env:LRT_VBOXMANAGE) { $candidates += $env:LRT_VBOXMANAGE }  # testy: atrapa VBoxManage
    if ($env:VBOX_MSI_INSTALL_PATH) { $candidates += (Join-Path $env:VBOX_MSI_INSTALL_PATH 'VBoxManage.exe') }
    $candidates += 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($cmd) { $candidates = @($cmd.Source) + $candidates }
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw 'Nie znaleziono VBoxManage. Zainstaluj VirtualBox 7 (virtualbox.org) i uruchom ponownie.'
}

# Prosta funkcja (bez [Parameter]): argumenty --opcja trafiają do $args jako tekst.
function Invoke-VBox {
    $VBoxArgs = [string[]]$args
    Write-Host "  VBoxManage $($VBoxArgs -join ' ')" -ForegroundColor DarkGray
    $out = & $script:VBox @VBoxArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "VBoxManage $($VBoxArgs[0]) zakończył się kodem ${LASTEXITCODE}:`n$out" }
    return $out
}

function Test-IsoChecksum {
    param([string]$Path, [string]$Expected, [string]$Label)
    if (-not $Path) { throw "Podaj ścieżkę obrazu ISO dla $Label." }
    if (-not (Test-Path $Path)) { throw "Brak pliku ISO dla ${Label}: $Path" }
    $name = Split-Path -Leaf $Path
    if (-not $Expected) {
        # Suma z pliku obok obrazu: <obraz>.sha256 albo SHA256SUMS (format sha256sum).
        $dir = Split-Path -Parent $Path
        foreach ($f in @("$Path.sha256", (Join-Path $dir 'SHA256SUMS'))) {
            if (Test-Path $f) {
                $line = Get-Content $f | Where-Object { $_ -match [regex]::Escape($name) -or $_ -match '^[0-9a-fA-F]{64}\s*$' } |
                    Select-Object -First 1
                if ($line) { $Expected = ($line -split '\s+')[0]; break }
            }
        }
    }
    if (-not $Expected) { throw "Brak sumy SHA-256 dla $Label (parametr albo plik .sha256 / SHA256SUMS obok obrazu)." }
    Write-Host "Sprawdzam SHA-256 $name ..."
    $actual = (Get-FileHash -Algorithm SHA256 -Path $Path).Hash
    if ($actual -ne $Expected.Trim().ToUpperInvariant()) {
        throw "Suma SHA-256 obrazu $Label się nie zgadza.`n  oczekiwana: $Expected`n  obliczona:  $actual"
    }
    Write-Host "  OK ($actual)" -ForegroundColor Green
}

function Get-HostOnlyAdapter {
    if ($HostOnlyAdapter) { return $HostOnlyAdapter }
    $list = Invoke-VBox list hostonlyifs
    $names = @($list | Select-String '^Name:\s+(.+)$' | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() })
    if ($names.Count -gt 0) { return $names[0] }
    $created = Invoke-VBox hostonlyif create
    $m = [regex]::Match(($created -join "`n"), "Interface '([^']+)'")
    if (-not $m.Success) { throw "Nie udało się utworzyć karty host-only:`n$created" }
    return $m.Groups[1].Value
}

function New-LinumertVm {
    param([string]$Name, [int]$Cpus, [int]$RamMb, [int]$DiskMb, [int]$VramMb, [string]$HostOnly)
    $existing = Invoke-VBox list vms
    if (($existing -join "`n") -match ('"' + [regex]::Escape($Name) + '"')) {
        throw "Maszyna $Name już istnieje. Usuń ją w VirtualBox albo zmień nazwę w vm.conf."
    }
    Write-Host "Tworzę $Name ($Cpus vCPU, $RamMb MB RAM, dysk $DiskMb MB)" -ForegroundColor Cyan
    Invoke-VBox createvm --name $Name --ostype Debian_64 --basefolder $VmRoot --register | Out-Null
    Invoke-VBox modifyvm $Name --cpus $Cpus --memory $RamMb --vram $VramMb --graphicscontroller vmsvga `
        --firmware bios --rtcuseutc on --paravirtprovider kvm --ioapic on --boot1 disk --boot2 dvd `
        --nic1 nat --nic2 intnet --intnet2 $conf.LRTNET_NAME --nic3 hostonly --hostonlyadapter3 $HostOnly | Out-Null
    $disk = Join-Path (Join-Path $VmRoot $Name) "$Name.vdi"
    Invoke-VBox createmedium disk --filename $disk --size $DiskMb --format VDI | Out-Null
    Invoke-VBox storagectl $Name --name SATA --add sata --controller IntelAhci --portcount 2 | Out-Null
    Invoke-VBox storageattach $Name --storagectl SATA --port 0 --device 0 --type hdd --medium $disk | Out-Null
}

$script:VBox = Find-VBoxManage
$doCtl = $Only -in @('both', 'ctl')
$doPlant = $Only -in @('both', 'plant')
if ($doCtl) { Test-IsoChecksum $CtlIso $CtlIsoSha256 'VM-A (LinuxCNC 2.9)' }
if ($doPlant) { Test-IsoChecksum $PlantIso $PlantIsoSha256 'VM-B (Debian 12 netinst)' }
$hostOnly = Get-HostOnlyAdapter
Write-Host "Sieć host-only: $hostOnly; sieć wewnętrzna: $($conf.LRTNET_NAME)"

if ($doCtl) {
    $n = $conf.CTL_NAME
    New-LinumertVm $n ([int]$conf.CTL_CPUS) ([int]$conf.CTL_RAM_MB) ([int]$conf.CTL_DISK_MB) ([int]$conf.CTL_VRAM_MB) $hostOnly
    Invoke-VBox storageattach $n --storagectl SATA --port 1 --device 0 --type dvddrive --medium $CtlIso | Out-Null
    if ($Start) { Invoke-VBox startvm $n --type gui | Out-Null }
}

if ($doPlant) {
    $n = $conf.PLANT_NAME
    New-LinumertVm $n ([int]$conf.PLANT_CPUS) ([int]$conf.PLANT_RAM_MB) ([int]$conf.PLANT_DISK_MB) ([int]$conf.PLANT_VRAM_MB) $hostOnly
    if ($NoUnattended) {
        Invoke-VBox storageattach $n --storagectl SATA --port 1 --device 0 --type dvddrive --medium $PlantIso | Out-Null
        if ($Start) { Invoke-VBox startvm $n --type gui | Out-Null }
    } else {
        $pwFile = $PasswordFile
        if (-not $pwFile) {
            $pw1 = Read-Host -AsSecureString "Hasło użytkownika $($conf.VM_USER) w VM-B"
            $pw2 = Read-Host -AsSecureString 'Powtórz hasło'
            $plain1 = [Net.NetworkCredential]::new('', $pw1).Password
            $plain2 = [Net.NetworkCredential]::new('', $pw2).Password
            if ($plain1 -ne $plain2 -or -not $plain1) { throw 'Hasła są puste albo różne.' }
            $pwFile = [IO.Path]::GetTempFileName()
            [IO.File]::WriteAllText($pwFile, $plain1)
            $plain1 = $plain2 = $null
        }
        $preseed = Join-Path $PSScriptRoot 'preseed-plant.cfg'
        $unattended = @('unattended', 'install', $n, "--iso=$PlantIso", "--user=$($conf.VM_USER)",
            "--password-file=$pwFile", '--full-user-name=linumeRT', "--hostname=$($conf.PLANT_HOSTNAME).local",
            '--locale=pl_PL', '--country=PL', "--time-zone=$TimeZone", "--script-template=$preseed")
        if ($Start) { $unattended += '--start-vm=gui' }
        try {
            Invoke-VBox @unattended | Out-Null
        } finally {
            # Plik z hasłem podanym interaktywnie usuwamy; plik z -PasswordFile należy do użytkownika.
            if (-not $PasswordFile) { Remove-Item -Force $pwFile -ErrorAction SilentlyContinue }
        }
    }
}

Write-Host ''
Write-Host 'Gotowe. Dalej: docs/VM.md' -ForegroundColor Green
if ($doCtl) { Write-Host "  VM-A $($conf.CTL_NAME): zainstaluj z pulpitu obrazu LinuxCNC (użytkownik $($conf.VM_USER)), potem post-install-ctl.sh" }
if ($doPlant) { Write-Host "  VM-B $($conf.PLANT_NAME): po instalacji post-install-plant.sh" }
