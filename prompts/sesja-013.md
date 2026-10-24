# Sesja 013/084 · M1 Wirtualna obrabiarka Plant · Biblioteka napędów wirtualnych: szablony, kopiowanie, parametryzacja

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 13 z 84 · poprzednia: sesja-012. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-013` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-013` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Zrealizować REQ-VD-01 … VD-05.

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` sekcja A.
2. Wygląd i funkcje biblioteki wg makiety `docs/design/makiety/08_napedy_wirtualne.png` (realizacja UI w sesji 023).
3. Format szablonu `plant/library/drives/<id>.yaml` (pola REQ-VD-01, `version`, `based_on`, `live:` przy parametrach zmienianych w locie), JSON Schema + loader z walidacją zakresów.
4. Instancje w machine.yaml: `drives: [{id: X1, template: servo_400w, overrides: {...}}]`; rozwiązywanie dziedziczenia; walidacja nadpisań.
5. Kopiowanie: `python -m plant drive clone <źródło> <nowe_id>` dla szablonu i instancji (zapis nowego szablonu z `based_on`); kopia niezależna (test modyfikacji kopii nie zmienia oryginału).
6. Biblioteka startowa REQ-VD-05 (7 szablonów, wartości typowe, bez nazw producentów, każdy z komentarzem źródła wartości „przykładowe”).
7. API zmiany parametrów live (REQ-VD-04) w rdzeniu C (z sesji 011–012) + dziennik zmian z czasem.
8. Testy z oznaczeniami `# REQ-VD-0x`, w tym fizyczny: większe J → mniejsze maks. przyspieszenie zgodnie ze wzorem.

## Kryteria akceptacji
- [ ] wszystkie REQ-VD-01…05 mają testy
- [ ] 7 szablonów ładuje się
- [ ] klon niezależny (test)
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 013 — Biblioteka napędów wirtualnych: szablony, kopiowanie, parametryzacja` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-013` do `main` (commit z prefiksem `sesja 013:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
