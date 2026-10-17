# Sesja 030/084 · M2 Ekran linumeRT na bazie QtDragon · MDI i klawiatura ekranowa

Kolejność: sesja 30 z 84 · poprzednia: sesja-029. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-030` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-030` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
MDI w nowym układzie.

## Zakres pracy
1. Widżet MDI QtVCP + historia, klawiatura ekranowa (QtDragon ma klawiaturę wirtualną — dostosuj wygląd i układ do G-code).
2. Linia aktywnych kodów G/M.
3. Błędy LinuxCNC → katalog E-1000 z tekstem oryginalnym.
4. Test na Plant: MDI `G0 X10` i `G1 X0 F500` z odczytem pozycji.

## Kryteria akceptacji
- [ ] scenariusz mdi_basic przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 030 — MDI i klawiatura ekranowa` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `030 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-030` do `main` (commit z prefiksem `sesja 030:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
