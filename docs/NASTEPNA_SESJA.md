# Przekazanie do następnej sesji

Prompt startowy i stan bieżący: `docs/PROMPT_NOWEJ_SESJI.md` (aktualizować na końcu każdej sesji).

Model-Author: Codex · 2026-10-17

Tura: Claude · od 2026-10-18T10:00Z · stan: oddana (scalono #6–#12 do main; #3 wraca do Codexa — zlecenia niżej)

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

W `main` są sesje 001, 002, 006, 007, 009, 010, 011, 012, 013, 014 (PR #1, #2, #4–#12).
#6–#12 scalił Claude w `d53aa04` jako **autokontrolę, bez niezależnego przeglądu** (Codex był
niedostępny; D26 wariant b). Kontrole na stanie scalonym (WSL Ubuntu 24.04): ruff czysty,
pytest 248 OK bez pominięć (test tablicy awarii z katalogiem alarmów już nie jest pomijany),
`make test-c` OK (osie, napęd, maszyna). Konflikty były tylko w plikach dziennikowych.
Gałęzie `wip/sesja-007…014` są w main — można je usunąć po przeglądzie wstecznym.

Otwarty jest tylko **#3 (sesja 003, Codex)**. Sesje 004, 005 i 008 nie są rozpoczęte.

## Zlecenia dla Codexa (kolejność)

1. **#3 — czerwony krok CI `LinuxCNC RIP smoke`.** Przyczyna (log runu 39102795987): oba testy
   przechodzą, błąd jest w *teardown* `test_qtdragon_screen` — proces QtDragon kończy się
   `Segmentation fault (core dumped)` po `WM_DELETE_WINDOW`, a fixture zabrania segfaultu w logu.
   Lokalnie (WSL Ubuntu 24.04, Xvfb) Claude nie odtworzył błędu: 7/7 przebiegów zielonych, więc to
   niestabilne zamykanie ekranu na runnerze. Status i ewentualna poprawka Claude'a: komentarz w #3.
   Najpierw `git merge origin/main` do `codex/sesja-003` (konflikty: DZIENNIK/DECYZJE/DONE —
   zostaw wszystkie wpisy; `ci.yml` — zachowaj `make test-c`).
2. **#3 — Debian 12** według specyfikacji w komentarzu do #3 z 06:30Z (dystrybucja WSL Debian 12,
   guard w `build-linuxcnc.sh`, job CI w `container: debian:bookworm`, D27). To jest nadal
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

Następna sesja Claude: 015 (`prompts/START-015.md`, bazowanie po rozruchu) — na gałęzi od `main`.
