# Sesja 057/084 · M4 Symulacja i kolizje · Widok 3D symulacji

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 57 z 84 · poprzednia: sesja-056. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-057` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-057` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M4
Ścieżka, czas obróbki, przygotówka, materiał 2.5D, reguły kolizji lite, widok 3D 30 FPS, raport; walidacja czasu względem Plant.

## Cel tej sesji
pyqtgraph.opengl w ekranie.

## Zakres pracy
1. Wygląd wg `docs/design/makiety/03_symulacja.png`. Mesh mapy wysokości, ścieżka jako jeden bufor linii, narzędzie jako bryła z profilu, limit 30 FPS (QTimer), render tylko przy zmianie.
2. Oś czasu ze znacznikami (zmiany narzędzia, kolizje), lista zdarzeń → skok do linii w edytorze.
3. Benchmark 100 000 segmentów offscreen → wynik w docs/raporty/G4/.

## Kryteria akceptacji
- [ ] limit FPS działa (test)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 057 — Widok 3D symulacji` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-057` do `main` (commit z prefiksem `sesja 057:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
