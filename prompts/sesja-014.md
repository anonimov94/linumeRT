# Sesja 014/084 · M1 Wirtualna obrabiarka Plant · Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O

Kolejność: sesja 14 z 84 · poprzednia: sesja-013. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-014` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-014` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Złożenie osi i instancji napędów w maszynę z `machine.yaml` — REQ-VM-02 … VM-05.

## Zakres pracy
1. `plant/core/machine.c` + `plant/server/build_machine.py`: budowa modelu z machine.yaml (bez osobnego plant.yaml — REQ-VM-01): łańcuch kinematyczny (kinematyka prosta dla pozycji narzędzia w układzie maszyny), mapowanie oś ↔ napędy, gantry z dwoma napędami i alarmem rozjazdu.
2. Twarde zderzaki (sprężyna + tłumik, zdarzenie CRASH_HARDSTOP, opcjonalny błąd napędu), krańcówki (pozycja, histereza, NC/NO, wspólne wejście, debounce), czujniki bazowe, impuls indeksu na obrót silnika.
3. Pętla E-STOP (przerwanie → quick stop/STO), sonda (prostopadłościan przygotówki lub płytka o znanej wysokości), mapa wejść/wyjść cyfrowych do LRT-NET.
4. Przykładowe maszyny z sesji 010 budują się w Plant.
5. Testy z oznaczeniami REQ: kin_gantry/kin_xyza/kin_trunnion (pozycja narzędzia z kinematyki prostej), gantry_skew_alarm, hardstop_crash, limit_switch_trip, shared_limit_input.

## Kryteria akceptacji
- [ ] wszystkie testy REQ-VM-02…05 zielone
- [ ] 5 przykładów buduje się w Plant
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 014 — Plant: łańcuch kinematyczny, przejazdy, zderzaki, krańcówki, I/O` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `014 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-014` do `main` (commit z prefiksem `sesja 014:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
