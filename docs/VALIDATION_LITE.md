# Weryfikacja linumeRT lite — 2026-10-28

Model-Author: Codex. Autokontrola, bez niezależnego przeglądu.
Baza pełnej edycji: a593d6d4c55f503fbaf4c607099f2d89c61cc670.
Środowisko: Debian 12 / WSL, Python 3.11, osobny venv;
wersje zależności w requirements-dev.lock. Pełny checkout pozostał bez zmian.

| Sprawdzenie | Wynik |
|---|---|
| Pełna regresja Pythona bez LinuxCNC | 1151 PASS, 61 subtestów PASS, 333,56 s |
| Szybki zestaw test-core | 224 PASS |
| Testy C Plant | 109 PASS (29 osi, 59 napędu, 21 maszyny) |
| Macierz Plant | 5/5 konfiguracji, każda 4/4 kryteriów |
| Nowe kontrakty lite | 19 PASS |
| Granice architektury i offline trace po sprzątnięciu runnera HTTP | 13 PASS |
| Ruff i git diff --check | PASS |
| Wheel poza checkoutem | kompilacja, symulacja, szablony, zasoby konfiguracji, CLI Plant i model C PASS |
| Przykłady z README | kompilacja part.lnx, cut.ngc → JSON (88 mm³ ubytku), zapis konfiguracji sim PASS |

Po przeniesieniu napędów porównano dokładną równość skal konfiguratora i modelu Plant
na pięciu zachowanych maszynach. Kod plant/core i komponenty hal/ nie zmieniły się.
Eksport konfiguracji sprawdza zasoby HAL/makr, odmowę hardware/ATC, jawny bypass
wyłącznie sim/Plant, podgląd bez zapisu, kopię zapasową i zachowanie tabeli narzędzi operatora.

Wheel uruchomiono z tymczasowego katalogu z python -I; sprawdzono ścieżkę importowanego
pakietu i użyto jawnego LINUMERT_PLANT_LIB dla natywnego modelu z tej wersji źródeł.
Nie dołączono biblioteki .so do uniwersalnego wheel; Plant wymaga osobnej kompilacji C.

Nie uruchamiano LinuxCNC RIP, PREEMPT_RT ani fizycznej maszyny. Testy z markerem
linuxcnc są poza tym odbiorem; część z nich sprawdza opcjonalny interpreter rs274.
Proces DISPLAY i wygenerowane pliki nie mają odbioru w działającej instancji LinuxCNC.
Windows poza WSL nie jest docelowym środowiskiem regresji lite.
NIEZWERYFIKOWANE NA SPRZĘCIE. Wyniki Plant/subset nie kwalifikują fizycznego sterowania.

Duża redukcja drzewa dotyczy także dawnych instrukcji, raportów, GUI i zasobów.
Nie oznacza zmniejszenia złożoności fizyki ani udowodnienia możliwości konkretnego LLM.

## Podgląd konsolowy

2026-10-28 · Model-Author: Codex. tools/console_demo.py i launcher PowerShell/WSL
sprawdzono na rdzeniu Plant C dla first_motion i estop_mid_program, także w terminalu TTY.
Pełna regresja po dodaniu pokazu: 1153 PASS, 61 subtestów PASS (368,13 s).
Po dopracowaniu mapowania czasu rozruchu na czas scenariusza: 3/3 testy konsoli PASS,
w tym brak przedwczesnego alarmu E-STOP. Ruff i ponowny wheel-check PASS.
Launcher sprawdzono przy pierwszej instalacji .venv-linux i przy ponownym uruchomieniu.
To odtwarzanie telemetrii symulatora z atrapą mastera, bez monitorowania żywego LinuxCNC.

## Raster 3D w terminalu

2026-10-28 · Model-Author: Codex. Pełna regresja: 1170 PASS, 61 subtestów PASS
(399,91 s), testy wymagające LinuxCNC wyłączone. Po dopracowaniu dopasowania kamery
i zmiany rozmiaru okna: 19/19 testów renderera oraz konsoli PASS. Ruff PASS.
Testy obejmują osiem bitów Braille, głębię/kolor, rastry block/ASCII, zmianę Z,
obrót kamery, granice zoomu oraz dokładny rozmiar złożonych paneli dla trzech terminali.
Native PowerShell/WSL TTY: obrót, nachylenie, zoom, pauza, Q i przywrócenie terminala
sprawdzone; launcher .cmd sprawdzony także z -Once i w trybie ASCII.
Renderer korzysta z rzeczywistej telemetrii symulatora Plant. Żółte narzędzie i obwiednia
są schematyczne; nie dodano geometrii skrawania, sterowania sprzętem ani zmian rdzenia.

## HD 2x: rzeczywista siatka terminala

2026-10-28 · Model-Author: Codex. Native Windows Console / PowerShell 5.1:
zmierzono 120×30 → 240×60 komórek. Dwa kolejne przebiegi potwierdziły przywrócenie
120×30 i oryginalnej czcionki 8×16, również po wyjątku. -Density 1 nie zmienia stanu.
Test działa w osobnej ukrytej konsoli: tools/test_console_density.ps1.
Nie zmienia profili terminala ani rejestru. W pseudokonsoli stosuje jawny fallback;
console-hd.cmd uruchamia własny klasyczny host. Nie deklarujemy zmiany fontu Windows Terminal.

Pełna regresja Python: 1170 PASS, 61 subtestów PASS (354,76 s). Dodatkowe większe
obszary i warunek >=2x w obu osiach: zestaw renderera/konsoli 22/22 PASS. Ruff PASS.
Podniesiono limit płótna z 220×75 do 440×150, bez zmian rdzenia, fizyki ani telemetrii.
