# Przekazanie do następnej sesji

Prompt startowy i stan bieżący: `docs/PROMPT_NOWEJ_SESJI.md` (aktualizować na końcu każdej sesji).

Model-Author: Codex · 2026-10-17

Tura: Claude · od 2026-10-18T14:59Z · stan: oddana (D31: sesje 004 → PR #24, 005 → PR #25; stos #18–#25 czeka na scalenie przez właściciela)

## Katalog i Git

Repo: https://github.com/anonimov94/linumeRT
Aktualny checkout Windows:
`C:/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`
WSL: `/mnt/c/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`.
Katalog nadrzędny jest starszą kopią dokumentacji bez własnego repo; nie pracuj w nim.

PR #1: zasady współpracy, scalony. PR #2: paczka testowa z VNC, sprawdź aktualny
stan przed rozpoczęciem. Dawne gałęzie sesji 001 i 002 są już zawarte w main.

## Zasady użytkownika

Modele pracują na zmianę (tura w linii `Tura:`). Gdy drugi model jest niedostępny,
pracuj samodzielnie przez PR, autokontrolę i testy (D26 wariant b); nie czekaj. Oznaczaj autorstwo modelu w commitach,
PR i dzienniku. Po każdym ukończonym kroku commit i push, bez czekania na koniec
sesji lub limit tokenów. Po ukończonym etapie przekaż prompt następnej sesji.

## Gotowa paczka testowa

`tools/agent_tests/README.md`: runner, launcher Windows i VNC.
Pełna próba Windows -> WSL -> VNC -> terminal -> raport: PASS, 47 testów, czysty lint.
Venv `.venv` z pytest/ruff istnieje w Ubuntu-24.04; python3-venv doinstalowany.
Uruchomienie: `tools/agent_tests/Start-Tests.ps1 -Model Codex -DisplayNumber 11`.
Jeśli ta sesja nadal działa, użyj istniejącego pulpitu zamiast uruchamiać drugi na
tym samym porcie. Podczas przekazania aktywny podgląd paczki używał portu 5911,
DISPLAY=:11 i XAUTHORITY=/tmp/linumert-vnc.atrgdu3j/Xauthority.
Te dane dotyczą bieżącego uruchomienia; po restarcie odczytaj wartości z nowego startu.
Starszy ręczny podgląd mógł pozostać na porcie 5909. Nie zabijaj obcych sesji.
Lokalne raporty `state/test-runs/` są ignorowane przez Git.

## Stan main — 2026-10-18 (Model-Author: Claude)

W `main` są sesje 001, 002, 006, 007, 009–016, 032, 039, 044 (PR #1, #2, #4–#17). PR #13–#17 scalił właściciel (GitHub, 2026-10-18 11:08–11:15Z) bez niezależnego przeglądu — przegląd wsteczny nadal należy do Codexa.
#6–#12 scalił Claude w `d53aa04` jako **autokontrolę, bez niezależnego przeglądu** (Codex był
niedostępny; D26 wariant b). Kontrole na stanie scalonym (WSL Ubuntu 24.04): ruff czysty,
pytest 248 OK bez pominięć (test tablicy awarii z katalogiem alarmów już nie jest pomijany),
`make test-c` OK (osie, napęd, maszyna). Konflikty były tylko w plikach dziennikowych.
Gałęzie `wip/sesja-007…014` są w main — można je usunąć po przeglądzie wstecznym.

Otwarte: **#3 (sesja 003, Codex)** i **#18** (Claude: walidacja pól ramki LRT-NET, brak sesji w DONE). Sesje 004, 005 i 008 nie są rozpoczęte.

## Zlecenia dla Codexa (kolejność)

1. **#3 — czerwony krok CI `LinuxCNC RIP smoke`.** Przyczyna (log runu 39102795987): oba testy
   przechodzą, błąd jest w *teardown* `test_qtdragon_screen` — proces QtDragon kończy się
   `Segmentation fault (core dumped)` po `WM_DELETE_WINDOW`, a fixture zabrania segfaultu w logu.
   Lokalnie (WSL Ubuntu 24.04, Xvfb) Claude nie odtworzył błędu: 7/7 przebiegów zielonych, więc to
   niestabilne zamykanie ekranu na runnerze. Ponowny run joba na GitHubie przeszedł (success) — crash jest niestabilny; diagnoza w komentarzu w #3.
   Najpierw `git merge origin/main` do `codex/sesja-003` (konflikty: DZIENNIK/DECYZJE/DONE —
   zostaw wszystkie wpisy; `ci.yml` — zachowaj `make test-c`).
2. **#3 — Debian 12** według specyfikacji w komentarzu do #3 z 06:30Z (dystrybucja WSL Debian 12,
   guard w `build-linuxcnc.sh`, job CI w `container: debian:bookworm`, D27 — zapis dopiero w #3, w DECYZJE.md kończy się na D26). To jest nadal
   wymaganie właściciela przed scaleniem #3.
3. **Przegląd wsteczny `d53aa04`** (sesje 007–014, kod Claude): uwagi z dawnych sekcji zleceń —
   `machine.c` (kinematyka `forward`, styki NC/NO, E-4207, E-STOP), presety `PRESET_CHAINS`
   w `build_machine.py` (znaki osi trunnion), wartości 7 szablonów napędów, model krokowca
   i mapowanie awarii w `drive.c`, `lrt_drive_set_live` i `live.c`. W WSL Debian 12:
   `make -C plant/core test shared` oraz ASan/UBSan na `axis.c`/`drive.c`/`machine.c`.
   Usterki zgłaszaj jako issue albo PR poprawkowy (model + SHA).
4. **Po scaleniu #3:** sesja 004 (konfiguracja sim 3 osie z QtDragon) i 005 (kopia ekranu
   QtDragon) — obszar Codexa (LinuxCNC, INI/HAL). 008 (bramka G0) dopiero po 003–005.
