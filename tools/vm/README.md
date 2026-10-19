# tools/vm

Maszyny wirtualne VM-A (LinuxCNC + ekran) i VM-B (Plant) dla VirtualBox (sesja 025) oraz środowisko WSL
do testów (Codex). Instrukcja krok po kroku: [`docs/VM.md`](../../docs/VM.md).

| Plik | Gdzie | Do czego |
|---|---|---|
| `vm.conf` | — | parametry obu VM (nazwy, vCPU, RAM, adresy lrtnet, porty); jedno źródło dla skryptów i `docs/VM.md` |
| `create-vms.ps1` | Windows | tworzy VM-A i VM-B przez VBoxManage, sprawdza SHA-256 obrazów ISO, instalacja nienadzorowana VM-B |
| `PSScriptAnalyzerSettings.psd1` | — | reguły PSScriptAnalyzer dla `*.ps1` (test: `tests/test_vm_scripts.py`) |
| `preseed-plant.cfg` | VM-B | preseed Debiana 12 netinst (szablon `VBoxManage unattended --script-template`) |
| `post-install-plant.sh` | VM-B | zależności, repozytorium, rdzeń C, usługa systemd `linumert-plant`, opcjonalnie most falownika (`--vfd`) |
| `post-install-ctl.sh` | VM-A | `halcompile --install` komponentów HAL, venv, konfiguracje `*_vm.ini`, opcjonalnie most falownika |
| `lib.sh` | VM-A, VM-B | wspólne funkcje obu skryptów (vm.conf, sieć lrtnet i host-only, klon, venv, plant.yaml) |
| `lrtnet_probe.py` | VM-A | pomiar łącza LRT-NET do Plant: RTT, rozrzut wysyłki, straty, watchdog E-4003 |
| `bootstrap-bookworm.sh` | Linux | rootfs Debiana 12 dla WSL (Codex, [`PODGLAD_UBUNTU.md`](../../docs/PODGLAD_UBUNTU.md)) |
| `setup-debian12-wsl.ps1` | Windows | import rootfs jako dystrybucji WSL (Codex) |
| `start-vnc.sh` | WSL | pulpit testowy przez VNC (Codex) |

Wspólne kroki: VirtualBox i WSL nie dzielą skryptów instalacji (WSL to środowisko testów agentów, VM to
stanowisko właściciela), wspólne są tylko wartości z `vm.conf` i repozytorium. NIEZWERYFIKOWANE W VIRTUALBOX.
