# Maszyny wirtualne VM-A i VM-B (VirtualBox)

Model-Author: Claude · sesja 025 · 2026-10-19. Skrypty: [`tools/vm/`](../tools/vm/README.md).
**NIEZWERYFIKOWANE W VIRTUALBOX**: skrypty sprawdzono shellcheckiem, PSScriptAnalyzerem i z atrapą
`VBoxManage` (tests/test_vm_scripts.py), a łącze LRT-NET między dwiema instancjami na localhost
(tests/test_vm_link.py). Pierwsza instalacja na Windows to punkt do sprawdzenia ręcznie (§10).
Nic tu nie dotyczy prawdziwej maszyny: NIEZWERYFIKOWANE NA SPRZĘCIE.

```
Windows (host) ── host-only ─┬─ VM-A linumert-ctl   LinuxCNC 2.9 + ekran linumeRT   10.77.0.10
   przeglądarka :8080, SSH   └─ VM-B linumert-plant Plant (usługa linumert-plant)   10.77.0.20
                                 VM-A ◄── sieć wewnętrzna lrtnet, LRT-NET UDP 47700 ──► VM-B
```

Karty sieciowe w obu VM: **1** NAT (internet, apt, git), **2** sieć wewnętrzna `lrtnet` (tylko VM-A ↔ VM-B,
adresy stałe), **3** host-only (SSH i panel Plant z Windows, adres z DHCP VirtualBoxa).

## 1. Wymagania i Hyper-V
- Windows 10/11, VirtualBox 7.0 lub nowszy (virtualbox.org), ok. 8 GB RAM i 50 GB miejsca na dysku.
- **Hyper-V, WSL 2, „Izolacja rdzenia / Integralność pamięci”** włączają hiperwizor Windows. VirtualBox działa
  wtedy przez Windows Hypervisor Platform (zielony żółw w pasku stanu VM): wolniej i z większym rozrzutem
  czasu. To wystarcza do pracy z Plant (§8). Jeśli chcesz pełną wydajność VirtualBoxa i nie potrzebujesz
  w tym czasie WSL 2, w PowerShellu jako administrator:
  ```powershell
  bcdedit /set hypervisorlaunchtype off   # potem restart; powrót: bcdedit /set hypervisorlaunchtype auto
  ```
- Nie uruchamiaj VirtualBoxa i testów w WSL (`tools/dev/wsl-test.sh --linuxcnc`) naraz: oba obciążają te same rdzenie.

## 2. Obrazy ISO i sumy kontrolne
Pobierasz sam (skrypt niczego nie pobiera), do jednego katalogu, np. `D:\iso`:

| VM | Obraz | Skąd | Suma |
|---|---|---|---|
| VM-A | LinuxCNC 2.9 (Debian 12, amd64, `*.hybrid.iso`) | linuxcnc.org → Downloads | SHA-256 podana na stronie pobierania |
| VM-B | Debian 12 netinst amd64 (`debian-12.*-amd64-netinst.iso`) | debian.org/distrib/netinst | plik `SHA256SUMS` z tego samego katalogu |

`create-vms.ps1` liczy SHA-256 i przerywa przy niezgodności. Sumę podajesz parametrem `-CtlIsoSha256` /
`-PlantIsoSha256` albo kładziesz obok obrazu plik `<obraz>.sha256` lub `SHA256SUMS` (format `sha256sum`).

