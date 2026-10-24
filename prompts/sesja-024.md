# Sesja 024/084 · M1 Wirtualna obrabiarka Plant · Plant: scenariusze i raport prototypu

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 24 z 84 · poprzednia: sesja-023. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-024` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-024` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Runner scenariuszy i raport HTML.

## Zakres pracy
1. `plant/scenarios/*.yaml`: nazwa, konfiguracja maszyny, program .ngc, kroki (czas/linia → akcja: awaria, zmiana parametru, oczekiwanie na stan), kryteria (maks. błąd nadążania, brak zgubionych kroków, oczekiwany alarm).
2. `tools/run_scenario.py`: uruchamia Plant + LinuxCNC (lokalnie lub zdalnie po SSH do VM), steruje przez `linuxcnc.command`, zbiera przebiegi i alarmy.
3. Raport HTML (statyczny, wykresy SVG): PASS/FAIL per kryterium, przebiegi, wersje — do `docs/raporty/prototypy/`.
4. Scenariusze startowe: first_motion, homing_all, rapid_vs_feed, too_much_accel_stepper (oczekiwane zgubione kroki), drive_fault_mid_program, estop_mid_program.
5. `tools/check_requirements.py` (REQ-QA-01): parsuje tabele REQ z docs/wymagania/*.md, szuka znaczników `# REQ-..` w testach i `requirements:` w scenariuszach; brak pokrycia = błąd; uaktualnia kolumnę Status w MACIERZ.md. Dodaj do `make test`.
6. Job CI `plant-matrix` (REQ-QA-02): scenariusze na 5 przykładowych maszynach z sesji 010; fuzz machine.yaml (REQ-QA-03).

## Kryteria akceptacji
- [ ] co najmniej 2 scenariusze przechodzą w CI (lockstep, bez LinuxCNC — atrapa mastera) lub z LinuxCNC, jeśli dostępny
- [ ] check_requirements.py w CI; wszystkie REQ mają testy
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 024 — Plant: scenariusze i raport prototypu` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-024` do `main` (commit z prefiksem `sesja 024:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
