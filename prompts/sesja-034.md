# Sesja 034/084 · M2 Ekran linumeRT na bazie QtDragon · Ręczna zmiana narzędzia

Kolejność: sesja 34 z 84 · poprzednia: sesja-033. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-034` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-034` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Dialog zmiany narzędzia QtDragon + dane z ToolDB.

## Zakres pracy
1. Dostosuj dialog ręcznej zmiany narzędzia (emulacja pinów hal_manualtoolchange w QtDragon) do nowego stylu; pokaż typ, D, L, opis z ToolDB; przerwanie → stop programu + W-2130.
2. Opcjonalne wycofanie Z do pozycji zmiany przed oknem (ustawienie INI).
3. Scenariusz Plant `manual_toolchange` (M6 w programie).

## Kryteria akceptacji
- [ ] scenariusz przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 034 — Ręczna zmiana narzędzia` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `034 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-034` do `main` (commit z prefiksem `sesja 034:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
