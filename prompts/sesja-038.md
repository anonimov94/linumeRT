# Sesja 038/084 · M2 Ekran linumeRT na bazie QtDragon · Bufor i bramka G2 (prototyp v0.1)

Kolejność: sesja 38 z 84 · poprzednia: sesja-037. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-038` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-038` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Domknąć M2.

## Zakres pracy
1. Zestaw scenariuszy `suite_operator`: bazowanie, JOG, MPG, MDI, program, pauza/wznowienie, zmiana narzędzia, sonda, awaria napędu, E-STOP.
2. Raport prototypu v0.1, zrzuty ekranów.
3. `docs/prawne/PRZEGLAD_PODOBIENSTWA_v0.1.md`: szablon dla osoby nieuczestniczącej w projekcie (WYTYCZNE §4.8) — zrzuty naszych ekranów i pytania kontrolne. Bez zrzutów cudzych sterowań w repo.
4. `docs/raporty/G2.md` dla użytkownika.

## Kryteria akceptacji
- [ ] raport v0.1
- [ ] G2.md i szablon przeglądu gotowe
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 038 — Bufor i bramka G2 (prototyp v0.1)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `038 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-038` do `main` (commit z prefiksem `sesja 038:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
