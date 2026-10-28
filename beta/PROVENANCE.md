# PROVENANCE — co zniknęło z wersji GUI i dlaczego

SPDX-License-Identifier: GPL-2.0-or-later

`beta/` jest bliźniakiem `linumeRT` bez warstwy wizualnej. Ten plik jest ścieżką audytu:
wymienia każdy usunięty plik, każdą zmianę w przejętym kodzie i każdy test, który
nie został przeniesiony — z powodem. Bez tego nie da się odróżnić „usunięte celowo”
od „zgubione przy kopiowaniu”.

Stan zweryfikowany: **902 testów przechodzi, 0 pominiętych, 77 podtestów**; `ruff` czysty;
`tools/check_no_gui.py` zwraca 0.

## 1. Pliki usunięte (GUI / Qt / OpenGL / panel web)

| Plik (w repo nadrzędnym) | Powód usunięcia |
| --- | --- |
| `simulation/linumert_sim/render_view.py` | jedyny plik Qt/OpenGL w symulacji — widok 3D ścieżki narzędzia. Symulacja offline liczy geometrię i czasy bez renderowania; GUI rysuje z `program.toolpath` / `sim.run`. |
| `plant/panel/app.py` | panel web (FastAPI + HTML) wirtualnej obrabiarki. Zastąpiony usługą `plant.*` w warstwie headless. |
| `plant/panel/static/` | zasoby statyczne panelu web (HTML/CSS/JS). |
| `plant/scenario_linuxcnc.py` | scenariusz wymagający LinuxCNC RIP **i** REST panelu web do wstrzykiwania usterek. Usterki idą teraz przez `plant.inject_fault`. |
| `config/sim/linumert_xyz/linumert_postgui.hal` | podpinał piny komponentu ekranu `linumert.*` (QtDragon). Bez GUI te sygnały nie istnieją. |

Katalog `plant/panel/` został, ale bez serwera: `__init__.py` nie importuje FastAPI
i rzuca `PanelUnavailable`, a `desk.py`, `editor.py`, `machine_library.py`, `presets.py`,
`record.py`, `telemetry.py` to logika bez warstwy wizualnej.

## 2. Zmiany w przejętym kodzie (5 poprawek ścieżek)

Kod rdzenia zakotwiczał ścieżki względem korzenia repozytorium; w `beta/` układ jest
inny (`plant_core/` zamiast `plant/core/`, `library/` zamiast `plant/library/`).

| Plik | Zmiana |
| --- | --- |
| `src/linumert/diag/doctor.py:37` | lista modułów do badania: `("yaml", "numpy", "linuxcnc", "hal")` — bez modułów Qt. |
| `src/linumert/machine/configgen.py:171` | generowane INI: `DISPLAY = linumert_headless` zamiast `qtvcp linumert`. |
| `src/linumert_plant/scenario.py:33` | `ROOT = Path(__file__).resolve().parents[2]`. |
| `src/linumert_plant/core_binding.py:29-31` | `ROOT = parents[2]`, `CORE_DIR = ROOT / "plant_core"`. |
| `src/linumert_sim/machine.py:22` | `DRIVES_DIR = parents[2] / "library" / "drives"`. |

## 3. Zmiany wynikające z braku GUI (bezpieczeństwo i wielowątkowość)

| Plik | Zmiana | Powód |
| --- | --- | --- |
| `src/linumert/machine/configgen.py` | generator nie emituje `linumert_hmi_estop.hal`, `linumert_pause_retract.hal` ani `POSTGUI_HALFILE` (domyślne `postgui = ""`) | grzyb E-STOP w HMI wchodzi **szeregowo** w łańcuch i jest fail-safe: bez ekranu jego piny są `0`, więc łańcuch nigdy by się nie zamknął. Łańcuch zostaje sprzętowy/emulowany (`lrt_estop2`). Przyszłe GUI dokłada swój element przez `hal_dir` — bez zmian w generatorze. |
| `config/sim/linumert_xyz/linumert_xyz.ini`, `config/plant/linumert_plant_xyz/linumert_plant_xyz.ini` | `DISPLAY = linumert_headless`, usunięte `HALFILE` zależne od ekranu | referencyjne konfiguracje startowały ekran Qt i ładowały HAL-e ekranu. |
| `src/linumert/access/__init__.py:82`, `src/linumert/diag/journal.py:21`, `src/linumert/tools/db.py:206` | `sqlite3.connect(..., check_same_thread=False)` | serwer jest wielowątkowy (uvicorn + pętla stanu). Bez tego **każdy** request REST dotykający dostępu, narzędzi albo dziennika padał z `sqlite3.ProgrammingError`. `sqlite3.threadsafety == 3` (serialized) w CPython 3.11, więc współdzielenie połączenia jest bezpieczne. |

## 4. Testy, które nie zostały przeniesione

