# Uruchomienie symulatora linumeRT (LinuxCNC 2.9 + QtDragon)

Model-Author: Claude · sesja 004 · 2026-10-18

Konfiguracja: `config/sim/linumert_xyz/linumert_xyz.ini` (trivkins, X 0..600, Y 0..400,
Z −120..0 mm, `sim_spindle`, bazowanie na symulowanych krańcówkach, kontrakt `docs/HAL_KONTRAKT.md`).

## Linux z podmanem (laptop właściciela, zalecane)
```
tools/dev/linuxcnc-gui.sh linuxcnc /work/config/sim/linumert_xyz/linumert_xyz.ini
```
Pierwsze uruchomienie buduje obraz `linumert-cnc:bookworm-4` (Debian 12, pakiety linuxcnc.org
2.9-uspace). Okno trafia na pulpit gospodarza przez X11/Xwayland. Bez argumentów skrypt
uruchamia przykładowy QtDragon z LinuxCNC.

## WSL (Windows 11, WSLg)
1. Dystrybucja Debian 12: `wsl --install -d Debian`.
2. Repozytorium linuxcnc.org (klucz `3CB9FD148F374FEF`, odcisk `EEDD0D29F81DCAA0D258661F3CB9FD148F374FEF`):
   `deb [signed-by=/usr/share/keyrings/linuxcnc.gpg] http://www.linuxcnc.org/ bookworm base 2.9-uspace`,
   potem `sudo apt install linuxcnc-uspace python3-pyqt5.qsci python3-pyqt5.qtopengl python3-opengl`.
3. `linuxcnc config/sim/linumert_xyz/linumert_xyz.ini` z katalogu repo.
Budowa RIP ze źródeł: `tools/ci/build-linuxcnc.sh` (PR #3, sesja 003).

## Typowe problemy
| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| `shmget(...): Permission denied`, `rtapi init failed` | `rtapi_app` z setuid root w kontenerze bez roota | obraz zdejmuje setuid (`linuxcnc-gui.sh`), uruchamiaj przez skrypt |
| `Refusing to run as root without fallback UID` | LinuxCNC uruchomiony jako root | uruchamiaj jako zwykły użytkownik (`--userns=keep-id`) |
| okno się nie pokazuje | brak `DISPLAY`/`XAUTHORITY` | uruchamiaj z sesji graficznej; Wayland potrzebuje Xwayland |
| ostrzeżenia `python3-gst1.0`, `python3-poppler-qt5`, D-Bus | opcjonalne dźwięki, PDF, powiadomienia | można pominąć |
| po M6 program czeka | ręczna zmiana narzędzia | potwierdź okno w ekranie |
| osie nie jadą | maszyna niezbazowana albo E-STOP | F1 (E-STOP), F2 (włącz), „Home all” |
