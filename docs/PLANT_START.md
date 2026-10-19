# Uruchomienie LinuxCNC z wirtualną obrabiarką Plant

Model-Author: Claude · sesja 018 · 2026-10-18

Konfiguracja `config/plant/linumert_plant_xyz/` (maszyna `config/machines/mill_servo_table.yaml`:
X, portal Y na dwóch napędach, Z; serwonapędy CiA 402; krańcówki NC, E-STOP NC, sonda).
Ekran: `linumert` (kopia QtDragon). Połączenie: komponenty HAL `lrt_net` + `lrt_cia402`
(docs/HAL_KONTRAKT.md), protokół LRT-NET v1 po UDP (docs/PLANT.md §3).

## Lokalnie (laptop, podman, Debian 12 w kontenerze)
1. Raz: obraz z zależnościami budowy i RIP LinuxCNC 2.9:
   ```
   podman build -t linumert-rip:bookworm -f - tools/ci <<'X'
   FROM debian:bookworm
   COPY build-linuxcnc.sh /tmp/build-linuxcnc.sh
   RUN bash /tmp/build-linuxcnc.sh --install-deps && rm -rf /var/lib/apt/lists/*
   X
   mkdir -p ~/.cache/linumert/rip-home
   podman run --rm --userns=keep-id -e HOME=/home/rip -v ~/.cache/linumert/rip-home:/home/rip \
     -v "$PWD:/work" -w /work linumert-rip:bookworm bash tools/ci/build-linuxcnc.sh
   ```
2. Start: `tools/dev/plant-gui.sh` — buduje rdzeń Plant, instaluje `lrt_net`/`lrt_cia402` w RIP,
   uruchamia serwer Plant (`plant.yaml`, lockstep) i LinuxCNC z ekranem na pulpicie.
3. W ekranie: F1 (E-STOP reset), F2 (maszyna włączona), „Home all”. Osie startują z losowej
   pozycji (ziarno `seed` w plant.yaml) i bazują na krańcówkach wirtualnej maszyny.

## WSL lub VM
- Dwie maszyny VirtualBox (VM-A z LinuxCNC, VM-B z Plant jako usługą): [`VM.md`](VM.md), skrypty `tools/vm/`.
- Plant w VM-B: w `plant.yaml` `mode: realtime`, `network.listen: 0.0.0.0`; w INI `[PLANT]IP` =
  adres VM-B. LinuxCNC w VM-A z RIP (`tools/ci/build-linuxcnc.sh`) albo z pakietów
  (`linuxcnc-uspace-dev` dla `halcompile`).
- Komponenty: `halcompile --install hal/lrt_net.comp` (z `hal/lrt_net_proto.h` obok) i
  `halcompile --install hal/lrt_cia402.comp`.

## Testy
- Bez LinuxCNC: `pytest tests/test_plant_config.py tests/test_lrt_net_proto.py`.
- Z LinuxCNC RIP: `pytest -o addopts= -m linuxcnc tests/test_hal_lrt_net.py tests/test_plant_linuxcnc.py
  tests/test_plant_vfd_linuxcnc.py` (bazowanie z losowego startu, G1, błąd nadążania z Plant; wrzeciono
  przez prawdziwy hy_vfd: M3/M4/M5; razem ok. 3 min).
- Wariant z falownikiem na pulpicie: `VFD=1 tools/dev/plant-gui.sh` (`linumert_plant_xyz_vfd.ini`,
  `plant_vfd.yaml`).

## Ograniczenia (LRT-NET v1)
Bez indeksu enkodera (`HOME_USE_INDEX`), bez limitu momentu 6072h w ramce, wrzeciono: w wariancie
domyślnym `sim_spindle` w HAL, w wariancie `_vfd` falownik Plant przez hy_vfd (docs/PLANT.md §5a). Warianty bazowania: `config/plant/linumert_plant_xyz/bazowanie/`.
NIEZWERYFIKOWANE NA SPRZĘCIE.
