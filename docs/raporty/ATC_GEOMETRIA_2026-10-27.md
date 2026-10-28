# 066 — ATC: zgodna geometria i kontrola przed wymianą

Model-Author: Codex · 2026-10-27 · baza main eb2deea.

Plant i generator makra M6 korzystają ze wspólnego wyznaczania pozycji gniazd w rdzeniu. Jawne slot_positions z machine.yaml mają pierwszeństwo przed bazą i rozstawem; makro obsługuje też konfigurację bez base_position/pitch_mm. Generator odmawia eksportu nieosiągalnej geometrii i sprawdza numery obu narzędzi przed ruchem.

## Odtworzony problem

Plant uwzględniał `slot_positions`, a `plan_swap` i makro zawsze wyznaczały XY ze wzoru baza + numer gniazda × rozstaw. Gdy konfiguracja zawierała oba opisy, makro jechało do innych punktów niż model magazynu. Przy samych jawnych pozycjach generator odmawiał eksportu mimo poprawnej geometrii obsługiwanej przez Plant.

Obliczenia pozycji przeniesiono bez zmiany zachowania z `linumert_plant.atc` do `linumert.machine.toolchanger_geometry`. Dotychczasowy import `linumert_plant.atc.pocket_positions` pozostaje dostępny. Plan i makro korzystają z tego samego wyniku. W G-code są jawne, warunkowe przejazdy do każdej pozycji gniazda; nie ma drugiego wzoru odtwarzającego rozstaw.

## Kontrole

- Wszystkie pozycje gniazd oraz Z podejścia, wycofania i przejazdu muszą mieścić się w limitach XYZ. Sprawdzane są także współrzędne po zaokrągleniu do czterech miejsc.
- Wymagane `approach_z <= retract_z <= safe_z`, kompletna geometria i skończone wartości.
- Liczba jawnych pozycji musi odpowiadać `slots`; plan odrzuca numery narzędzi spoza 0…slots. Makro sprawdza stare i nowe narzędzie przed ścieżką bezczynności i ruchem.
- Przed fizyczną sekwencją makro wymaga G21/G90/G94 oraz programowego stanu M5. Odmowa następuje przed ruchem osi i wyjściami zacisku/osłony. Nie zmienia automatycznie trybów programu.

M5 oznacza tu stan polecenia interpretera, nie potwierdzenie fizycznego wyhamowania wrzeciona. Czujnik zatrzymania i pełna integracja HAL wymagają osobnego odbioru.

## Weryfikacja

- Windows/Python 3.12: `test_atc_macro`, `test_atc`, `test_machine_config`, `test_configgen`: 96 PASS, 1 SKIP (rdzeń C niedostępny na Windows).
- Debian 12, samodzielny interpreter `rs274` z oficjalnego pakietu Debiana `linuxcnc-uspace` 2.9.0~pre1+git20230208.f1270d6ed7-1+deb12u2: 8 PASS. Pakiet rozpakowano w prywatnym katalogu testów bez instalowania systemowego LinuxCNC i bez uruchamiania HAL.
- Trzy próby potwierdzają kanoniczny przejazd do jawnych gniazd 1/3/6 oraz zakończenie remapu. Pięć prób potwierdza odmowę przed ruchem i wyjściami dla G20, G91, G93, G95 i M3.
- Model Plant: wymiany 0→3, 2→5 i 4→0 dla nieregularnych gniazd bez TOOL_DROP, CLAMP_FAULT, POCKET_OCCUPIED i COVER_CRASH. Osobny przypadek sprawdza regał obrócony o 90°.
- Ruff zakresu PASS. Wyniki pełnej regresji i CI zapisano poniżej.

Próby interpretera mają osobne HOME, plik parametrów i tabelę narzędzi. Nie korzystają z plików operatora. Samodzielny rs274 nie wykonuje fizycznego oczekiwania M66 ani wymiany na czujnikach HAL — te wyniki potwierdzają składnię, geometrię i warunki wstępne, nie cały ATC.

## Pozostały zakres

Sesja 066 pozostaje częściowa. Po integracji #198 mapowanie motion.digital-* do Plant jest generowane. Nadal potrzebne są pełny remap z czujnikami i awariami, potwierdzenie zatrzymania wrzeciona, przywracanie stanu modalnego programu, dziennik transakcji i RECOVERY_REQUIRED po przerwaniu oraz osobne rozwiązania karuzeli/parasolowego magazynu. Sprawdzenie zakresów punktów nie jest dowodem bezkolizyjności całej drogi narzędzia i oprawki.

NIEZWERYFIKOWANE NA SPRZĘCIE. Autokontrola Codex, bez niezależnego przeglądu.

Dokumentacja parametrów interpretera: [LinuxCNC 2.9 — predefined named parameters](https://www.linuxcnc.org/docs/2.9/html/gcode/overview.html#sec:predefined-named-parameters).

## Integracja #197 i #198 — 2026-10-28

Model-Author: Codex. PR #197 (`d278f5e`) i #198 (`a593d6d`) scalone odpowiednio jako `20dd962` i `d3945d3`. Oba źródłowe SHA miały SUCCESS python, plant-matrix i linuxcnc. Przegląd #198 objął wyznaczanie pinów z makra, num_dio i wykrywanie konfliktów również z plikiem wrzeciona. To przegląd kodu Claude przez Codex; geometria #197 i odbiór połączenia są autokontrolą Codex.

Połączony zakres w kontenerze Debian 12 `localhost/linumert-branches-test:bookworm-git`: `tests/test_atc_hal.py`, `test_atc_macro.py`, `test_atc.py`, `test_configgen.py`, `test_machine_config.py`: **100 PASS**, 8 deselected. Osobno rzeczywisty `rs274`: **8 PASS**, 33 deselected. Prywatne HOME i pliki parametrów/tabeli w kontenerze; bez uruchamiania HAL i bez zasobów operatora.

Te próby nie potwierdzają oczekiwania na rzeczywiste czujniki M66. Kolejny krok: odbiór remapu z Plant i kontrolowanym brakiem potwierdzenia zacisku, następnie dziennik transakcji i recovery. Sesja 066 pozostaje partial. NIEZWERYFIKOWANE NA SPRZĘCIE.

### CI połączonego kodu `88070aa` (PR #199)

- [Python i macierz Plant, run 40639005705](https://github.com/anonimov94/linumeRT/actions/runs/40639005705): SUCCESS; Python **1740 PASS, 127 SKIP, 177 deselected**. Lint i macierz Plant PASS.
- [LinuxCNC RIP, run 40639005668](https://github.com/anonimov94/linumeRT/actions/runs/40639005668): SUCCESS; wspólny runner **177 live PASS**, 1899 deselected; kroki ekranu i renderera również SUCCESS.
- Te wyniki dotyczą kodu połączenia #197/#198. Późniejsza synchronizacja z merge commitami main nie zmieniła kodu.

Lokalne `make lint test test-c` w obrazie z systemowym modułem gcode: lint PASS, następnie FAIL testu `test_sim_path` i SIGSEGV w `test_sim_worker`, stos `parse_rs274` (`simulation/linumert_sim/path.py:307`). `test-c` nie został w tym poleceniu osiągnięty. Taki przebieg systemowego gcode 2.9 był już opisany w przekazaniu odbioru #190/#184 na czystym main; nie zaliczamy lokalnej próby jako PASS. Log pozostaje w `/tmp/linumert-atc-integration-20261028.log`. Powtórka offline korzysta z nowego venv bez systemowego modułu gcode; oddzielny odbiór rzeczywistego interpretera i CI RIP opisano wyżej.
