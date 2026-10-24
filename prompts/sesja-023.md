# Sesja 023/084 · M1 Wirtualna obrabiarka Plant · Edytor wirtualnej obrabiarki w panelu Plant

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 23 z 84 · poprzednia: sesja-022. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-023` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-023` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Zrealizować REQ-VM-12 i interfejs dla REQ-VD-03.

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` REQ-VM-12, REQ-VD-03.
2. Wygląd wg makiet `docs/design/makiety/08_napedy_wirtualne.png` (zakładka Napędy) i `09_wirtualna_obrabiarka.png` (zakładka Maszyna).
3. Zakładka „Maszyna” w panelu Plant: drzewo (kinematyka → osie → napędy, krańcówki, zderzaki, bazowanie; magazyn; pozycje; strefy; bryły), formularze generowane ze schematu machine.yaml.
4. Napędy: lista szablonów, „Kopiuj”, „Zapisz jako szablon”, porównanie z szablonem bazowym (różnice wyróżnione).
5. Uproszczony podgląd 2D (rzuty XY i XZ) brył, zakresów, krańcówek, stref i gniazd magazynu, z przesuwaniem magazynu i pozycji wymiany.
6. Każdy zapis przechodzi walidację REQ-VM-11; zapis wersji (`machines/<nazwa>/historia/`), przeładowanie modelu bez restartu VM (bezpiecznie: tylko gdy napędy wyłączone).
7. Styl wg docs/design (tokens.yaml, makieta 06).
8. Testy API edytora i scenariusz `edit_reload`.

## Kryteria akceptacji
- [ ] test_editor_api i edit_reload zielone
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 023 — Edytor wirtualnej obrabiarki w panelu Plant` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-023` do `main` (commit z prefiksem `sesja 023:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
