# Sesja 069/084 · M5 Konfiguracja maszyn hobbystów · Diagnostyka napędów

Kolejność: sesja 69 z 84 · poprzednia: sesja-068. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-069` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-069` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M5
machine.yaml → INI/HAL dla sim, Plant, step/dir, EtherCAT, VFD; 4/5 osi; ATC; kreator; diagnostyka napędów; asystent strojenia na Plant.

## Cel tej sesji
Ekran diagnostyki.

## Zakres pracy
1. Wygląd wg `docs/design/makiety/04_diagnostyka_napedow.png`. Dekoder statusword CiA 402 (własne opisy PL), kody błędów, tabela napędów.
2. Wykres błędu nadążania i momentu z pinów (lrt_net/lcec), ≤ 20 Hz.
3. Wyjście `ethercat slaves/master` gdy dostępne; brak mastera → komunikat.
4. Test z Plant: wymuszony fault widoczny w diagnostyce.

## Kryteria akceptacji
- [ ] test dekodera na każdy stan
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 069 — Diagnostyka napędów` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `069 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-069` do `main` (commit z prefiksem `sesja 069:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
