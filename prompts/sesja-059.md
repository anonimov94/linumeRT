# Sesja 059/084 · M4 Symulacja i kolizje · Raport symulacji i eksport STL

Kolejność: sesja 59 z 84 · poprzednia: sesja-058. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-059` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-059` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M4
Ścieżka, czas obróbki, przygotówka, materiał 2.5D, reguły kolizji lite, widok 3D 30 FPS, raport; walidacja czasu względem Plant.

## Cel tej sesji
Raport HTML i STL.

## Zakres pracy
1. Raport: program, czas, zdarzenia, zrzut widoku.
2. Eksport STL z mapy wysokości.
3. Przycisk „Symuluj” w panelu dialogowym i plikach.

## Kryteria akceptacji
- [ ] STL poprawny (test nagłówka)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 059 — Raport symulacji i eksport STL` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `059 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-059` do `main` (commit z prefiksem `sesja 059:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
