# Sesja 005/084 · M0 Fundament, prawo, środowisko · Kopia bazowa ekranu QtDragon

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 5 z 84 · poprzednia: sesja-004. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-005` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-005` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M0
Repozytorium, CI, wytyczne IP i rejestr pochodzenia, budowa LinuxCNC w środowisku agenta, kopia bazowa QtDragon, rdzeń z atrapą.

## Cel tej sesji
Utworzyć `screens/linumert/` metodą `qtvcp copy` / handler-patch.

## Zakres pracy
1. Skopiuj ekran `qtdragon` (wariant 1280×768+) z LinuxCNC 2.9 do `screens/linumert/` (pliki .ui, handler, .qss, zasoby), zmień nazwy plików na `linumert*`.
2. Handler: `linumert_handler.py` dziedziczy po oryginalnym handlerze tam, gdzie to możliwe (wzorzec patch z dokumentacji QtVCP), żeby łatwiej przenosić poprawki upstream.
3. `screens/linumert/UPSTREAM.md`: wersja LinuxCNC, commit, lista skopiowanych plików, licencja, procedura aktualizacji (diff z upstream).
4. Usuń z kopii zasoby, których nie potrzebujemy (np. przykładowe obrazy), wpisz zmiany w PROVENANCE.md.
5. Konfiguracja sim z sesji 004 dostaje wariant `DISPLAY = qtvcp linumert` (ścieżka ekranu w INI).
6. Jeśli LinuxCNC działa w środowisku (sesja 003): zrzut ekranu pod Xvfb do `docs/raporty/G0/ekran_bazowy.png`.

## Kryteria akceptacji
- [ ] UPSTREAM.md kompletny
- [ ] ekran startuje (zrzut) albo opisany powód, czemu nie da się sprawdzić
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 005 — Kopia bazowa ekranu QtDragon` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-005` do `main` (commit z prefiksem `sesja 005:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
