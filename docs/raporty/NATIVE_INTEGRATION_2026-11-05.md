# Przyspieszenia C w pełnym projekcie

2026-11-05 · Model-Author: Codex (integracja/odbiór); Claude (algorytmy C i referencje).
PR #222, zależny od częściowej kontroli #221. Nie utworzono drugiego kernela z lite.

## Zakres i zgodność

Scalona historia `claude/natywne-przyspieszenia` 0bd1f04: zmap_cut i relief_heights,
ctypes, wektoryzacja referencji, optymalizacja okna obciążenia i katalogu alarmów.
GUI i sterowanie pełnego projektu zachowane. C liczy poza RT; bez biblioteki
pozostaje Python. Import nie uruchamia kompilatora. Wheel nie zawiera pliku .so;
budowa ze źródeł/ISO lub jawny LINUMERT_NATIVE_LIB, zgodnie z core/native/README.md.

Po przeglądzie integracji dodano fallback dla biblioteki mającej ABI, ale brakujące
eksporty. Porównanie wysokości/map sprawdza także bajty tablic, nie tylko równość
numeryczną. Nie zmieniono algorytmów Claude ani progów diagnostyki.

Odbiór w WSL Debian 12:

- `make test-c`: Plant C i 7 C core/native PASS; 189 testów symulacji/CAM z C PASS,
  2 skip (GUI/Qt w lokalnym venv), 6 subtestów PASS.
- `make -C core/native test-san`: 7 PASS, ASan+UBSan, setarch x86_64 -R.
- Po kontroli eksportów i dodaniu porównań bajtowych: 22 testy native/architektury PASS.
- Brak odbioru całego zadania verify/run/report ani sprzętu; końcowe CI wymagane.
- Pełny natywny klon 51de699: 2070 PASS, 15 skip, 217 linuxcnc deselected,
  184 subtesty PASS; dwie porażki: znana Qt (100 zamiast85) oraz harness
  `test_make_test_c_target_runs_core_tests` wybierający systemowy Python bez pytest.
  Harness wskazuje teraz `sys.executable`; ten sam zagnieżdżony cel PASS (39 s).
  Nie deklarujemy pełnego zielonego odbioru Qt ani ponownego pełnego przebiegu po tej zmianie.

## Pomiar Python i C po integracji

Python 3.11.2, numpy 2.4.6, gcc 12.2, WSL; checkout na /mnt/c, nice -n10.
Minimum z 3 powtórzeń, bez izolacji CPU. Pomiary backendów wykonane kolejno;
pod koniec pomiaru C równolegle działał krótki test zgodności native.
Wynik orientacyjny dla tych danych, bez deklaracji gwarantowanego czasu.
Oba przebiegi używają **parsera subset** w istniejącej symulacji diagnostycznej.
To pomiar integracji obliczeń, nie odbiór pełnego toru z LinuxCNC ani całego VERTICAL-VERIFY.

Surowe dane: [Python](native-integration/bench_python.json),
[C](native-integration/bench_native.json). Odtworzenie:

```sh
make native
LINUMERT_NATIVE=0 nice -n10 python tools/bench_wydajnosc.py --repeat 3 --json bench_python.json
LINUMERT_NATIVE=1 nice -n10 python tools/bench_wydajnosc.py --repeat 3 --json bench_native.json
python tools/bench_wydajnosc.py --compare bench_python.json bench_native.json
```

Tabela wygenerowana z dwóch plików JSON powyżej:

python: Python (wyłączona przez LINUMERT_NATIVE=0), 2026-11-05 15:59 · native: natywna (C), 2026-11-05 16:02

| Obszar | Dane | python [ms] | native [ms] | × |
|---|---|---:|---:|---:|
| generator CAM | 100×80 mm | 259.9 | 333.1 | 0.8 |
| generator płaskorzeźby plan_relief | 1458 trójkątów, 401×81 | 747.9 | 231.5 | 3.2 |
| ścieżka load_path | linumert_demo | 12.3 | 12.7 | 1.0 |
| symulacja offline simulate | linumert_demo | 756.6 | 135.5 | 5.6 |
| ścieżka load_path | linumert_neon_demo | 15.2 | 15.1 | 1.0 |
| symulacja offline simulate | linumert_neon_demo | 705.3 | 105.9 | 6.7 |
| ścieżka load_path | linumert_rowek | 12.2 | 11.1 | 1.1 |
| symulacja offline simulate | linumert_rowek | 11.1 | 14.1 | 0.8 |
| ścieżka load_path | linumert_kwadrat | 12.1 | 9.8 | 1.2 |
| symulacja offline simulate | linumert_kwadrat | 182.1 | 26.0 | 7.0 |
| ścieżka load_path | linumert_wiercenie | 13.1 | 11.6 | 1.1 |
| symulacja offline simulate | linumert_wiercenie | 277.2 | 65.8 | 4.2 |
| ścieżka load_path | linumert_kolizja | 10.7 | 9.9 | 1.1 |
| symulacja offline simulate | linumert_kolizja | 27.2 | 6.4 | 4.3 |
| ścieżka load_path | linumert_g2_odbior | 11.5 | 10.2 | 1.1 |
| symulacja offline simulate | linumert_g2_odbior | 2.0 | 2.0 | 1.0 |
| ścieżka load_path | gen_kieszen_planowanie | 8.2 | 8.3 | 1.0 |
| ścieżka parse_subset | gen_kieszen_planowanie | 8.2 | 8.3 | 1.0 |
| symulacja offline simulate | gen_kieszen_planowanie | 3623.7 | 764.1 | 4.7 |
| ścieżka load_path | gen_plaskorzezba | 587.3 | 595.7 | 1.0 |
| ścieżka parse_subset | gen_plaskorzezba | 575.8 | 583.6 | 1.0 |
| symulacja offline simulate | gen_plaskorzezba | 4554.2 | 2247.8 | 2.0 |
| podgląd Toolpath | gen_plaskorzezba | 603.1 | 614.4 | 1.0 |
| podgląd Toolpath.locate | ostatnia linia | 1.1 | 1.3 | 0.9 |
| STL read_stl | 50880 trójkątów | 6.8 | 6.8 | 1.0 |
| STL read_stl | 12640 trójkątów | 116.7 | 121.0 | 1.0 |
| STL section_xy | 50880 trójkątów | 23.2 | 21.5 | 1.1 |
| płaskorzeźba plan_relief | 1458 trójkątów, 32481 pkt | 517.4 | 112.4 | 4.6 |
| płaskorzeźba ball_tip_height ×200 | 1458 trójkątów | 135.2 | 138.9 | 1.0 |
| eksport materiału write_stl | 200×160 komórek | 21.6 | 23.6 | 0.9 |
| brama WebHMI Gateway.step ×500 | FakeBackend | 20.0 | 20.2 | 1.0 |
| Plant ramka LRT-NET ×2000 | mill_servo_table | 191.5 | 196.1 | 1.0 |
