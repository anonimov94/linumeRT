# Sesja 028/084 · M2 Ekran linumeRT na bazie QtDragon · Kompozycja ekranu głównego

Kolejność: sesja 28 z 84 · poprzednia: sesja-027. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-028` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-028` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M2
Własny system projektowy i kompozycja ekranu, tryby, JOG/MPG, MDI, AUTO, narzędzia, zerowanie i sonda, zmiana narzędzia, alarmy, role, PL/EN.

## Cel tej sesji
Przebudować `.ui` ekranu głównego na własną kompozycję.

## Zakres pracy
1. Najpierw `docs/design/SPEC_EKRAN_GLOWNY.md`: czego operator potrzebuje (dane, akcje, priorytety) — specyfikacja funkcjonalna bez odniesień do cudzych ekranów (WYTYCZNE §4.1).
2. Odwzoruj makietę `docs/design/makiety/01_maszyna.png`: górny pasek (znak + logotyp linumeRT, przełącznik JOG/MDI/AUTO, program, stan połączenia, rola, zegar), linia komunikatu, lewa szyna obszarów (Maszyna, Program, Narzędzia, Symulacja, Diagnostyka, Konfiguracja), DRO, karty narzędzia i posuwu/wrzeciona, okno bieżących bloków, podgląd ścieżki, dolny pasek dużych akcji ze stanem E-STOP. Edytuj `.ui` (Qt Designer XML) ostrożnie. Zachowaj nazwy obiektów, których używa handler QtDragon, albo przenieś logikę do handler-patch.
3. Uruchom ekran w sim, napraw błędy handlera, zrzut ekranu do `docs/raporty/G2/`.
4. Notatka podobieństwa: lista elementów funkcjonalnie wspólnych dla wielu sterowań vs elementy własne (WYTYCZNE §4.8, §9).

## Kryteria akceptacji
- [ ] ekran startuje bez wyjątków w handlerze (log)
- [ ] SPEC_EKRAN_GLOWNY.md istnieje
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 028 — Kompozycja ekranu głównego` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `028 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-028` do `main` (commit z prefiksem `sesja 028:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
