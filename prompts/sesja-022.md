# Sesja 022/084 · M1 Wirtualna obrabiarka Plant · Plant: panel sterowania i pulpit MPG

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 22 z 84 · poprzednia: sesja-021. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-022` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-022` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Panel web Plant na porcie 8080 (narzędzie testowe, nie HMI operatora).

## Zakres pracy
1. Wygląd wg `docs/design/makiety/06_panel_plant.png` (kolory z docs/design/tokens.yaml). FastAPI + WebSocket w `plant/server/panel/`, wykresy uPlot (MIT, wpis w LICENCJE/PROVENANCE): pozycja zadana/rzeczywista, błąd nadążania, moment, prędkość, zgubione kroki — na oś, okno 10 s, odświeżanie ≤ 20 Hz.
2. Suwaki na żywo: parametry `live` z szablonu napędu (masa, J, tarcie, limit momentu, luz, napięcie) (skaluje krzywą moment–prędkość); zapis/odczyt presetów.
3. Przyciski awarii: E-STOP, fault napędu, utrata ramek X %, opóźnienie, krańcówka, zablokowanie osi, utrata VFD, czujnik ATC zablokowany.
4. Wirtualny pulpit: pokrętło MPG (impulsy), wybór osi, krok, Start/Stop posuwu, przełącznik kluczykowy — jako wejścia do LinuxCNC przez LRT-NET.
5. Nagrywanie przebiegu do CSV.
6. Styl panelu: własna paleta linumeRT.

## Kryteria akceptacji
- [ ] panel działa na localhost (test API)
- [ ] zmiana masy w panelu zmienia przyspieszenie w teście
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 022 — Plant: panel sterowania i pulpit MPG` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-022` do `main` (commit z prefiksem `sesja 022:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
