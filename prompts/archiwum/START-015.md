# Prompt startowy: sesja 015 (Plant: bazowanie po rozruchu)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji (Claude lub Codex). Stan opisuje koniec sesji 014.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md, prompts/LOCK (jeśli istnieje) oraz prompts/sesja-015.md (REQ-VM-07).
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`; GraphQL jest zablokowany).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego pusha.
4. Weź blokadę: `prompts/LOCK` = `sesja 015 · <UTC> · <model>`; ustaw `Tura:` na „w toku”.

## Stan (po sesji 014)
- #4 i #5 są w main. Otwarte: #3 (Codex), #6, #7, #8, #9, #10, #11 (013) i PR sesji 014 (`wip/sesja-014`,
  zbudowany na #11). Utwórz `wip/sesja-015` z `origin/wip/sesja-014` (albo z `main`, jeśli PR 014 jest
  scalony); czego brakuje, czytaj przez `git show origin/wip/sesja-NNN:<ścieżka>` i zapisz w dzienniku.
- Dostępne API C: `lrt_machine_*` (machine.h: konfiguracja kluczami, krok, osie, gantry, zderzaki,
  krańcówki i czujniki bazowe ze zdarzeniami `LIMIT_TRIP`/`HOME_SENSOR`, impuls indeksu z licznikiem i
  położeniem zatrzaśniętym `lrt_machine_index_latch`, E-STOP, sonda), `lrt_drive_*` (tryb 6 jeszcze
  zwraca `LRT_DRIVE_ERR_UNSUPPORTED`; obiekty 6098h/6099h/609Ah tylko przechowywane), `lrt_axis_*`.
  Python: `linumert_plant.build_machine.build_machine(yaml)` → `MachineModel`,
  `linumert_plant.core_binding.PlantMachine(model)` (ctypes; `enable_all`, `move`, `set_joint_target`,
  `input(name)`, `events()`, `tool_tip()`), CLI `python -m plant machine build <yaml> [--run]`.
- Pozycja startowa osi = środek soft limits (`joint.J.initial`); sesja 015 dodaje losową z ziarnem
  albo ze stanu i enkoder absolutny. Indeks nie ma wejścia w machine.yaml (API: licznik i zatrzask).
- Zalecane kroki czasu: serwa 1 ms, krokowiec bez sprzężenia ≤ 100 µs. Drgania styków (`debounce_ms`)
  trwają po każdym przełączeniu — testy odczytują wejście po kilku ms.
- roboCODE to osobny projekt na przyszły rok. Nie dotykać.

## Zasady
- CLAUDE.md wygrywa z promptem sesji. Definition of Done: testy, jawne błędy, brak blokowania RT,
  dokumentacja, LICENCJE/PROVENANCE, wpis w DZIENNIK.md i prompts/DONE.md. Testy REQ z `# REQ-VM-07`.
- Małe kroki; po każdym commit i push na wip/sesja-015 (`git push -u origin wip/sesja-015`). Własnych PR-ów
  nie scalasz (wyjątek D25: autokontrola z adnotacją). `Model-Author: Claude|Codex`.
- ruff (line-length 100, `zip(..., strict=...)`), pytest z `PYTHONPATH=core`, `make test-c`.
- W Git Bash heredoc z `\n` w kodzie Pythona potrafi się rozwinąć — edycje kodu rób narzędziem Edit/Write.

## ZAWSZE KOŃCZ PRACĘ
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone.
2. Wpis `## 015 — Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd` w DZIENNIK.md
   i linia w DONE.md.
3. Zaktualizuj „Stan” w docs/PROMPT_NOWEJ_SESJI.md, `Tura:` w NASTEPNA_SESJA.md (oddana), zwolnij LOCK.
4. Zostaw drugiemu modelowi konkretne zlecenia.
5. Użytkownikowi: co powstało, link do PR-a, jeden następny krok (sesja 016).
