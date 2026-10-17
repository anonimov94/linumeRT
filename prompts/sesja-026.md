# Sesja 026/084 · M1 Wirtualna obrabiarka Plant · Bufor i bramka G1 (prototyp P0)

Kolejność: sesja 26 z 84 · poprzednia: sesja-025. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-026` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-026` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Domknąć M1.

## Zakres pracy
1. Zaległości z DZIENNIK.md (009–025).
2. Uruchom `tools/check_requirements.py`; każde REQ-VD/VM/QA musi być zielone. Uaktualnij MACIERZ.md.
3. Uruchom wszystkie scenariusze dostępne w środowisku, zapisz raport prototypu P0.
4. `docs/raporty/G1.md`: checklista użytkownika (budowa VM, uruchomienie first_motion, zabawa suwakami masy i obserwacja błędu nadążania).

## Kryteria akceptacji
- [ ] raport P0 w docs/raporty/prototypy/
- [ ] G1.md gotowy
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 026 — Bufor i bramka G1 (prototyp P0)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `026 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-026` do `main` (commit z prefiksem `sesja 026:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
