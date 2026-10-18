# Przekazanie do następnej sesji

Prompt startowy i stan bieżący: `docs/PROMPT_NOWEJ_SESJI.md` (aktualizować na końcu każdej sesji).

Model-Author: Codex · 2026-10-17

Tura: Claude · od 2026-10-18 · stan: w toku (sesja 014 na `wip/sesja-014`)

## Katalog i Git

Repo: https://github.com/anonimov94/linumeRT
Aktualny checkout Windows:
`C:/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`
WSL: `/mnt/c/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`.
Katalog nadrzędny jest starszą kopią dokumentacji bez własnego repo; nie pracuj w nim.

PR #1: zasady współpracy, scalony. PR #2: paczka testowa z VNC, sprawdź aktualny
stan przed rozpoczęciem. Dawne gałęzie sesji 001 i 002 są już zawarte w main.

## Zasady użytkownika

Claude jest niedostępny do odwołania. Codex kontynuuje samodzielnie przez PR,
autokontrolę i testy; nie czeka na Claude. Oznaczaj autorstwo modelu w commitach,
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

## Następne zadanie — sesja 003

Przeczytaj AGENTS.md, CLAUDE.md, DECYZJE, trzy ostatnie wpisy DZIENNIK oraz
`prompts/sesja-003.md`. Zrealizuj spike LinuxCNC 2.9 zgodnie z promptem:
skrypt budowania RIP/uspace, test importu i konfiguracji sim, próba QtDragon
pod Xvfb z raportem, workflow ręczny/tygodniowy i decyzja D20 na podstawie
rzeczywistych wyników. Pokazuj postęp w terminalu VNC użytkownika.

LinuxCNC nie został jeszcze zbudowany ani uruchomiony w tej sesji.
Nie wpisuj 003 do DONE przed spełnieniem kryteriów. Ubuntu WSL jest środowiskiem
deweloperskim; docelowy system projektu nadal Debian 12 + LinuxCNC 2.9.
Historyczny prompts/LOCK wskazuje sesję Claude 001; właściciel potwierdził,
że Claude nie pracuje. Przejmij blokadę jawnie do swojej sesji, zachowując ślad
w dzienniku. Nie instaluj ani nie uruchamiaj sterowania rzeczywistą maszyną.

## Zlecenia po sesji 011 (Model-Author: Claude → Codex)

1. **Przegląd i scalenie:** kolejność #4 (protokół), potem niezależne #5, #6, #7, #8 i #9 (rdzeń osi
   Plant w C; w opisie PR SHA do przeglądu). Konflikty tylko w plikach dziennikowych (DZIENNIK, DECYZJE,
   DONE: zostaw wszystkie wpisy), `docs/PROMPT_NOWEJ_SESJI.md` (add/add: weź wersję z #9) i `ci.yml`
   (zachowaj krok `make test-c`).
2. **Sprawdź #9 w WSL Debian 12** (po zakończeniu zadania z #3): `make -C plant/core test` oraz
   `cc -std=c11 -g -O1 -fsanitize=address,undefined -fno-sanitize-recover=undefined plant/core/axis.c
   plant/core/tests/test_axis.c -lm -o /tmp/t && /tmp/t`; oczekiwane 23 testy `ok`, brak raportów
   sanitizerów. Zgłoś wynik komentarzem do PR (model + SHA).
3. **Czerwone CI w #3** pozostaje u Ciebie (spec w komentarzu do #3). Bez zmian.
4. **Dla Claude, następna sesja:** 012 (napęd CiA 402 i krokowce w C) buduje na `plant/core/axis.h`:
   bazuj na `wip/sesja-011` albo na `main` po scaleniu #9.

## Zlecenia po sesji 013 (Model-Author: Claude → Codex)

1. **Przegląd PR sesji 013** (gałąź `wip/sesja-013`, SHA w opisie PR). PR zawiera scalone `wip/sesja-010`
   (#8) oraz commity #9/#10 — scalaj po nich albo razem z nimi. Uwaga: dotyka kodu #8
   (`core/linumert/machine/schema.py`: `id` jako alias `name`; przykładowe maszyny używają szablonów
   biblioteki; jedna nazwa szablonu w `tests/test_machine_config.py`).
2. **Przejrzyj niezależnie:** wartości 7 szablonów (przykładowe), `drive_template._cross_checks`,
   `machine_drives.py` (zgodność linear/rotary), `lrt_drive_set_live` i `live.c`, fizyczny test C
   `test_drive_live_heavier_load_lowers_max_acceleration`.
3. **Po scaleniu #6:** `pytest tests/test_plant_core.py -rs` — test spójności tablicy awarii ma przejść bez skipu.
4. Następna sesja Claude: 014 (`prompts/START-014.md`).
