# plant/server

Serwer Plant (pakiet linumert_plant): protokol LRT-NET, scenariusze, panel web (FastAPI + uPlot).

## Serwer LRT-NET (sesja 016)

- `linumert_plant.lrtnet` — ramki LRT-NET v1 (docs/PLANT.md §3): `encode_*`/`decode_*`, `FrameError`.
- `linumert_plant.server.PlantServer` — `handle(ramka) → odpowiedź` (bez gniazd; testy i scenariusze),
  `serve(sock)` (UDP), watchdog E-4003, statystyki, stan bezpieczny, `digest` (SHA-256 śladu).
- `linumert_plant.trace.TraceWriter` — zapis przebiegu (CSV/JSON Lines) w osobnym wątku.
- `python -m linumert_plant serve [machine.yaml] [--plant plant.yaml] [--lockstep|--realtime]
  [--port N] [--trace plik.csv] [--frames N]`; przykład: `config/plant/plant.example.yaml`.
- `plant/server/test_master.py` — master testowy udający LinuxCNC (CiA 402, profil trapezowy):
  `python plant/server/test_master.py --axes 4 --distance 50000` (z serwerem na localhost).

## Wirtualna obrabiarka z machine.yaml (sesja 014)

- `linumert_plant.build_machine` — `build_machine(machine.yaml)` → `MachineModel`: klucze rdzenia C
  (SI), nazwy osi/napędów/członów, mapa wejść, kinematyka LinuxCNC presetu (`LINUXCNC_KINEMATICS`).
  Presety łańcucha: `PRESET_CHAINS` (osie liniowe stołu mają wektor przeciwny — dodatni ruch osi to ruch
  narzędzia względem detalu w plus, jak trivkins). Środki obrotu stołów w presetach są w zerze maszyny;
  inne położenie przez `kinematics.chain` z `offset`.
- `linumert_plant.core_binding.PlantMachine` — uruchomiony model (ctypes, `plant/core/build/libplant_core.so`
  budowana automatycznie przez `make -C plant/core shared`); API w jednostkach machine.yaml (mm, stopnie).
- CLI: `python -m plant machine build <machine.yaml> [--keys] [--run]`.
