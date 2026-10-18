# Prompt startowy: sesja 013 (Plant: biblioteka napędów wirtualnych — szablony YAML)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji (Claude lub Codex). Stan opisuje koniec sesji 012.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md, prompts/LOCK oraz prompts/sesja-013.md (zakres i kryteria, REQ-VD-01…05).
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`; GraphQL jest zablokowany).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego pusha.
   Stan na koniec sesji 012: `Tura: Claude · stan: oddana`.
4. Weź blokadę: wpisz do prompts/LOCK `sesja 013 · <UTC> · <model>`; ustaw `Tura:` na „w toku”.

## Stan (2026-10-18)
- `main` = c71b4fa (stary). PR-y czekają na przegląd i scalenie przez Codexa w kolejności: #4 (protokół v2),
  #5 (006), #6 (007, katalog alarmów), #7 (009, docs/PLANT.md + LRT-NET v1), #8 (010, machine.yaml),
  #9 (011, rdzeń osi w C), #10 (012, napęd CiA 402 w C; zależy od #9). #3 (LinuxCNC CI) u Codexa.
- Sesja 013 buduje na `plant/core/drive.h` (#10) i `machine.yaml` (#8). Utwórz `wip/sesja-013` z
  `origin/wip/sesja-012` (albo z `main`, jeśli #10 jest już scalony); PR z bazą `main`, w opisie zależności.
  Jeśli #6/#7/#8 nie są na main, czytaj je przez `git show origin/wip/sesja-NNN:<ścieżka>`.
- Po scaleniach możliwe konflikty na końcu DZIENNIK.md, DECYZJE.md, prompts/DONE.md (zostaw wszystkie
  wpisy), docs/PROMPT_NOWEJ_SESJI.md (weź wersję z najnowszego PR) i ci.yml (zachowaj `make test-c`).
- roboCODE to osobny projekt na przyszły rok. Nie dotykać.

## Co dała sesja 012 (do wykorzystania)
- API: `lrt_drive_params_default(&p, typ)`, `lrt_drive_tune_servo`, `lrt_drive_params_check`, `lrt_drive_init`,
  `set_controlword`, `set_target_position`, `od_read/od_write`, `step(&d, &feedback, dt, &torque_cmd)`.
  Typy: SERVO_CSP, STEPPER_OPEN, STEPPER_CLOSED. Tablica awarii `LRT_DRIVE_FAULT_LIST` (603Fh + E-4200…4208).
- Szablony YAML w `plant/library/drives/` mają mapować na `lrt_drive_params` (wszystkie pola jawne, z
  walidacją i polskimi komunikatami błędów); wirtualny napęd = zawsze instancja szablonu (CLAUDE.md §5a).
- Uwaga: tłumienie krokowca ograniczone do 20 % amplitudy, ζ domyślnie 0,2; `tune_servo` ogranicza pasmo do
  0,15/dt; pomiar ma opóźnienie jednego kroku. Hamulca brak; bazowanie (tryb 6) odrzucane — sesja 015.
- Test spójności tablicy awarii z katalogiem alarmów jest pomijany, dopóki #6 nie wejdzie do main —
  po scaleniu #6 sprawdź, że przechodzi bez skipu.

## Zasady
- CLAUDE.md wygrywa z promptem sesji. Definition of Done: testy, jawne błędy, brak blokowania RT,
  dokumentacja, LICENCJE/PROVENANCE, wpis w DZIENNIK.md i prompts/DONE.md. Testy REQ-VD z `# REQ-VD-NN`.
- Małe kroki; po każdym commit i push na wip/sesja-013 (`git push -u origin wip/sesja-013`, śledzenie
  gałęzi wymagane przez hook końca sesji). Oszczędzaj tokeny.
- Własnych PR-ów nie scalasz (wyjątek D25: autokontrola z adnotacją, bez podawania jej za niezależny przegląd).
- `Model-Author: Claude|Codex` w commitach, PR, dzienniku. Sprzęt/LinuxCNC: `NIEZWERYFIKOWANE NA SPRZĘCIE`.
- ruff (line-length 100, `zip(..., strict=True)`), pytest z `PYTHONPATH=core`, `make test-c`.

## ZAWSZE KOŃCZ PRACĘ
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone.
2. Wpis `## 013 — Plant: biblioteka napędów wirtualnych` w DZIENNIK.md i linia w prompts/DONE.md.
3. Zaktualizuj „Stan” w docs/PROMPT_NOWEJ_SESJI.md, `Tura:` w NASTEPNA_SESJA.md (oddana), zwolnij LOCK.
4. Zostaw drugiemu modelowi konkretne zlecenia (co przejrzeć, scalić, zrobić dalej).
5. Użytkownikowi: co powstało, link do PR-a, jeden następny krok (sesja 014: kinematyka wielu osi).
