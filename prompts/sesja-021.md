# Sesja 021/084 · M1 Wirtualna obrabiarka Plant · Plant: wrzeciono VFD przez Modbus

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 21 z 84 · poprzednia: sesja-020. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-021` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-021` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Emulacja VFD i konfiguracja LinuxCNC.

## Zakres pracy
1. Model wrzeciona: bezwładność, rampa, obciążenie (stałe/z parametru), at-speed.
2. Serwer Modbus RTU na wirtualnym porcie szeregowym (socat pty ↔ TCP między VM) w mapie rejestrów zgodnej z tym, czego oczekuje `hy_vfd` (sprawdź dokumentację komponentu) oraz Modbus TCP dla `mb2hal` (ogólna mapa z plant.yaml). Biblioteka Modbus: wybierz licencyjnie zgodną (wpis w LICENCJE.md) lub prosty własny serwer.
3. Wstrzykiwanie: utrata komunikacji, błąd falownika, przeciążenie.
4. Konfiguracja LinuxCNC: wariant `_vfd` w config/plant z hy_vfd i sygnałami `linumert.spindle.*`.
5. Testy: odpowiedzi rejestrów, rampa, at-speed.

## Kryteria akceptacji
- [ ] test komunikacji Modbus na localhost
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 021 — Plant: wrzeciono VFD przez Modbus` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-021` do `main` (commit z prefiksem `sesja 021:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
