# Sesja 071/084 · M5 Konfiguracja maszyn hobbystów · Asystent strojenia na Plant

Kolejność: sesja 71 z 84 · poprzednia: sesja-070. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-071` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-071` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Narzędzie strojenia.

## Zakres pracy
1. Testy ruchu (skok, trapez, sinus) z rejestracją błędu nadążania i momentu przez piny.
2. Propozycja MAX_ACCELERATION/MAX_VELOCITY z zapasem momentu (dla krokowców: margines na gubienie kroków), propozycja FF dla serw.
3. Walidacja na Plant: zmiana masy w panelu → asystent proponuje mniejsze przyspieszenie; brak zgubionych kroków po zastosowaniu.
4. Ostrzeżenia bezpieczeństwa przy przyszłym użyciu na sprzęcie. Oznacz NIEZWERYFIKOWANE NA SPRZĘCIE.

## Kryteria akceptacji
- [ ] scenariusz tuning_heavy_table przechodzi
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 071 — Asystent strojenia na Plant` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `071 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-071` do `main` (commit z prefiksem `sesja 071:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
