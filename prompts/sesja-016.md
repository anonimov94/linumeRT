# Sesja 016/084 · M1 Wirtualna obrabiarka Plant · Plant: serwer LRT-NET

Kolejność: sesja 16 z 84 · poprzednia: sesja-015. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-016` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-016` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Serwer Python + rdzeń C (cffi lub ctypes) w `plant/server/`.

## Zakres pracy
1. Budowa biblioteki współdzielonej z `plant/core` i wiązania (ctypes, bez dodatkowych zależności, lub cffi — wpis w LICENCJE.md).
2. Pętla UDP: odbiór ramki → krok modelu dla dt z ramki → odpowiedź; watchdog (brak ramek > N ms → napędy w fault E-4003), statystyki (utracone, spóźnione, jitter odbioru).
3. Tryby: `--realtime` (VM-B) i `--lockstep` (testy, CI).
4. Klient testowy `plant/server/test_master.py` udający LinuxCNC (profil trapezowy) i testy pętli zwrotnej na localhost.
5. Logowanie przebiegów do pliku (CSV/npz) w osobnym wątku.
6. Odporność (REQ-QA-03): uszkodzona ramka, brak pliku szablonu, wyjątek w modelu → bezpieczny stan (napędy wyłączone) i komunikat, bez zakończenia procesu; deterministyczność (REQ-QA-04): ślad z sumą kontrolną dla ziarna.

## Kryteria akceptacji
- [ ] test: 10 000 ramek w lockstep bez strat
- [ ] watchdog działa (test)
- [ ] testy `# REQ-QA-03` i `# REQ-QA-04` zielone
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 016 — Plant: serwer LRT-NET` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `016 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-016` do `main` (commit z prefiksem `sesja 016:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
