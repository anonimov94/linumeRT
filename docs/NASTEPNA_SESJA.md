# Przekazanie do następnej sesji

Model-Author: Codex · 2026-10-17

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
