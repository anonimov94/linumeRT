# Sesja 010/084 · M1 Wirtualna obrabiarka Plant · Model obrabiarki machine.yaml (jedno źródło prawdy)

Kolejność: sesja 10 z 84 · poprzednia: sesja-009. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-010` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-010` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M1
Osobna VM symulująca fizyczną obrabiarkę: biblioteka kopiowalnych, parametryzowanych napędów wirtualnych; konfigurowalna kinematyka, liczba osi, przejazdy, zderzaki, krańcówki, ograniczenia programowe i strefy zakazane, magazyn narzędzi z położeniem i pozycjami wymiany, bazowanie po rozruchu (krańcówka, indeks, twardy zderzak, enkoder absolutny, bazowanie w napędzie); dynamika z bezwładnością i ograniczeniem przyspieszenia; panel z edytorem i awariami.

## Cel tej sesji
Schemat `machine.yaml` wspólny dla Plant i (od M5) generatora konfiguracji LinuxCNC — REQ-VM-01, VM-02, VM-03, VM-11.

## Zakres pracy
1. Przeczytaj `docs/wymagania/WIRTUALNA_OBRABIARKA.md` sekcja B.
2. `core/linumert/machine/schema.py` (Pydantic v2 — dopisz do LICENCJE.md): `machine` (nazwa, typ), `kinematics` (preset: router_gantry_xyz, mill_table_xyz, xyza_rotary, xyzac_trunnion, xyzbc_trunnion, albo jawny łańcuch członów: id, rodzaj liniowy/obrotowy, wektor osi, przesunięcie, rodzic), `axes[]` (litera, napędy[], zakres mechaniczny, zderzaki: pozycja/sztywność/tłumienie, krańcówki: pozycja/histereza/NC-NO/wejście/debounce, czujnik bazowy, soft limits, maks. prędkość i przyspieszenie, bazowanie: metoda a–e z REQ-VM-07 + parametry), `forbidden_zones[]`, `spindle`, `toolchanger` (typ, gniazda, baza i orientacja, podejście/odjazd, osłona, czujniki, zacisk), `positions` (wymiana ręczna, bezpieczna Z, czujnik narzędzia), `collision_bodies[]`, `io` (mapa wejść/wyjść, E-STOP), `drives[]` (instancje: template + overrides — format z sesji 013).
3. Walidacja spójności REQ-VM-11 jako osobny moduł `machine/validate.py` (≥ 15 reguł, błędy PL ze ścieżką pola), np. soft limits wewnątrz krańcówek, krańcówki przed zderzakami, gniazda magazynu w zasięgu osi i poza strefami zakazanymi, liczba osi zgodna z kinematyką, gantry ma 2 napędy.
4. Przykłady w `config/machines/`: router_gantry_steppers.yaml, mill_servo_table.yaml, router_xyza.yaml, mill_xyzac_trunnion.yaml, router_atc_rack.yaml (wartości typowe, opisane jako przykładowe).
5. Testy: każdy przykład waliduje się; ≥ 15 testów błędnych konfiguracji (każdy oznaczony `# REQ-VM-11`); test, że nie ma drugiego źródła parametrów (`# REQ-VM-01`).

## Kryteria akceptacji
- [ ] 5 przykładów przechodzi walidację
- [ ] ≥ 15 testów negatywnych
- [ ] znaczniki REQ w testach
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 010 — Model obrabiarki machine.yaml (jedno źródło prawdy)` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `010 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-010` do `main` (commit z prefiksem `sesja 010:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
