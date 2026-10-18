# tools

Narzędzia deweloperskie, CI i koordynacji pracy. Polecenia środowiska krok po kroku:
[`docs/NASTEPNA_SESJA.md`](../docs/NASTEPNA_SESJA.md) §4 i [`docs/PLANT_START.md`](../docs/PLANT_START.md).

| Ścieżka | Do czego |
|---|---|
| `dev/debian-container.sh` | dowolne polecenie w kontenerze Debian 12 (podman/docker albo rootfs) z repo jako `/work`; wyniki testów liczą się tylko z Debiana 12 (D27), np. `tools/dev/debian-container.sh make lint test test-c test-san` |
| `dev/wsl-test.sh` | testy zatwierdzonego HEAD gałęzi w WSL (Windows): świeży klon i venv w `~/linumert-test/<gałąź>`, `--linuxcnc` z blokadą `linuxcnc`; równoległe sesje (D33, `prompts/START-PODZIAL.md`) |
| `dev/plant-gui.sh` | LinuxCNC (RIP) + serwer Plant + ekran linumert w kontenerze, okno na pulpicie; `VFD=1` = wariant z hy_vfd; `HEADLESS=1 … CMD` = polecenie w gotowym środowisku |
| `dev/linuxcnc-gui.sh` | LinuxCNC 2.9 z pakietów linuxcnc.org (symulator `config/sim`) z oknem na pulpicie |
| `dev/zrzut_ekranu.py` | zrzut ekranu linumeRT pod Xvfb (raporty kamieni) |
| `dev/autozapis.sh` | opcjonalny autozapis pracy co 10 min (tylko gałęzie `wip/*` i `claude/*`) |
| `lock.py` | blokady zasobów współdzielonych (`linuxcnc`, `wsl-build`) przy pracy równoległej (D30, `WSPOLPRACA_MODELI.md` §2a) |
| `ci/` | skrypty CI: budowa i testy LinuxCNC 2.9 RIP (sesja 003, `build-linuxcnc.sh`, `test-linuxcnc.sh`) |
| `agent_tests/` | wspólna paczka testowa z raportem JSON i launcherem Windows ([README](agent_tests/README.md)) |
| `vm/` | pulpit VNC w WSL (`start-vnc.sh`); skrypty maszyn wirtualnych VM-A/VM-B w sesji 025 |
| `check_requirements.py` | (od sesji 024) kontrola znaczników REQ w testach względem macierzy |
