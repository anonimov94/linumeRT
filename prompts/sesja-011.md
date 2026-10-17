# Sesja 011/084 · M1 Wirtualna obrabiarka Plant · Plant: rdzeń dynamiki osi (C)

Kolejność: sesja 11 z 84 · poprzednia: sesja-010. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-011` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-011` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Biblioteka C `plant/core` z modelem mechaniki osi.

## Zakres pracy
1. `plant/core/axis.h/.c`: struktura parametrów (J_motor, J_screw, masa, skok śruby lub przełożenie dla osi obrotowej, krzywa moment–prędkość jako tablica punktów, tarcie Coulomba/lepkie, grawitacja, luz, sztywność opcjonalna), stan (pozycja, prędkość silnika i obciążenia).
2. `axis_step(axis, torque_cmd, dt)` z podkrokami; ograniczenie momentu z krzywej; obsługa twardego ogranicznika (zderzenie → flaga).
3. Zero alokacji po inicjalizacji; brak zależności poza libc/libm.
4. `Makefile` + testy w C (prosty framework w repo): rozpędzanie przy stałym momencie vs wzór, wpływ masy na przyspieszenie, tarcie statyczne, luz przy zmianie kierunku.
5. `make test-c` w CI.

## Kryteria akceptacji
- [ ] ≥ 10 testów C, błąd względem rozwiązania analitycznego ≤ 1 %
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 011 — Plant: rdzeń dynamiki osi (C)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `011 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-011` do `main` (commit z prefiksem `sesja 011:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
