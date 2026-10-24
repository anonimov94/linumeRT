# Macierz realizacji wymagań (Plant)

Model-Author: Claude · sesja 009. Źródło: `docs/wymagania/WIRTUALNA_OBRABIARKA.md`
(treść wymagań jest tam; zmiana tylko przez wpis w `docs/DECYZJE.md`). Opis realizacji: `docs/PLANT.md`.
Status: planowane → zaimplementowane → zielone; aktualizują sesje realizujące wymaganie.
Tabela jest zgodna z wymaganiami (pilnuje tego `tests/test_plant_spec.py`).

| REQ | Sesja | Test (scenariusz / test jednostkowy) | Status |
|---|---|---|---|
| REQ-VD-01 | 013, 021 | `test_drive_template_schema`, `test_drive_template_physics`; wrzeciono VFD: `tests/test_vfd.py`, `tests/test_plant_vfd_linuxcnc.py` | zielone |
| REQ-VD-02 | 013 | `test_drive_instance_overrides` | zielone |
| REQ-VD-03 | 013, 023 | `test_drive_clone_independent`, scenariusz `drive_clone_tuning` | zielone |
| REQ-VD-04 | 013, 022 | `test_live_params`, scenariusz `heavy_table_live` | zielone |
| REQ-VD-05 | 013 | `test_library_loads_all` | zielone |
| REQ-VD-06 | 061 | `test_template_real_mapping`, `test_servo_machine_maps_to_ethercat` (`tests/test_drive_real.py`) | zielone |
| REQ-VM-01 | 010 | `test_single_source` | zielone |
| REQ-VM-02 | 010, 014 | scenariusze `kin_gantry`, `kin_xyza`, `kin_trunnion` | zielone |
| REQ-VM-03 | 010, 014 | `gantry_skew_alarm` | zielone |
| REQ-VM-04 | 014 | `hardstop_crash` | zielone |
| REQ-VM-05 | 014 | `limit_switch_trip`, `shared_limit_input` | zielone |
| REQ-VM-06 | 019 | `softlimit_oracle`, `forbidden_zone_oracle` (`tests/test_plant_linuxcnc.py`, `tests/test_oracle.py`) | zielone |
| REQ-VM-07 | 015, 018 | `home_switch`, `home_switch_index`, `home_hardstop`, `home_absolute`, `home_drive_internal`, `home_gantry_square` | zielone |
| REQ-VM-08 | 020 | `atc_rack_geometry`, `atc_carousel_index`, `atc_cover_timing` (`tests/test_atc.py`) | zielone |
| REQ-VM-09 | 020 | `manual_change_position`, `toolsetter_measure` (`tests/test_atc.py`) | zielone |
| REQ-VM-10 | 020 | `crash_head_magazine` (`tests/test_atc.py`) | zielone |
| REQ-VM-11 | 010, 023 | `test_machine_validation_*` (≥ 15 przypadków); `tests/test_machine_finite.py`, `test_nonfinite_save_and_reload_preserve_model` — odrzucenie NaN/inf; audyt pozostałych luk geometrii: `raporty/03.md` | zielone |
| REQ-VM-12 | 023 | `tests/test_editor_api.py`, scenariusz `edit_reload` | zielone |
| REQ-QA-01 | 024 | `tools/check_requirements.py` w `make test`, `tests/test_requirements.py` | zielone |
| REQ-QA-02 | 024, 082 | job `plant-matrix` (`run_scenario.py --matrix`), `test_matrix_smoke_on_every_machine` | zielone |
| REQ-QA-03 | 016, 024 | 016: `test_fuzz_only_frame_errors`, `test_rejects_bad_frames`, `test_corrupt_frames_*`, `test_model_exception_gives_safe_state`, `test_watchdog_*`, `test_missing_template_refuses_start`, `test_bad_plant_yaml`; 024: `test_fuzz_machine_yaml`, `tests/test_scenario_faults.py`, scenariusze `link_loss`, `drive_fault_mid_program`, `estop_mid_program` (z LinuxCNC: `tests/test_scenario_linuxcnc.py`) | zielone |
| REQ-QA-04 | 016, 024 | `test_determinism` (016: SHA-256 odpowiedzi serwera); scenariusze: `test_scenario_is_deterministic`, `test_frame_loss_is_deterministic` | zielone |

Kontrola granicy uruchomienia (CLAUDE.md §6, konkurs 01; bez nowego identyfikatora REQ):
`tests/test_launch_gate.py` sprawdza odmowę przed exec, kompletną deklarację hardware,
pliki HAL/source, niejednoznaczne INI i profile sim/Plant z atrapą procesu CNC.
To dodatkowe pokrycie kontraktu konfiguracji; nie zmienia statusu REQ-VD-06 ani nie
stanowi odbioru fizycznego I/O, napędów lub zewnętrznego watchdoga.
