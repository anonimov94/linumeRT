# Sesja 019/084 · M1 Wirtualna obrabiarka Plant · Ograniczenia programowe, strefy zakazane i wyrocznia testowa

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 19 z 84 · poprzednia: sesja-018. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-019` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-019` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Zrealizować REQ-VM-06.

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` REQ-VM-06.
2. Plant wczytuje soft limits (z machine.yaml; od M5 te same wartości trafiają do INI) i strefy zakazane (prostopadłościany w układzie maszyny).
3. Wyrocznia: każda zadana pozycja (target z ramki) i pozycja narzędzia z kinematyki prostej sprawdzana w każdym cyklu; naruszenie → zdarzenie ORACLE_VIOLATION (oś/strefa, pozycja, numer ramki) i FAIL w raporcie scenariusza, niezależnie od tego, czy LinuxCNC je zablokował.
4. Scenariusze `softlimit_oracle` (MDI poza zakres — LinuxCNC powinien odrzucić; test sprawdza brak naruszenia) i `forbidden_zone_oracle` (program celowo wjeżdża w strefę magazynu — oczekiwane naruszenie wykryte).
5. Testy jednostkowe geometrii stref.

## Kryteria akceptacji
- [ ] oba scenariusze dają oczekiwany wynik
- [ ] znaczniki # REQ-VM-06
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 019 — Ograniczenia programowe, strefy zakazane i wyrocznia testowa` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-019` do `main` (commit z prefiksem `sesja 019:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