W pierwszym commicie (`5fed224`) `beta/tests/` miało **63 pliki**: **56 przeniesionych
z rdzenia** (766 testów) i **7 napisanych od zera** dla warstwy usług — `test_cli_sdk`,
`test_contract`, `test_machine_service`, `test_no_gui`, `test_services`,
`test_transport_rest`, `test_transport_ws` (102 testy). Razem 868 zebranych: **865
przechodziło, 3 pominięte**. Z rdzenia nie przeniesiono:

**Testy warstwy wizualnej** — w bliźniaku nie ma czego testować:
`test_access_ui`, `test_appearance`, `test_checkbox_indicator`, `test_design_system`,
`test_diagnostic_history_gui`, `test_doctor_gui`, `test_hmi_*`, `test_i18n`,
`test_iso*`, `test_launcher`, `test_machine_page_layout`, `test_neon_render`,
`test_neon_view`, `test_numeric_keyboard`, `test_operator_controls`, `test_panel*`,
`test_pause_retract_gui`, `test_pause_settled`, `test_program_startup`,
`test_render_gl`, `test_render_mesh`, `test_report_gl`, `test_skin_*`,
`test_tool_filters_gui`, `test_workpiece_view`, `test_webhmi_*`.

**Testy wymagające LinuxCNC** — bliźniak musi działać bez RIP (atrapy zamiast sprzętu):
`test_*_linuxcnc.py`, `test_ngc_linuxcnc`, `test_m6_remap`, `test_toolpath`,
`test_estimate`, `test_sim_path`, `test_cam_interpreter`, `test_lexer`,
`test_limits*`, `test_gen_*`, `test_hal_*`, `test_atc_macro`, `test_subroutines`,
`test_tools_db`, `test_sim_config`.

**Testy narzędzi repozytorium nadrzędnego** — tych narzędzi w `beta/` nie ma:
`test_agent_runner` (`tools/agent_tests/`), `test_hmi_inventory`, `test_lock`,
`test_requirements` (`tools/check_requirements.py`), `test_roadmap` (`tools/roadmap.py`),
`test_stock_probe`, `test_suite_cycles`, `test_lrtnet`, `test_vm_link` (`tools/vm/`).

**Testy dokumentów i procesu repo nadrzędnego** — `beta/` ma własną dokumentację:
`test_license` (`LICENSE`, `docs/LICENCJE.md`), `test_plant_spec`
(`docs/PLANT.md`, `docs/wymagania/MACIERZ.md`), `test_launch_gate`,
`test_launch_runtime`, `test_machine_drives`, `test_plant_server`,
`test_probe_scenarios`, `test_smoke_cleanup` — wymagały zainstalowanego pakietu
w procesach potomnych albo plików `config/hal/` zależnych od HMI.

## 5. Poprawki w przejętych testach

| Plik | Zmiana | Powód |
| --- | --- | --- |
| `tests/test_configgen.py` | asercja `DISPLAY` → `linumert_headless` | test sprawdzał obecność ekranu Qt. |
| `tests/test_build_machine.py` | `python -m plant` → `-m linumert_plant` | nazwa pakietu w bliźniaku. |
| `tests/test_plant_core.py`, `tests/test_drive_library.py` | `plant/core` → `plant_core` | nazwa katalogu rdzenia C. |
| `tests/test_machine_drives.py` *(usunięty)*, `tests/test_accel_tuning.py`, `tests/test_plant_substeps.py`, `tests/test_probe_scenarios.py` | `plant/library` → `library`, `plant/scenarios` → `scenarios` | układ katalogów. |
| `tests/conftest.py` | `PYTHONPATH` eksportowany do procesów potomnych, `REPO = beta/` | bliźniak nie jest instalowany w `site-packages`. |

## 6. Czego tu nie ma i co to znaczy dla wdrożenia

- **Brak ekranu** — LinuxCNC uruchamiany z wygenerowanego INI nie pokaże GUI
  (`DISPLAY = linumert_headless`). Operator pracuje przez API/CLI, dopóki nie powstanie GUI.
- **Brak grzyba E-STOP w HMI** — łańcuch E-STOP jest sprzętowy/emulowany. Przed
  podłączeniem fizycznego GUI należy dołożyć `linumert_hmi_estop.hal` (fail-safe:
  łańcuch otwarty, dopóki ekran nie żyje).
- **`machine.tool_change` i `offset.probe_run`** działają jako makra LinuxCNC
  (`T<n> M6` z remapem, `o<lrt_probe>`); atrapa wykonuje M6, ale sondowanie odrzuca
  (`conflict`) — pełna ścieżka wymaga LinuxCNC (VM-A + Plant).
- **Wszystko, co dotyczy fizycznej maszyny, jest NIEZWERYFIKOWANE NA SPRZĘCIE** —
  testy idą na atrapie (`backend=fake`). Backend LinuxCNC nie był uruchamiany
  na prawdziwym sterowniku w tym środowisku.
