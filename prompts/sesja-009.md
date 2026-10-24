# Sesja 009/084 · M1 Wirtualna obrabiarka Plant · Specyfikacja wirtualnej maszyny Plant

> Status, rozszerzenia i pozostały zakres: [wspólny rejestr](../docs/roadmap/plan.json).
> Ten prompt jest specyfikacją sesji; aktualizacja stanu według [instrukcji](../docs/roadmap/README.md).

Kolejność: sesja 9 z 84 · poprzednia: sesja-008. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-009` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-009` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Napisać `docs/PLANT.md` — specyfikację, na której oprą się sesje 010–026, w pełni pokrywającą wymagania REQ.

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` — wymagania REQ-VD/VM/QA są obowiązujące. Specyfikacja musi opisywać, jak każde z nich zostanie zrealizowane, i odsyłać do numerów REQ.
2. Architektura: VM-A (Debian 12 + LinuxCNC 2.9 + ekran) ↔ sieć wewnętrzna `lrtnet` 10.77.0.0/24 ↔ VM-B (Plant: serwer, rdzeń C, panel web na porcie 8080). Wariant lokalny: oba procesy na localhost (CI, WSL).
3. Protokół **LRT-NET v1** (UDP, port 47700): ramka master→plant na każdy cykl servo (seq u32, czas ns u64, liczba osi, per oś: controlword u16, mode i8, target_pos i32 [inkrementy], wyjścia cyfrowe u32, spindle_cmd f32, crc32) i odpowiedź plant→master (seq echo, per oś: statusword u16, mode_display i8, actual_pos i32, following_error i32, torque_pct i16, error_code u16; wejścia cyfrowe u32, spindle_actual f32, statystyki). Little-endian, wersja w nagłówku. Plant liczy krok modelu dla każdej ramki (sterowanie ramkami = deterministycznie).
4. Model osi: J_eff = J_silnika + J_śruby + m·(p/2π)²; moment z krzywej moment–prędkość; tarcie Coulomba + lepkie; grawitacja Z (opcjonalna przeciwwaga); luz; całkowanie półjawne z podkrokami (domyślnie 10 na ramkę). Maks. przyspieszenie wynika z (T_maks − T_tarcia − T_grawitacji)/J_eff.
5. Typy napędu: serwo CSP (pętla PI + FF w napędzie, okno błędu nadążania → fault), krokowiec open-loop (przekroczenie momentu → gubienie kroków bez alarmu), serwo krokowe (zamknięta pętla, alarm po przekroczeniu błędu).
6. I/O: krańcówki, czujniki bazowania + impuls indeksu, E-STOP pętla, sonda (z modelu przygotówki), czujniki ATC, VFD (Modbus), pulpit MPG.
7. Format `plant.yaml` (parametry maszyny) i `scenarios/*.yaml` (oś czasu awarii). Parametry zmieniane na żywo przez panel.
8. Kryteria jakości modelu i testy referencyjne (np. czas rozpędzania do v_maks zgodny z analitycznym).
9. Utwórz `docs/wymagania/MACIERZ.md` (REQ · sesja · test · status = planowane) na podstawie `docs/wymagania/WIRTUALNA_OBRABIARKA.md`.

## Kryteria akceptacji
- [ ] PLANT.md kompletny z rysunkiem (mermaid) i tabelą ramki
- [ ] przykładowe plant.yaml i scenariusz w docs
- [ ] każde REQ z WIRTUALNA_OBRABIARKA.md jest przywołane w PLANT.md i w MACIERZ.md
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 009 — Specyfikacja wirtualnej maszyny Plant` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Zaktualizuj rekord sesji w `docs/roadmap/plan.json` (status, postęp, pozostałe kryteria i dowody); uruchom `python3 tools/roadmap.py`. DONE i spis promptów są generowane.
3. Scal `wip/sesja-009` do `main` (commit z prefiksem `sesja 009:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
