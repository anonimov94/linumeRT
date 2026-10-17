# Sesja 051/084 · M4 Symulacja i kolizje · Ścieżka z programu

Kolejność: sesja 51 z 84 · poprzednia: sesja-050. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-051` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-051` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M4
Ścieżka, czas obróbki, przygotówka, materiał 2.5D, reguły kolizji lite, widok 3D 30 FPS, raport; walidacja czasu względem Plant.

## Cel tej sesji
Moduł `simulation/path/`: lista ruchów z programu G-code do podglądu i symulacji.

## Zakres pracy
1. Własna klasa canon dla `gcode.parse` (gdy dostępny) + interpreter zapasowy (podzbiór) dla CI.
2. MoveList (tablice float32/int, linie, narzędzia), łuki z błędem cięciwy ≤ 0.01 mm.
3. Testy na 10 programach (w tym z M3).

## Kryteria akceptacji
- [ ] testy przechodzą
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 051 — Ścieżka z programu` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `051 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-051` do `main` (commit z prefiksem `sesja 051:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
