# Pochodzenie ekranu linumert (kopia bazowa QtDragon)

Model-Author: Claude · sesja 005 · 2026-10-18

| | |
|---|---|
| Źródło | ekran `qtdragon` z LinuxCNC (`share/qtvcp/screens/qtdragon/`) |
| Wersja | LinuxCNC **2.9.10** (pakiet `linuxcnc-uspace 1:2.9.10`, linuxcnc.org bookworm 2.9-uspace) |
| Commit upstream | `86cdca76fa2a36274c432caa21952b23c267989a` (tag `v2.9.10`) |
| Wersja ekranu | `UPSTREAM_version.txt` (kopia `version.txt` QtDragon) |
| Licencja | GPL-2.0 (LinuxCNC, plik COPYING); nasze zmiany GPL-2.0-or-later, całość rozpowszechniana na GPL-2.0 |
| Wariant | QtDragon 1280×768+ (`qtdragon.ui`); wariant `qtdragon_hd` nieużywany |

## Pliki
| Nasz plik | Plik upstream | Zmiany |
|---|---|---|
| `linumert.ui` | `qtdragon.ui` | odwołanie do zasobów `qtdragon.qrc` → `linumert.qrc`; domyślna ścieżka pliku ustawień |
| `linumert.qrc` | `qtdragon.qrc` | bez zmian |
| `linumert.qss` | `qtdragon.qss` | bez zmian |
| `linumert_upstream_handler.py` | `qtdragon_handler.py` | **bez zmian** (wzorzec patch) |
| `linumert_handler.py` | — | własny: klasa pochodna `HandlerClass`, tytuł okna, nakładka linumeRT (`LINUMERT_SHELL=0` wyłącza) |
| `linumert_shell.py`, `linumert_shell_model.py`, `linumert_shell_selftest.py` | — | własne (HMI-PoC): powłoka i widok „Maszyna” wokół niezmienionego QtDragon, samotest GUI |
| `linumert_ABOUT` | `qtdragon_ABOUT` | bez zmian |
| `UPSTREAM_version.txt` | `version.txt` | bez zmian |
| `images/*.png` | `images/*.png` | bez zmian; usunięty nieużywany `linuxcnc-wizard.gif` |

Nieskopiowane: style alternatywne (`argentium.qss`, `brushed_metal*.qss`, `qtdragon-bright.qss`,
`qtdragon_dark_grey.qss`, `qtdragon_flat.qss`). Wygląd linumeRT powstanie z `docs/design/tokens.yaml`.

`resources.py` generuje QtVCP przy starcie z `linumert.qrc` (ignorowany przez Git).

## Uruchomienie
Konfiguracja `config/sim/linumert_xyz/` ma `DISPLAY = qtvcp linumert`; QtVCP znajduje ekran przez
dowiązanie `config/sim/linumert_xyz/qtvcp/screens/linumert` → `screens/linumert/`.

## Aktualizacja z upstream
1. Pobierz nową wersję `share/qtvcp/screens/qtdragon/` (np. z pakietu w `tools/dev/linuxcnc-gui.sh`:
   `cp -r /usr/share/qtvcp/screens/qtdragon /work/state/up`).
2. `diff state/up/qtdragon_handler.py screens/linumert/linumert_upstream_handler.py` → podmień kopię
   handlera w całości; sprawdź, czy metody nadpisane w `linumert_handler.py` nie zmieniły sygnatur.
3. `diff <(sed 's/qtdragon\.qrc/linumert.qrc/g' state/up/qtdragon.ui) screens/linumert/linumert.ui` —
   przenieś zmiany upstream; nasze zmiany w `.ui` dopisuj do tabeli wyżej.
4. Uaktualnij wersję i commit w tej tabeli, `UPSTREAM_version.txt` i `docs/PROVENANCE.md`.
5. `pytest -o addopts= -m linuxcnc tests/test_sim_config.py` i ręczny start ekranu.
