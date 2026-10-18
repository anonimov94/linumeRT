# Prompt startowy: sesja 017 (komponent HAL lrt_net)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji (Claude lub Codex). Stan opisuje koniec sesji 016.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md, prompts/LOCK (jeśli istnieje) oraz prompts/sesja-017.md.
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego pusha.
4. Weź blokadę: `prompts/LOCK` = `<model> · sesja 017 · <UTC> · <opis>`; ustaw `Tura:` na „w toku”.

## Stan (po sesji 016)
- PR #17 (016, serwer LRT-NET) na gałęzi #13 (015). Jeśli nie scalone, utwórz `wip/sesja-017`
  z `origin/wip/sesja-016`.
- Gotowe: `linumert_plant.lrtnet` (ramki v1, docs/PLANT.md §3 + „Realizacja”), `server.PlantServer`
  (`handle`, `serve`, watchdog E-4003 = awaria napędu 8130h), `python -m linumert_plant serve ...`,
  master testowy `plant/server/test_master.py` (wzór sekwencji CiA 402 i profilu dla `lrt_cia402`).
- Kolejność bloków osi w ramce = napędy z `drives:` bez wrzeciona (gantry = dwa jointy).
- Do decyzji w 017: zatrzask indeksu enkodera (pole w ramce v2 albo `index-enable` w lrt_net) —
  wpis sesji 016 w DECYZJE pkt (9). Wrzeciono w ramce nieużywane (sesja 021).
- Test integracyjny z LinuxCNC wymaga środowiska Codexa (WSL, RIP 2.9) — zleć go w „Dla Codex:”,
  jeśli sam go nie uruchomisz. roboCODE to osobny projekt. Nie dotykać.

## Zasady
- CLAUDE.md wygrywa z promptem sesji. RT: bez alokacji, UDP nieblokująco, bez logowania (CLAUDE.md §5).
- Małe kroki; po każdym commit i push na wip/sesja-017; draft PR po pierwszym kroku.
  Własnych PR-ów nie scalasz bez przeglądu. `Model-Author: Claude|Codex`.
- ruff (line-length 100), pytest z `PYTHONPATH=core`, `make test-c`. W WSL: `.venv/bin/python`.
- W Git Bash heredoc bywa zawodny; Python w Windows zapisuje CRLF — używaj `newline="\n"`.

## ZAWSZE KOŃCZ PRACĘ
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone.
2. Wpis `## 017 — Komponent HAL lrt_net` w DZIENNIK.md i linia w DONE.md.
3. Zaktualizuj „Stan” w docs/PROMPT_NOWEJ_SESJI.md, `Tura:` w NASTEPNA_SESJA.md (oddana), zwolnij LOCK.
4. Zostaw drugiemu modelowi konkretne zlecenia; użytkownikowi: co powstało, link do PR, jeden następny krok.
