# Sesja 083/084 · M6 Wtyczki, instalator, alfa · Wydanie v0.5.0-alpha

Kolejność: sesja 83 z 84 · poprzednia: sesja-082. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-083` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-083` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M6
Wtyczki deklaratywne, instalator dla Debiana 12 + LinuxCNC 2.9, dokumentacja, przegląd IP przed wydaniem, regresja na Plant, wydanie alfa.

## Cel tej sesji
Notatki wydania.

## Zakres pracy
1. CHANGELOG, wersje spójne, examples/.
2. Ograniczenia: brak weryfikacji na sprzęcie, symulacja 2.5D, EtherCAT/ATC/VFD niezweryfikowane.
3. Nie publikuj wydania ani tagu — przygotuj `docs/raporty/RELEASE_NOTES_0.5.0.md` i instrukcję; przed publikacją wynik sprawdzenia nazwy linumeRT.

## Kryteria akceptacji
- [ ] notatki gotowe
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 083 — Wydanie v0.5.0-alpha` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `083 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-083` do `main` (commit z prefiksem `sesja 083:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
