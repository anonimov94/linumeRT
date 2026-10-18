# Przekazanie po sesji 003

Model-Author: Codex · 2026-10-18

## Repozytorium i zasady

Repo: https://github.com/anonimov94/linumeRT — PR sesji 003: #3.
Przed pracą sprawdź jego stan, pobierz main i sprawdź czystość checkoutu.
Windows: `C:/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`.
WSL: `/mnt/c/Users/pc/Documents/PythonProjects/linumeRT/.collaboration/linumeRT`.
Katalog nadrzędny zawiera starszą kopię dokumentacji; nie pracuj w nim.

Claude niedostępny do odwołania. Codex pracuje samodzielnie: PR, jawna
autokontrola i testy, merge po sukcesie. Po każdym ukończonym kroku commit
i push, zawsze `Model-Author: Codex`. Nie nazywaj autokontroli niezależnym review.

## Działające środowisko

LinuxCNC gałąź 2.9, SHA `a33293f46575c809e082e0806e79ab996f982513`, RIP/uspace
w `/home/pc/.cache/linuxcnc-2.9`. D20 przyjęta. Pełna budowa po make clean: 50 s.
Raport: `docs/raporty/SPIKE_LINUXCNC.md`; zrzut: `spike_qtdragon.png` obok niego.
Kod upstream niezmieniony. Ubuntu 24.04 WSL2 to środowisko dev non-realtime;
docelowy system nadal Debian 12. NIEZWERYFIKOWANE NA SPRZĘCIE.

```bash
bash tools/ci/build-linuxcnc.sh
.venv/bin/python tools/agent_tests/run.py --model Codex --linuxcnc
make test-linuxcnc PYTHON=.venv/bin/python
```

Venv używa systemowych pakietów GUI. Jeśli brak zależności:
`bash tools/ci/build-linuxcnc.sh --install-deps` (apt wymaga administratora).
WSL nie ma sudo bez hasła; zależności instalowano przez `wsl -u root`.
Nie uruchamiaj builda ani GUI jako root. Nie wykonano `make setuid`.

Testy: import, bazowanie trzech osi, ruch MDI i położenie końcowe, gotowość
QtDragon oraz poprawne zamknięcie okna. API statusu upstream nie toleruje
zbyt wczesnego pierwszego poll; fixture czeka na udany osobny proces próbny.
Testowa preferencja shutdown_check=False omija dialog potwierdzenia zamknięcia.

Workflow `linuxcnc.yml`: PR narzędzi integracyjnych, ręczny, tygodniowy;
cache budowy i artefakty dowodowe. JSON/logi lokalne: `state/test-runs/`.

## VNC

W tej sesji uruchomiono wspólny launcher na localhost:5911, DISPLAY=:11,
XAUTHORITY=/tmp/linumert-vnc.rSYjwuGM/Xauthority. To dane bieżącego procesu,
nie konfiguracja trwała. Sprawdź procesy przed uruchomieniem kolejnego pulpitu.
Po restarcie użyj `tools/agent_tests/Start-Tests.ps1 -Model Codex -DisplayNumber 11`.
Pokazuj także testy integracyjne w terminalu VNC. Nie zabijaj obcych sesji.

## Następne zadanie — sesja 004

Przeczytaj AGENTS.md, CLAUDE.md, DECYZJE, trzy ostatnie wpisy DZIENNIK i
`prompts/sesja-004.md`. Zbuduj własną konfigurację `config/sim/linumert_xyz/`
na bazie przykładów QtDragon: XYZ w mm, kontrakt D05, narzędzia i programy
testowe, dokumentacja HAL i WSL. Rejestruj pochodzenie upstream i licencje.
Wykorzystaj istniejący RIP i wspólny runner; sesja 003 nie tworzy docelowej
konfiguracji ani Plant. Uporządkuj ścieżki PROGRAM_PREFIX/NGCGUI, które
w przykładzie upstream dają ostrzeżenia. Opcjonalny podgląd PDF nie jest testowany.

Historyczną blokadę Claude 001 przejęto jawnie w dzienniku sesji 003.
Przed następną pracą sprawdź `prompts/LOCK`; nie uruchamiaj równoległych LinuxCNC.

## Stan zatrzymania na prośbę właściciela

Praca zatrzymana 2026-10-18. Sesja 003 NIE jest jeszcze wpisana do DONE.
Najpierw dokończ sesję 003: sprawdź aktualne kontrole PR #3, wykonaj autokontrolę
końcowego diffu, scal dopiero po sukcesie, dopisz DONE i zwolnij blokadę.
Dopiero potem przejdź do sesji 004 opisanej wyżej.
Ostatni lokalny runner: PASS, 47 testów bazowych + 2 integracyjne, lint i diff OK.
Raport: `state/test-runs/20261018T060319.515034Z-Codex/report.json`.
Pełna przebudowa po make clean: 50 s. CI Python zielone; CI LinuxCNC nadal
trwało przy zatrzymaniu. PR pozostaje draft, bez merge. Pulpit VNC pozostawiony.
