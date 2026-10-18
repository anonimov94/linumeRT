# Macierz realizacji wymagań (Plant)

Model-Author: Claude · sesja 009. Źródło: `docs/wymagania/WIRTUALNA_OBRABIARKA.md`
(treść wymagań jest tam; zmiana tylko przez wpis w `docs/DECYZJE.md`). Opis realizacji: `docs/PLANT.md`.
Status: planowane → zaimplementowane → zielone; aktualizują sesje realizujące wymaganie.
Tabela jest zgodna z wymaganiami (pilnuje tego `tests/test_plant_spec.py`).

| REQ | Sesja | Test (scenariusz / test jednostkowy) | Status |
|---|---|---|---|
| REQ-VD-01 | 013 | `test_drive_template_schema`, `test_drive_template_physics` | zaimplementowane |
| REQ-VD-02 | 013 | `test_drive_instance_overrides` | zaimplementowane |
| REQ-VD-03 | 013, 023 | `test_drive_clone_independent`, scenariusz `drive_clone_tuning` | zaimplementowane |
| REQ-VD-04 | 013, 022 | `test_live_params`, scenariusz `heavy_table_live` | zaimplementowane |
| REQ-VD-05 | 013 | `test_library_loads_all` | zaimplementowane |
| REQ-VD-06 | 061 | `test_template_real_mapping` | planowane |
| REQ-VM-01 | 010 | `test_single_source` | zaimplementowane |
| REQ-VM-02 | 010, 014 | scenariusze `kin_gantry`, `kin_xyza`, `kin_trunnion` | zaimplementowane |
| REQ-VM-03 | 010, 014 | `gantry_skew_alarm` | zaimplementowane |
| REQ-VM-04 | 014 | `hardstop_crash` | zaimplementowane |
| REQ-VM-05 | 014 | `limit_switch_trip`, `shared_limit_input` | zaimplementowane |
| REQ-VM-06 | 019 | `softlimit_oracle`, `forbidden_zone_oracle` (`tests/test_plant_linuxcnc.py`, `tests/test_oracle.py`) | zaimplementowane |
| REQ-VM-07 | 015, 018 | `home_switch`, `home_switch_index`, `home_hardstop`, `home_absolute`, `home_drive_internal`, `home_gantry_square` | zaimplementowane |
| REQ-VM-08 | 020 | `atc_rack_geometry`, `atc_carousel_index`, `atc_cover_timing` (`tests/test_atc.py`) | zaimplementowane |
| REQ-VM-09 | 020 | `manual_change_position`, `toolsetter_measure` (`tests/test_atc.py`) | zaimplementowane |
| REQ-VM-10 | 020 | `crash_head_magazine` (`tests/test_atc.py`) | zaimplementowane |
| REQ-VM-11 | 010, 023 | `test_machine_validation_*` (≥ 15 przypadków) | zaimplementowane |
| REQ-VM-12 | 023 | `test_editor_api`, scenariusz `edit_reload` | planowane |
| REQ-QA-01 | 024 | samo narzędzie w CI | planowane |
| REQ-QA-02 | 024, 082 | job `plant-matrix` | planowane |
| REQ-QA-03 | 016, 024 | 016: `test_fuzz_only_frame_errors`, `test_rejects_bad_frames`, `test_corrupt_frames_*`, `test_model_exception_gives_safe_state`, `test_watchdog_*`, `test_missing_template_refuses_start`, `test_bad_plant_yaml`; 024: `test_fuzz_machine_yaml`, `plant_restart_midrun`, `link_loss` | zaimplementowane |
| REQ-QA-04 | 016, 024 | `test_determinism` (016: SHA-256 odpowiedzi serwera); scenariusze: 024 | zaimplementowane |
