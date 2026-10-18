# Prompt startowy: sesja 014 (Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji (Claude lub Codex). Stan opisuje koniec sesji 013.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md, prompts/LOCK oraz prompts/sesja-014.md (REQ-VM-02…05).
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`; GraphQL jest zablokowany).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego pusha.
4. Weź blokadę: `prompts/LOCK` = `sesja 014 · <UTC> · <model>`; ustaw `Tura:` na „w toku”.

## Stan (po sesji 013)
- Kolejność scalania: #4, #5–#9, #10, PR sesji 013 (biblioteka napędów). Utwórz `wip/sesja-014` z
  najnowszej gałęzi zawierającej #8 (machine.yaml), #10 (napęd) i sesję 013; jeśli czegoś brakuje na main,
  czytaj przez `git show origin/wip/sesja-NNN:<ścieżka>` i zapisz w dzienniku, co wzięto.
- Dostępne API: `lrt_axis_*` (axis.h: init, step, zderzaki, zdarzenia, `lrt_axis_set_live`),
  `lrt_drive_*` (drive.h), Python: `linumert_plant.drive_library.load_library()`, `resolve_instances()`
  (lista `drives:` z machine.yaml), `drive_template.to_c_params()` (pola `lrt_drive_params` i
  `lrt_axis_params`), `LiveParams` (zmiany live z dziennikiem).
- Brak: wiązania Pythona z rdzeniem C (do tej pory tylko narzędzie `plant/core/tools/check_params.c`),
  modelu hamulca, `machine.c`. Sesja 014 buduje `plant/core/machine.c` i `plant/server/build_machine.py`.
- Zalecane kroki czasu: serwa 1 ms, krokowiec bez sprzężenia ≤ 100 µs.
- roboCODE to osobny projekt na przyszły rok. Nie dotykać.

## Zasady
- CLAUDE.md wygrywa z promptem sesji. Definition of Done: testy, jawne błędy, brak blokowania RT,
  dokumentacja, LICENCJE/PROVENANCE, wpis w DZIENNIK.md i prompts/DONE.md. Testy REQ z `# REQ-VM-NN`.
- Małe kroki; po każdym commit i push na wip/sesja-014 (`git push -u origin wip/sesja-014`). Własnych PR-ów
  nie scalasz (wyjątek D25: autokontrola z adnotacją). `Model-Author: Claude|Codex`.
- ruff (line-length 100, `zip(..., strict=...)`), pytest z `PYTHONPATH=core`, `make test-c`.

## ZAWSZE KOŃCZ PRACĘ
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone.
2. Wpis `## 014 — Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O` w DZIENNIK.md i linia w DONE.md.
3. Zaktualizuj „Stan” w docs/PROMPT_NOWEJ_SESJI.md, `Tura:` w NASTEPNA_SESJA.md (oddana), zwolnij LOCK.
4. Zostaw drugiemu modelowi konkretne zlecenia.
5. Użytkownikowi: co powstało, link do PR-a, jeden następny krok (sesja 015: bazowanie po rozruchu).
