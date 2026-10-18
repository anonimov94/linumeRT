# Prompt startowy: sesja 016 (Plant: serwer LRT-NET)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji (Claude lub Codex). Stan opisuje koniec sesji 015.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md, prompts/LOCK (jeśli istnieje) oraz prompts/sesja-016.md.
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego pusha.
4. Weź blokadę: `prompts/LOCK` = `sesja 016 · <UTC> · <model>`; ustaw `Tura:` na „w toku”.

## Stan (po sesji 015)
- W main: sesje 001, 002, 006, 007, 009–014. PR sesji 015 (`wip/sesja-015`) czeka na przegląd Codexa;
  jeśli nie jest scalony, utwórz `wip/sesja-016` z `origin/wip/sesja-015`.
- Gotowe API: `linumert_plant.build_machine.build_machine(yaml, seed=, start="random"|"center")`,
  `core_binding.PlantMachine` (kroki, CiA 402: `set_controlword`, `set_target`, `position_actual`,
  `statusword`, `torque_actual`, `od_read/od_write`, `set_mode`, absolut i bateria, wejścia, zdarzenia),
  `plant_state.save_state/load_state/apply_state`, `homing_master.HomingMaster` (atrapa mastera:
  okres 1 ms, krok Plant 1 ms albo 100 µs dla krokowców — wzór pętli lockstep dla serwera).
- Do decyzji w 016/017: LRT-NET v1 nie ma pola zatrzasku indeksu enkodera; master w testach czyta
  licznik indeksu z Plant (`index_count`). Zaproponuj pole w ramce albo zapisz, że LinuxCNC dostanie
  indeks przez `index-enable` w lrt_net (sesja 017).
- Watchdog serwera (REQ z sesji-016): brak ramek > N ms → napędy w fault (E-4003 w katalogu).
- roboCODE to osobny projekt na przyszły rok. Nie dotykać.

## Zasady
- CLAUDE.md wygrywa z promptem sesji. Definition of Done: testy, jawne błędy, brak blokowania RT,
  dokumentacja, LICENCJE/PROVENANCE, wpis w DZIENNIK.md i prompts/DONE.md. Znaczniki `# REQ-…`.
- Małe kroki; po każdym commit i push na wip/sesja-016. Własnych PR-ów nie scalasz bez przeglądu
  (wyjątek D26 wariant b: autokontrola z adnotacją). `Model-Author: Claude|Codex`.
- ruff (line-length 100), pytest z `PYTHONPATH=core`, `make test-c`. W WSL: `.venv/bin/python`.
- W Git Bash heredoc bywa zawodny — skrypty edycji zapisuj do pliku i uruchamiaj.

## ZAWSZE KOŃCZ PRACĘ
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone.
2. Wpis `## 016 — Plant: serwer LRT-NET` w DZIENNIK.md i linia w DONE.md.
3. Zaktualizuj „Stan” w docs/PROMPT_NOWEJ_SESJI.md, `Tura:` w NASTEPNA_SESJA.md (oddana), zwolnij LOCK.
4. Zostaw drugiemu modelowi konkretne zlecenia.
5. Użytkownikowi: co powstało, link do PR-a, jeden następny krok (sesja 017).
