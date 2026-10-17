# Sesja 064/084 · M5 Konfiguracja maszyn hobbystów · Wrzeciono RS485 w generatorze

Kolejność: sesja 64 z 84 · poprzednia: sesja-063. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-064` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-064` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Generator hy_vfd / mb2hal.

## Zakres pracy
1. Generowanie konfiguracji z machine.yaml, alarmy E-41xx.
2. Walidacja na emulatorze VFD z Plant (sesja 021).
3. `docs/WRZECIONO_RS485.md`. Oznacz NIEZWERYFIKOWANE NA SPRZĘCIE.

## Kryteria akceptacji
- [ ] scenariusz vfd_basic przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 064 — Wrzeciono RS485 w generatorze` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `064 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-064` do `main` (commit z prefiksem `sesja 064:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
