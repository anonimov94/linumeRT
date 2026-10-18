# config/plant

Konfiguracje LinuxCNC połączone z wirtualną obrabiarką Plant przez komponent `lrt_net` (LRT-NET v1).
Uruchomienie i testy: [`docs/PLANT_START.md`](../../docs/PLANT_START.md).

| Plik | Do czego |
|---|---|
| `plant.example.yaml` | przykład `plant.yaml`: maszyna, sieć, czas, tryb, ślad, falownik (opis pól: `docs/PLANT.md` §7) |
| `linumert_plant_xyz/linumert_plant_xyz.ini` | maszyna `mill_servo_table` (X, portal Y1/Y2, Z), ekran linumert, wrzeciono `sim_spindle` (`spindle_sim.hal`) |
| `linumert_plant_xyz/linumert_plant_xyz_vfd.ini` | to samo z wrzecionem przez falownik: `hy_vfd` (`spindle_vfd.hal`, sekcja `[VFD]`) |
| `linumert_plant_xyz/linumert_plant.hal` | napędy, krańcówki, E-STOP, sonda, wyrocznia (kontrakt `docs/HAL_KONTRAKT.md`) |
| `linumert_plant_xyz/plant.yaml`, `plant_vfd.yaml` | serwer Plant dla obu wariantów (`plant_vfd.yaml` uruchamia emulator falownika na pty i Modbus TCP) |
| `linumert_plant_xyz/bazowanie/` | warianty bazowania (twardy zderzak, bazowanie w napędzie) |

Wartości osi pochodzą z `config/machines/mill_servo_table.yaml`; zgodność pilnuje `tests/test_plant_config.py`.
NIEZWERYFIKOWANE NA SPRZĘCIE.