5. **Sesja 018** (z LinuxCNC): porównaj znaki A/B/C presetów trunnion z `xyzac-trt-kins` /
   `xyzbc-trt-kins` (`PlantMachine.tool_tip(workpiece=True)` vs układ detalu w LinuxCNC).


## Zlecenia po sesji 015 (Model-Author: Claude → Codex)

1. **Przegląd PR sesji 015** (`wip/sesja-015`, SHA w opisie PR; zbudowany na `main` z #6–#12).
   Przejrzyj niezależnie: `drive.c` — `establish_offset`, `homing_update` (fazy, zbocza, ramka
   po `homing_set_home`), krokowiec (`pos_offset` przy włączeniu), E-4211; `machine.c` —
   `drive_inputs`, `switch.S.drive`, start losowy; `homing_master.py` (zgodność z homemod).
2. **W WSL Debian 12** (po #3): `make -C plant/core test`, ASan/UBSan na `drive.c`/`machine.c`,
   `pytest tests/test_homing.py` oraz `pytest -o addopts= -m linuxcnc tests/test_hal_comps.py`
   (kopiuje moduł do `rtlib` RIP na czas testu i usuwa). Wynik komentarzem w PR (model + SHA).
3. **CI `linuxcnc`:** dołącz `tests/test_hal_comps.py` do joba LinuxCNC (marker już jest).
4. **Sesja 018:** scenariusze `home_switch`, `home_switch_index`, `home_hardstop`, `home_absolute`,
   `home_drive_internal`, `home_gantry_square` z prawdziwym homemod; INI według
   `hal/README.md` i wpisu sesji 015 w `docs/DECYZJE.md` (HOME_ABSOLUTE_ENCODER 1/2).

## Dla Codex: (2026-10-18, Claude po sesji 016)
0. **Przegląd wsteczny PR Claude** (już scalone przez właściciela; dawniej: przegląd i scalenie) w kolejności #13 → #17 (#17 jest na gałęzi #13), potem #14, #15,
   #16 (niezależne od siebie). Każdy: CI zielone, autor Claude; komentarz z modelem, SHA i wynikiem,
   potem merge commit albo lista usterek. Konflikty tylko w DZIENNIK/DECYZJE/DONE/PROMPT_NOWEJ_SESJI —
   zostaw wszystkie wpisy, DONE posortuj.
   - #17 lokalnie: `make test-c`, `pytest tests/test_lrtnet.py tests/test_plant_server.py`, potem ręcznie:
     `python -m linumert_plant serve config/machines/mill_servo_table.yaml --lockstep` i w drugim terminalu
     `python plant/server/test_master.py --axes 4 --distance 50000` (oczekiwane: utracone 0, spóźnione 0).
   - Proszę o próbę `--realtime` z masterem na drugim hoście/VM (jitter, watchdog) — wynik w „Dla Claude:”.

- (Claude, sesja laptop) Pkt 0 częściowo: autokontrola Claude #13–#17 w komentarzach PR — to nie zastępuje Twojego przeglądu. Kierunek indeksu `switch_index` (zawracanie) jest właściwy według właściciela: jazda za krańcówkę = uszkodzenie. Nowe pole `homing.latch: approach|release` (PR `claude/bazowanie-strategie`); w sesji 018 dobierz znak HOME_LATCH_VEL do strategii (release = znak przeciwny do SEARCH).

Następna sesja Claude: 017 (`prompts/START-017.md`, komponent HAL lrt_net) — od `wip/sesja-016`.

## Stan zatrzymania (Model-Author: Claude, sesja laptop)
- 2026-10-18T14:07Z A zrobione: Debian 12.15 (rootfs linuxcontainers, unshare -r + chroot; podman/docker brak na laptopie), `make lint test test-c test-san` na `6105649`: ruff czysty, pytest 436 OK (48 odznaczonych), testy C 29/59/20 OK, ASan/UBSan 29/59/20 bez usterek. Następny: B (przegląd wsteczny #13–#17).
- 2026-10-18T14:11Z B zrobione (autokontrola #13–#17, komentarze w PR; #17 lockstep: utracone 0, spóźnione 0); C pominięte (brak RIP). debian-container.sh działa bez podmana (rootfs w ~/.cache/linumert/debian12). Sesja oddana, LOCK zwolniony.
- 2026-10-18T14:17Z Strategie bazowania: `homing.latch` approach/release, PR #23 (bbb1e46), pytest 439 OK na Debianie 12. Sesja oddana, LOCK zwolniony.
- 2026-10-18T14:23Z Podman (6.1.3, crun) na laptopie; `make lint test test-c test-san` na `ab9a9ab`: ruff czysty, pytest 439 OK, C 29/59/20 OK, ASan/UBSan czysto. Następny: LinuxCNC z GUI w kontenerze (prośba właściciela).
- 2026-10-18T14:34Z `tools/dev/linuxcnc-gui.sh`: LinuxCNC 2.9.10 (linuxcnc.org, bookworm) + QtDragon sim w podmanie, okno na pulpicie laptopa (Xwayland). Działa. To pakiety, nie RIP z #3 — budowa nadal u Codexa. Blokada `linuxcnc` (lock.py) trzymana, dopóki GUI otwarte.
- 2026-10-18T14:47Z Sesja 004 (D31): config/sim/linumert_xyz działa w LinuxCNC 2.9.10 z QtDragon, bazowanie OK, pytest 443 OK + test linuxcnc. Następny: 005 (ekran linumert).
- 2026-10-18T14:59Z Sesja 005 (D31): screens/linumert działa w LinuxCNC 2.9.10, zrzut G0, pytest 443 OK + test linuxcnc. PR-y #18–#24 czekają na scalenie przez właściciela (klasyfikator odmówił samodzielnego scalenia własnych PR). Następny: 017 (lrt_net).
- 2026-10-18T15:36Z Sesje 017 (PR #27) i 018 (wip/sesja-018): LinuxCNC steruje Plant przez lrt_net; e2e test zielony. Uruchomienie z ekranem: tools/dev/plant-gui.sh. Następny: 019 (ograniczenia programowe, strefy, wyrocznia).
- 2026-10-18T15:47Z Sesja 019 (wip/sesja-019): wyrocznia REQ-VM-06, scenariusze z LinuxCNC zielone. Następny: 020 (magazyn narzędzi, kolizje).
- 2026-10-18T15:54Z Sesja 020 (wip/sesja-020): magazyn, pozycje, kolizje w Plant; 468 OK. Następny: 021 (wrzeciono VFD Modbus).
