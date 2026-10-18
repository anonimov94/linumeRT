# plant/server

Serwer Plant (pakiet linumert_plant): protokol LRT-NET, scenariusze, panel web (FastAPI + uPlot).

## Wirtualna obrabiarka z machine.yaml (sesja 014)

- `linumert_plant.build_machine` — `build_machine(machine.yaml)` → `MachineModel`: klucze rdzenia C
  (SI), nazwy osi/napędów/członów, mapa wejść, kinematyka LinuxCNC presetu (`LINUXCNC_KINEMATICS`).
  Presety łańcucha: `PRESET_CHAINS` (osie liniowe stołu mają wektor przeciwny — dodatni ruch osi to ruch
  narzędzia względem detalu w plus, jak trivkins). Środki obrotu stołów w presetach są w zerze maszyny;
  inne położenie przez `kinematics.chain` z `offset`.
- `linumert_plant.core_binding.PlantMachine` — uruchomiony model (ctypes, `plant/core/build/libplant_core.so`
  budowana automatycznie przez `make -C plant/core shared`); API w jednostkach machine.yaml (mm, stopnie).
- CLI: `python -m plant machine build <machine.yaml> [--keys] [--run]`.
