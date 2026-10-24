# Sesja 012/084 · M1 Wirtualna obrabiarka Plant · Plant: emulacja napędów CiA 402 i krokowców

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 12 z 84 · poprzednia: sesja-011. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-012` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-012` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Moduł napędu w `plant/core/drive.c`.

## Zakres pracy
1. Maszyna stanów CiA 402 (Not ready → Switch on disabled → Ready to switch on → Switched on → Operation enabled; Quick stop; Fault; Fault reset) sterowana controlword, raportowana statusword (własna implementacja wg ogólnego opisu profilu).
2. Tryb CSP: pętla położenia P + pętla prędkości PI + FF prędkości/przyspieszenia, ograniczenie momentu, okno błędu nadążania → fault z kodem.
3. Krokowiec open-loop: pozycja zadana jako kroki; gdy wymagany moment > dostępny (krzywa pull-out) → poślizg o pełne kroki, licznik zgubionych kroków (bez alarmu do mastera — jak w realu).
4. Serwo krokowe: zamknięta pętla, alarm przy błędzie > progu.
5. Rozdzielczość enkodera, szum enkodera (opcjonalny).
6. Testy C: przejścia stanów, fault przy przekroczeniu okna, gubienie kroków przy zbyt dużym przyspieszeniu, brak gubienia przy rozsądnym.
7. Obsługa obiektów 6065h (okno błędu), 6072h (maks. moment — używany też przy bazowaniu na zderzak), 6098h/6099h/609Ah (metoda i prędkości bazowania w napędzie) w modelu napędu.

## Kryteria akceptacji
- [ ] testy C przechodzą
- [ ] każdy kod błędu napędu ma odpowiednik E-42xx w katalogu
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 012 — Plant: emulacja napędów CiA 402 i krokowców` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-012` do `main` (commit z prefiksem `sesja 012:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
