# Sesja 018/084 · M1 Wirtualna obrabiarka Plant · Konfiguracja LinuxCNC dla Plant (3 osie)

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 18 z 84 · poprzednia: sesja-017. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-018` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-018` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
`config/plant/linumert_plant_xyz/`.

## Zakres pracy
1. INI/HAL: servo-thread 1 ms, `lrt_net` (adres Plant z INI), `lrt_cia402`, sygnały kontraktu D05, bazowanie z czujnikami i indeksem, krańcówki, E-STOP z Plant (estop_latch), limity prędkości/przyspieszenia zgodne z plant.yaml.
2. Warianty bazowania w INI/HAL dla każdej metody z sesji 015 (osobne pliki `home_*.hal`/sekcje INI) i scenariusze home_* z LinuxCNC.
3. Ekran `linumert` jako DISPLAY.
4. Test end-to-end (marker linuxcnc, localhost): start Plant lockstep/realtime + LinuxCNC headless, bazowanie przez `linuxcnc.command`, ruch G1, odczyt błędu nadążania z Plant.
5. `docs/PLANT_START.md`: jak uruchomić lokalnie (WSL) i w VM.

## Kryteria akceptacji
- [ ] test e2e przechodzi lub szczegółowy raport, co blokuje
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 018 — Konfiguracja LinuxCNC dla Plant (3 osie)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-018` do `main` (commit z prefiksem `sesja 018:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
