# tools

Narzedzia deweloperskie i skrypty: check_requirements.py (od sesji 024), tools/vm (maszyny wirtualne), tools/ci.

`lock.py` — blokady zasobów współdzielonych (`linuxcnc`, `wsl-build`) przy rzadkiej pracy równoległej modeli; zasady: `docs/WSPOLPRACA_MODELI.md` §2a.

`dev/debian-container.sh` — uruchamia polecenie w kontenerze Debian 12 (Podman/Docker) z repo jako /work; zob. `prompts/START-LAPTOP.md`.
