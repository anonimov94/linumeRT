# Prompt startowy: sesja 012 (Plant: emulacja napędów CiA 402 i krokowców)

Model-Author: Claude · 2026-10-18. Wklej na początku sesji (Claude lub Codex). Stan opisuje koniec sesji 011.

Pracujesz nad linumeRT (repo anonimov94/linumeRT, LinuxCNC 2.9 + QtDragon, Debian 12) razem z drugim
modelem. Pracujecie na zmianę, nigdy równolegle. Użytkownik jest użytkownikiem końcowym i ocenia po efektach.

## Start
1. Przeczytaj CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/DECYZJE.md, 3 ostatnie wpisy docs/DZIENNIK.md,
   docs/NASTEPNA_SESJA.md, prompts/LOCK oraz prompts/sesja-012.md (zakres i kryteria).
2. Sprawdź otwarte PR-y (REST: `gh api repos/anonimov94/linumeRT/pulls`; GraphQL jest zablokowany).
3. Linia `Tura:` w NASTEPNA_SESJA.md: nie wchodź w turę drugiego modelu młodszą niż 2 h od ostatniego
   pusha. Stan na koniec sesji 011: `Tura: Claude · stan: oddana`, więc można wchodzić.
4. Weź blokadę: wpisz do prompts/LOCK `sesja 012 · <UTC> · <model>`; ustaw `Tura:` na „w toku”.

## Stan (2026-10-18)
- `main` = c71b4fa (stary). Wszystkie PR-y są niezależne względem main i czekają na przegląd i scalenie
  przez Codexa: #4 (protokół v2, scala się pierwszy), #5 (006), #6 (007, katalog alarmów), #7 (009,
  docs/PLANT.md + LRT-NET v1), #8 (010, machine.yaml), #9 (011, rdzeń osi w C, CI zielone).
- #3 (sesja 003, LinuxCNC CI): u Codexa (Debian 12 w WSL, naprawa czerwonego CI).
- Sesja 012 buduje na `plant/core/axis.h` z #9. Utwórz `wip/sesja-012` z `origin/wip/sesja-011` (albo z
  `main`, jeśli #9 jest już scalony). Otwórz PR z bazą `main`; w opisie podaj zależność od #9.
- Katalog alarmów jest dopiero w #6 (`core/linumert/alarms/catalog.yaml`, E-4000..E-4210). Specyfikacja
  napędów jest w #7 (`docs/PLANT.md` §5, mapowanie błędów napędu na E-42xx). Żadnego z tych plików nie ma
  na main ani w #9. Przeczytaj je przez `git show origin/wip/sesja-006|007|009:<ścieżka>`.
- Po scaleniach możliwe konflikty na końcu DZIENNIK.md, DECYZJE.md, prompts/DONE.md (zostaw wszystkie
  wpisy), `docs/PROMPT_NOWEJ_SESJI.md` (add/add #8 i #9: weź wersję z #9) i `ci.yml` (zachowaj `make test-c`).
- roboCODE to osobny projekt na przyszły rok. Nie dotykać.

## Zakres sesji 012 (skrót; pełny: prompts/sesja-012.md)
`plant/core/drive.h/.c`: maszyna stanów CiA 402 (controlword/statusword, własna implementacja), tryb CSP
(P położenia + PI prędkości + FF, limit momentu, okno błędu nadążania → fault z kodem), krokowiec
open-loop (gubienie pełnych kroków wg krzywej pull-out, licznik zgubionych kroków, bez alarmu do mastera),
serwo krokowe (pętla zamknięta, alarm przy błędzie > progu), rozdzielczość i opcjonalny szum enkodera,
obiekty 6065h, 6072h, 6098h/6099h/609Ah. Napęd liczy `torque_cmd` dla `lrt_axis_step()`.
Testy C: przejścia stanów, fault przy przekroczeniu okna, gubienie kroków przy zbyt dużym przyspieszeniu
i brak gubienia przy rozsądnym. Nie wykonuj tu bazowania na zderzak ani szablonów YAML (sesje 013/015).

## Wskazówki z sesji 011
- Model osi: moment dostępny z krzywej, powyżej ostatniego punktu 0; ustaw krzywą do prędkości
  roboczych (przy 872 rad/s krzywa 300 rad/s obcina moment). Brak hamulca silnika: Z opada, gdy
  tarcie < grawitacja; hamulec dodaj w napędzie.
- Kryterium: każdy kod błędu napędu ma odpowiednik E-42xx w katalogu alarmów. Tabelę mapowania zrób w
  `drive.h` (kod C → `"E-42xx"`), a test w Pythonie (`tests/`) niech sprawdza ją z `catalog.yaml` i
  przechodzi przez `pytest.skip`, gdy katalogu jeszcze nie ma w gałęzi. Zapisz to w DZIENNIKU i zleć
  Codexowi włączenie testu po scaleniu #6.
- Testy C: framework `plant/core/tests/lrt_test.h`, `make -C plant/core test` albo `make test-c`;
  rdzeń bez malloc/I/O (pilnuje `tests/test_plant_core.py`). Dopisz `drive.c` do `SRC` w Makefile.
- Tolerancje testów: błąd względem wzoru analitycznego ≤ 1 %; kroki 20–100 µs.

## Zasady
- CLAUDE.md wygrywa z promptem sesji (m.in. scalanie przez PR, nie do main). Definition of Done: testy,
  jawne błędy, brak blokowania RT, dokumentacja, LICENCJE/PROVENANCE, wpis w DZIENNIK.md i prompts/DONE.md.
- Małe kroki; po każdym commit i push na wip/sesja-012. Oszczędzaj tokeny.
- Własnych PR-ów nie scalasz: scala drugi model po sprawdzeniu (wyjątek D25: autokontrola z adnotacją).
  Nie przedstawiaj autokontroli jako niezależnego przeglądu.
- Oznaczaj `Model-Author: Claude|Codex` w commitach, PR i dzienniku. Prawdziwy sprzęt/LinuxCNC:
  `NIEZWERYFIKOWANE NA SPRZĘCIE`.
- ruff (line-length 100, B905: `zip(..., strict=True)`), pytest z `PYTHONPATH=core`, `make test-c`.
- Push przez `git push -u origin wip/sesja-012` (remote `linumert` przekierowuje na `linumeRT`; ustaw
  śledzenie gałęzi, bo hook końca sesji sprawdza niewypchnięte commity).

## ZAWSZE KOŃCZ PRACĘ (obowiązkowe zamknięcie sesji)
1. Wszystko scommitowane i wypchnięte; PR otwarty; testy i lint zielone (w tym `make test-c`).
2. Wpis w DZIENNIK.md (`## 012 — Plant: emulacja napędów CiA 402 i krokowców`) i prompts/DONE.md.
3. Zaktualizuj sekcję „Stan” w docs/PROMPT_NOWEJ_SESJI.md i linię `Tura:` w NASTEPNA_SESJA.md
   (stan: oddana), zwolnij LOCK (pusty plik).
4. Zostaw drugiemu modelowi konkretne zlecenia (co sprawdzić, co scalić, co zrobić dalej).
5. Użytkownikowi podaj: co powstało, link do PR-a i jeden następny krok (sesja 013: biblioteka napędów
   wirtualnych, szablony YAML).
