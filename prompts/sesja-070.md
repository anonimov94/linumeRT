# Sesja 070/084 · M5 Konfiguracja maszyn hobbystów · Łańcuch E-STOP i bezpieczeństwo

Kolejność: sesja 70 z 84 · poprzednia: sesja-069. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-070` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-070` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
E-STOP w generatorach + dokumentacja.

## Zakres pracy
1. estop_latch z wejściem sprzętowym, błędami napędów, watchdogiem komunikacji; odmowa generowania bez wejścia E-STOP (poza sim).
2. Źródło E-STOP na ekranie.
3. `docs/BEZPIECZENSTWO.md` dla hobbystów.
4. Scenariusze Plant: estop_button, estop_comm_loss.

## Kryteria akceptacji
- [ ] scenariusze przechodzą
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 070 — Łańcuch E-STOP i bezpieczeństwo` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `070 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-070` do `main` (commit z prefiksem `sesja 070:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