## 3. Tworzenie maszyn (Windows)
W PowerShellu, w katalogu repozytorium (klon na dysku Windows wystarczy):
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\vm\create-vms.ps1 -CtlIso D:\iso\linuxcnc-2.9.x-amd64.hybrid.iso -CtlIsoSha256 <suma> -PlantIso D:\iso\debian-12.x-amd64-netinst.iso -Start
```
- Skrypt pyta o hasło użytkownika `linumert` w VM-B (nie trafia do repozytorium; można też `-PasswordFile <plik>`).
- Tylko jedna maszyna: `-Only ctl` albo `-Only plant`. Instalacja VM-B ręczna zamiast nienadzorowanej: `-NoUnattended`.
- Własna karta host-only: `-HostOnlyAdapter "VirtualBox Host-Only Ethernet Adapter #2"`; bez parametru skrypt bierze
  pierwszą istniejącą albo tworzy nową. Katalog maszyn: `-VmRoot` (domyślnie `~\VirtualBox VMs`).
- Maszyna o tej samej nazwie już istnieje → błąd; skrypt niczego nie usuwa.

## 4. VM-A: LinuxCNC i ekran linumeRT
1. W oknie VM-A uruchom instalator z pulpitu obrazu LinuxCNC (Install). Użytkownik: **`linumert`**
   (inna nazwa: przy kroku 3 `VM_USER=<login> sudo -E bash ...`). Po instalacji wysuń obraz
   (Urządzenia → Napędy optyczne) i uruchom VM ponownie.
2. W terminalu VM-A:
   ```bash
   sudo apt-get install -y git
   git clone --depth 1 https://github.com/anonimov94/linumeRT.git ~/linumeRT
   sudo bash ~/linumeRT/tools/vm/post-install-ctl.sh
   ```
   Skrypt: pakiety (`linuxcnc-uspace-dev`, `socat`), adres `10.77.0.10/24` na karcie 2 (NetworkManager albo
   ifupdown), DHCP na karcie 3, klon w `/opt/linumert` z venv (`--system-site-packages`, bo moduły `linuxcnc` i
   PyQt5 pochodzą z pakietów), `halcompile --install` dla `lrt_net`, `lrt_cia402`, `lrt_hardstop_home` oraz
   konfiguracje `config/plant/linumert_plant_xyz/*_vm.ini` z `[PLANT]IP = 10.77.0.20`.
3. Start (po §5): `linuxcnc /opt/linumert/config/plant/linumert_plant_xyz/linumert_plant_xyz_vm.ini`.

## 5. VM-B: Plant jako usługa
1. Instalacja nienadzorowana startuje sama (`create-vms.ps1 -Start`) i kończy się ekranem logowania (ok. 10–20 min).
2. Zaloguj się jako `linumert` i wpisz:
   ```bash
   git clone --depth 1 https://github.com/anonimov94/linumeRT.git ~/linumeRT
   sudo bash ~/linumeRT/tools/vm/post-install-plant.sh
   ```
   Skrypt: pakiety (Python, gcc, `socat`), adres `10.77.0.20/24` na karcie 2, DHCP na karcie 3, klon w
   `/opt/linumert`, venv z panelem (`.[panel]`), rdzeń C (`make -C plant/core shared`), `/etc/linumert/plant.yaml`
   (tryb `realtime`, LRT-NET na `10.77.0.20:47700`, panel na `0.0.0.0:8080`) i usługa `linumert-plant`
   (start przy rozruchu, restart po awarii, stan enkoderów w `/var/lib/linumert-plant`).
3. Adres host-only pokazuje ostatnia linia skryptu (`hostname -I`, zwykle `192.168.56.x`). Panel Plant w przeglądarce
   Windows: `http://192.168.56.x:8080/`. SSH: `ssh linumert@192.168.56.x`.
4. Polecenia usługi:
   ```bash
   systemctl status linumert-plant
   journalctl -u linumert-plant -f
   sudo systemctl restart linumert-plant
   ```
Panel nie ma logowania: sieć host-only widzi tylko Twój komputer, nie wystawiaj portu 8080 dalej.

## 6. Sprawdzenie łącza VM-A ↔ VM-B
Przy **zatrzymanym** LinuxCNC (jeden master naraz), w VM-A:
```bash
/opt/linumert/.venv/bin/python /opt/linumert/tools/vm/lrtnet_probe.py --host 10.77.0.20
```
Sonda wysyła ramki co 1 ms jak `lrt_net`, włącza napędy (cel CSP = pozycja aktualna, osie stoją) i na końcu je
wyłącza. Wynik `OK` = brak watchdoga E-4003 i < 1 % brakujących odpowiedzi. Kod wyjścia: 0 OK, 1 łącze nie w normie,
2 brak odpowiedzi (sprawdź `systemctl status linumert-plant` w VM-B i `ping 10.77.0.20` z VM-A).
Po pomiarze Plant zgłasza watchdog (brak ramek); LinuxCNC kasuje go przy włączeniu napędów.

## 7. Wrzeciono przez falownik (hy_vfd) między VM
`hy_vfd` w VM-A rozmawia z portem szeregowym; Plant w VM-B wystawia pseudoterminal. Most `socat`:
pty Plant ↔ TCP `10.77.0.20:47710` ↔ pty `/tmp/linumert-hy_vfd` w VM-A. Oba skrypty z opcją `--vfd`:
```bash
sudo bash ~/linumeRT/tools/vm/post-install-plant.sh --vfd   # VM-B: plant.yaml z vfd: i usługa linumert-vfd-bridge
sudo bash ~/linumeRT/tools/vm/post-install-ctl.sh --vfd     # VM-A: usługa linumert-vfd-link
```
Usługi uruchamiają dokładnie te polecenia (test: tests/test_vm_link.py):
```bash
# VM-B (linumert-vfd-bridge)
/usr/bin/socat TCP-LISTEN:47710,bind=10.77.0.20,reuseaddr,fork FILE:/tmp/linumert-hy_vfd,raw,echo=0
# VM-A (linumert-vfd-link)
/usr/bin/socat PTY,link=/tmp/linumert-hy_vfd,raw,echo=0 TCP:10.77.0.20:47710
```
Start LinuxCNC z falownikiem: `linuxcnc /opt/linumert/config/plant/linumert_plant_xyz/linumert_plant_xyz_vfd_vm.ini`.
Modbus TCP dla `mb2hal` (bez mostu): `10.77.0.20:1502`.

## 8. Czas rzeczywisty w VM
- VM nie daje prawdziwego RT, nawet z jądrem PREEMPT_RT z obrazu LinuxCNC: hiperwizor wywłaszcza całą VM.
  Wątek servo LinuxCNC (1 ms) w VM-A ma rozrzut rzędu ms i pojedyncze przerwy po kilkadziesiąt ms.
  `latency-histogram` w VM-A pokazuje to od razu; tych liczb nie przenoś na prawdziwy komputer sterujący.
- Plant pracuje ramkowo: każdy krok modelu wyzwala ramka LinuxCNC, a krok liczy się z `time_ns` ramki, więc rozrzut
  odbioru nie psuje dynamiki osi (tryb `realtime`, docs/PLANT.md §2). Ograniczenie: przerwa między ramkami
  dłuższa niż `watchdog_ms` (50 ms) to watchdog E-4003, czyli napędy w stan błędu, tak jak w prawdziwej magistrali.
- Pomiary na localhost (sesja 025, Plant `realtime` + `lrtnet_probe.py`, 3000 ramek co 1 ms, przekaźnik UDP
  zamiast `tc netem`, którego nie ma w środowisku agenta):

  | Łącze | RTT p50 / p99 [ms] | Okres wysyłki p99 [ms] | Utracone / spóźnione | Watchdog |
  |---|---|---|---|---|
  | bez opóźnienia | 0,4 / 1,0 | 1,2 | 0 / 0 | nie |
  | 5 ms w każdą stronę | 11,1 / 13,2 | 1,3 | 0 / 0 | nie |
  | 20 ms w każdą stronę | 41,1 / 42,6 | 1,2 | 0 / 0 | nie |
  | 5 ± 2 ms (zmiana kolejności) | 11,2 / 15,6 | 1,3 | ok. 1/3 ramek | nie |
  | zawieszenie mastera 120 ms | — | — | — | **tak** (E-4003) |

  Stałe opóźnienie nie szkodzi. Rozrzut większy niż cykl zmienia kolejność ramek: starsza ramka jest
  odrzucana jako spóźniona (bez kroku), Plant pracuje dalej. Sieć wewnętrzna VirtualBoxa na jednym hoście
  kolejności nie zmienia; w VM-A spodziewaj się raczej przerw (zawieszeń) niż przestawień.
- Restart LinuxCNC przy działającej usłudze Plant: `lrt_net` numeruje ramki od 1, a Plant po przerwie dłuższej niż
  `watchdog_ms` przyjmuje nową numerację (sesja 025, wcześniej ramki nowej sesji odrzucał jako spóźnione).
- Jeśli w VM-A watchdog zadziała w czasie pracy: zamknij inne programy na hoście, daj VM-A 4 rdzenie i plan
  zasilania „Wysoka wydajność”; w ostateczności zwiększ `watchdog_ms` w `/etc/linumert/plant.yaml`
  (np. 100) i `sudo systemctl restart linumert-plant` (zmiana znika po ponownym uruchomieniu skryptu).

## 9. Wydajność
- VM-A: 4 vCPU, 4 GB RAM, grafika VMSVGA 128 MB; VM-B: 2 vCPU, 2 GB, bez pulpitu (panel w przeglądarce hosta).
- Parawirtualizacja KVM w obu VM (lepszy zegar gościa), dyski VDI dynamiczne.
- Widok 3D ekranu i panelu jest ograniczony do 30 FPS; w VM bez akceleracji 3D to wciąż spore obciążenie CPU.

## 10. Do sprawdzenia ręcznie (właściciel)
1. `create-vms.ps1` na Windows z VirtualBox 7 (obie VM, karty 1–3, sumy ISO).
2. Instalacja nienadzorowana VM-B z `preseed-plant.cfg`: pola `@@VBOX_INSERT_…@@` VirtualBoxa, logowanie, sudo.
3. `post-install-ctl.sh` na obrazie LinuxCNC 2.9 (NetworkManager, `halcompile --install`), start `*_vm.ini`.
4. `lrtnet_probe.py` z VM-A (§6) i wynik w tabeli w `docs/raporty/G1.md` (sesja 026).
Błąd: zgłoszenie na GitHubie z poleceniem i komunikatem; poprawi go następna sesja.

## 11. Parametry (`tools/vm/vm.conf`)
Jedno źródło wartości dla skryptów i tej instrukcji (zgodność: tests/test_vm_scripts.py).

| Klucz | Wartość | Znaczenie |
|---|---|---|
| `CTL_NAME` | `linumert-ctl` | nazwa VM-A |
| `CTL_CPUS` | `4` | vCPU VM-A |
| `CTL_RAM_MB` | `4096` | RAM VM-A [MB] |
| `CTL_DISK_MB` | `30000` | dysk VM-A [MB] |
| `CTL_VRAM_MB` | `128` | pamięć grafiki VM-A [MB] |
| `CTL_HOSTNAME` | `linumert-ctl` | nazwa hosta VM-A |
| `PLANT_NAME` | `linumert-plant` | nazwa VM-B |
| `PLANT_CPUS` | `2` | vCPU VM-B |
| `PLANT_RAM_MB` | `2048` | RAM VM-B [MB] |
| `PLANT_DISK_MB` | `12000` | dysk VM-B [MB] |
| `PLANT_VRAM_MB` | `16` | pamięć grafiki VM-B [MB] |
| `PLANT_HOSTNAME` | `linumert-plant` | nazwa hosta VM-B |
| `LRTNET_NAME` | `lrtnet` | sieć wewnętrzna VirtualBox |
| `LRTNET_PREFIX` | `24` | maska sieci lrtnet |
| `LRTNET_CTL_IP` | `10.77.0.10` | VM-A w lrtnet |
| `LRTNET_PLANT_IP` | `10.77.0.20` | VM-B w lrtnet (`[PLANT]IP` w `*_vm.ini`) |
| `LRTNET_PORT` | `47700` | LRT-NET UDP |
| `PANEL_PORT` | `8080` | panel Plant |
| `VFD_BRIDGE_PORT` | `47710` | most falownika TCP |
| `VFD_DEVICE` | `/tmp/linumert-hy_vfd` | pty dla `hy_vfd` (`[VFD]DEVICE`) |
| `VM_USER` | `linumert` | użytkownik w obu VM |
| `REPO_URL` | `https://github.com/anonimov94/linumeRT.git` | źródło klonu |
| `REPO_DIR` | `/opt/linumert` | katalog repozytorium w VM |
