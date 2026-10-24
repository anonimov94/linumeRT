# Sesja 020/084 · M1 Wirtualna obrabiarka Plant · Magazyn narzędzi, pozycje wymiany i kolizje w Plant

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 20 z 84 · poprzednia: sesja-019. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-020` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-020` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Zrealizować REQ-VM-08, VM-09, VM-10 w Plant (makra M6 po stronie LinuxCNC — sesja 066).

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` REQ-VM-08…10.
2. Model magazynu: regał liniowy, karuzela (indeksowanie z czasem i czujnikiem pozycji), parasolowy (wahadło z czasem), ręczny; baza i orientacja w układzie maszyny, pozycje gniazd wyliczane z parametrów lub z listy; obecność narzędzia w gnieździe; osłona z siłownikiem i czujnikami; zacisk wrzeciona (zwolnij/zaciśnij, czas, czujnik, przedmuch).
3. Fizyka wymiany: narzędzie przechodzi z gniazda do wrzeciona tylko przy właściwej pozycji (tolerancja), wysokości i stanie zacisku; inaczej zdarzenie (np. TOOL_DROP, CLAMP_FAULT).
4. Pozycje: ręczna wymiana, bezpieczna Z, czujnik długości narzędzia (wejście sondy przy dotknięciu z uwzględnieniem długości narzędzia z bazy).
5. Bryły kolizyjne (prostopadłościany, walce) i detekcja CRASH z parą elementów (głowica–magazyn, narzędzie–imadło itd.).
6. Wejścia/wyjścia magazynu w LRT-NET; testy: atc_rack_geometry, atc_carousel_index, atc_cover_timing, manual_change_position, toolsetter_measure, crash_head_magazine (w lockstep z atrapą mastera).

## Kryteria akceptacji
- [ ] testy REQ-VM-08…10 zielone
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 020 — Magazyn narzędzi, pozycje wymiany i kolizje w Plant` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-020` do `main` (commit z prefiksem `sesja 020:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
