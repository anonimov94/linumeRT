# tools

Narzędzia deweloperskie, CI i koordynacji pracy. Polecenia środowiska krok po kroku:
[`docs/NASTEPNA_SESJA.md`](../docs/NASTEPNA_SESJA.md) §4 i [`docs/PLANT_START.md`](../docs/PLANT_START.md).

| Ścieżka | Do czego |
|---|---|
| `linumert-start.sh` | **starter aplikacji** (README „Szybki start”): pobiera/aktualizuje main, instaluje podman, buduje obraz Debian 12 + LinuxCNC 2.9 (pakiety linuxcnc.org), otwiera ekran linumeRT na symulatorze; `--plant` z Plant i panelem, `--desktop` skróty w menu |
| `dev/debian-container.sh` | dowolne polecenie w kontenerze Debian 12 (podman/docker albo rootfs) z repo jako `/work`; wyniki testów liczą się tylko z Debiana 12 (D27), np. `tools/dev/debian-container.sh make lint test test-c test-san` |
| `dev/wsl-test.sh` | testy zatwierdzonego HEAD gałęzi w WSL (Windows): świeży klon i venv w `~/linumert-test/<gałąź>`, `--linuxcnc` z blokadą `linuxcnc`; równoległe sesje (D33, `prompts/archiwum/START-PODZIAL.md`) |
| `dev/plant-gui.sh` | LinuxCNC (RIP) + serwer Plant + ekran linumert w kontenerze, okno na pulpicie; `VFD=1` = wariant z hy_vfd; `HEADLESS=1 … CMD` = polecenie w gotowym środowisku |
| `dev/linuxcnc-gui.sh` | LinuxCNC 2.9 z pakietów linuxcnc.org (symulator `config/sim`) z oknem na pulpicie |
| `dev/zrzut_ekranu.py` | zrzut ekranu linumeRT pod Xvfb (raporty kamieni) |
| `dev/autozapis.sh` | opcjonalny autozapis pracy co 10 min (tylko gałęzie `wip/*` i `claude/*`) |
| `lock.py` | blokady zasobów współdzielonych (`linuxcnc`, `wsl-build`) przy pracy równoległej (D30, `WSPOLPRACA_MODELI.md` §2a) |
| `ci/` | skrypty CI: budowa i testy LinuxCNC 2.9 RIP (sesja 003, `build-linuxcnc.sh`, `test-linuxcnc.sh`) |
| `agent_tests/` | wspólna paczka testowa z raportem JSON i launcherem Windows ([README](agent_tests/README.md)) |
| `vm/` | pulpit VNC w WSL (`start-vnc.sh`); skrypty maszyn wirtualnych VM-A/VM-B w sesji 025 |
| `check_requirements.py` | (od sesji 024) kontrola znaczników REQ w testach względem macierzy |

Diagnostyka scenariusza z LinuxCNC (pod wspólną blokadą zasobu):
`LINUMERT_SCENARIO_DIAGNOSTICS=build/scenario-evidence python tools/run_scenario.py first_motion --master linuxcnc`.
Każde uruchomienie zachowuje osobny `lrt_scen_*`: konfigurację, plan, driver,
raport Plant, stdout/stderr LinuxCNC, logi drivera/Plant i telemetrię.
Log drivera zawiera próbki `PEAK` z nowym maksimum błędu, stanem jointa i licznikami LRT-NET.
To próbki NML (~10 ms), nie ślad każdego cyklu servo; dodatkowy odczyt HAL może wpływać
na pomiar czasu. Bez tej zmiennej katalog tymczasowy jest usuwany jak dotychczas.

### Ślad serwo scenariusza Plant (M1)

Po zajęciu wspólnej blokady LinuxCNC: ustaw `LINUMERT_SCENARIO_DIAGNOSTICS=build/evidence` oraz `LINUMERT_SCENARIO_SERVO_TRACE=1`, a następnie uruchom pojedynczy scenariusz z `--master linuxcnc`. Trace jest opcjonalny i wymaga trwałego katalogu diagnostyki.

Standardowy sampler LinuxCNC zapisuje kanały X/Z i LRT-NET na końcu servo-thread. `servo_trace.txt` zaczyna każdą próbkę numerem cyklu próbkowania; `servo_trace.json` zawiera nazwy kolumn, integralność, overruns i pozostałą głębokość FIFO. `valid=false` wyklucza użycie śladu jako ciągłego. Nie jest to atomowy pomiar fizyczny Plant/NML: wartości zachowują kolejność aktualizacji producentów w HAL. Nie zmienia sterowania ani zabezpieczeń.

Analiza bez uruchamiania LinuxCNC: `PYTHONPATH=plant/server python -m linumert_plant.scenario_trace_analysis KATALOG --out wynik.json`. Katalog musi zawierać kompletne servo_trace.json/txt. Porównuje fazy 0/1/2 na tej samej populacji próbek ruchu, zachowuje hashe i odmawia analizy nieciągłego lub niespójnego śladu. Wynik nie jest estymatorem przyczynowego opóźnienia ani dokładnością fizyczną.
- `tools/tune_accel.py` — dobór największego przyspieszenia osi na Plant z budżetu uchybu (M1); opis: `plant/server/linumert_plant/accel_tuning.py`, raport `docs/raporty/prototypy/M1_ACCEL_TUNING_2026-10-25.md`.
