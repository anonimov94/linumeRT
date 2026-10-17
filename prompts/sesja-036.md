# Sesja 036/084 · M2 Ekran linumeRT na bazie QtDragon · Poziomy dostępu

Kolejność: sesja 36 z 84 · poprzednia: sesja-035. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-036` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-036` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Role w ekranie.

## Zakres pracy
1. Role operator/technolog/serwis, PIN (scrypt) w SQLite, opcjonalnie klucz z pulpitu (pin HAL).
2. Blokowanie zakładek/akcji: edycja narzędzi i offsetów (technolog+), ustawienia i konfiguracja (serwis).
3. Audyt zmian w SQLite.
4. Testy rdzenia uprawnień.

## Kryteria akceptacji
- [ ] testy przechodzą
- [ ] PIN nie zapisany jawnie
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 036 — Poziomy dostępu` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `036 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-036` do `main` (commit z prefiksem `sesja 036:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
