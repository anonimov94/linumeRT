# Przekazanie do następnej sesji

Prompt startowy i stan bieżący: `docs/PROMPT_NOWEJ_SESJI.md` (aktualizować na końcu każdej sesji).

Model-Author: Codex · 2026-10-17

Tura: Claude · od 2026-10-18 · stan: w toku (sesja 013, dokończenie)

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

1. **Wprowadź sesję 013 do git:** utwórz `wip/sesja-013` z `origin/wip/sesja-012` (albo z `main`, jeśli #10
   jest scalony), rozpakuj paczkę `linumert-sesja-013.zip` w korzeniu repo (ścieżki względne od korzenia),
   `git status`, `make lint test test-c`, commit `sesja 013: biblioteka napędów wirtualnych`
   z `Model-Author: Claude`, push i PR z bazą `main` (w opisie: zależność od #10 i #9).
2. **Po scaleniu #6:** `pytest tests/test_plant_core.py -rs` — test spójności tablicy awarii z katalogiem
   alarmów ma przejść bez pominięcia.
3. **Po scaleniu #8:** podłącz `drive_library.resolve_instances()` do ładowarki `machine.yaml` (sekcja
   `drives:`) i sprawdź, czy przykładowe maszyny z sesji 010 używają id szablonów z biblioteki.
4. **Przegląd niezależny:** wartości 7 szablonów (przykładowe), reguły między polami w
   `drive_template._cross_checks`, rdzeń C `lrt_axis_set_live` (axis.c) i narzędzie `plant/core/tools/check_params.c`.
5. Następna sesja Claude: 014 (`prompts/START-014.md`).

