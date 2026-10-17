# Sesja 015/084 · M1 Wirtualna obrabiarka Plant · Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd

Kolejność: sesja 15 z 84 · poprzednia: sesja-014. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-015` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-015` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Zrealizować REQ-VM-07 po stronie Plant i przygotować obsługę po stronie LinuxCNC.

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` REQ-VM-07.
2. Stan po włączeniu: niebazowany, pozycja startowa losowa w zakresie przejazdu (ziarno w scenariuszu) albo z pliku stanu; enkoder absolutny pamięta pozycję między uruchomieniami, awaria baterii (wstrzykiwana) kasuje ją.
3. Metoda (a) krańcówka/czujnik bazowy i (b) czujnik + indeks: zachowanie fizyczne czujników z sesji 014.
4. Metoda (c) twardy zderzak: podczas bazowania zredukowany limit momentu (6072h z HAL lub parametr), detekcja zderzaka przez próg momentu lub błędu nadążania przez zadany czas. Po stronie LinuxCNC: sygnał „czujnik bazowy” syntetyzowany w HAL z momentu/błędu nadążania (komponenty `comp`, `timedelay` lub własny `hal/lrt_hardstop_home.comp`) — sprawdź w dokumentacji LinuxCNC 2.9 opcje bazowania (HOME_SEARCH_VEL, HOME_LATCH_VEL, HOME_IGNORE_LIMITS, HOME_ABSOLUTE_ENCODER, moduł homemod) i opisz wybrane rozwiązanie w DECYZJE.md.
5. Metoda (d) enkoder absolutny: konfiguracja `HOME_ABSOLUTE_ENCODER` (sprawdź wartości 0/1/2 w dokumentacji) i obsługa utraty pozycji.
6. Metoda (e) bazowanie w napędzie CiA 402: tryb 6, metoda z szablonu (6098h), bity statusword homing attained/error; po stronie mastera sekwencja w `lrt_cia402` (sesja 017 dokończy po stronie HAL).
7. Wyrównanie gantry na dwóch czujnikach (osobne bazowanie napędów Y1/Y2).
8. Testy Plant (lockstep, atrapa mastera) dla każdej metody z oznaczeniem `# REQ-VM-07`; w scenariuszach z LinuxCNC (sesja 018): home_switch, home_switch_index, home_hardstop, home_absolute, home_drive_internal, home_gantry_square.

## Kryteria akceptacji
- [ ] każda metoda a–e ma test w Plant
- [ ] decyzja o metodzie zderzakowej w DECYZJE.md
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 015 — Bazowanie po rozruchu: krańcówka, indeks, twardy zderzak, absolut, napęd` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `015 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-015` do `main` (commit z prefiksem `sesja 015:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
