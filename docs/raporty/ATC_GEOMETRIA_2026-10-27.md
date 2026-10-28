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
- Ruff zakresu PASS. Wyniki pełnej regresji i CI zostaną dopisane po zakończeniu.

Próby interpretera mają osobne HOME, plik parametrów i tabelę narzędzi. Nie korzystają z plików operatora. Samodzielny rs274 nie wykonuje fizycznego oczekiwania M66 ani wymiany na czujnikach HAL — te wyniki potwierdzają składnię, geometrię i warunki wstępne, nie cały ATC.

## Pozostały zakres

Sesja 066 pozostaje częściowa. Nadal potrzebne są mapowanie motion.digital-* do Plant, pełny remap z czujnikami i awariami, potwierdzenie zatrzymania wrzeciona, przywracanie stanu modalnego programu, dziennik transakcji i RECOVERY_REQUIRED po przerwaniu oraz osobne rozwiązania karuzeli/parasolowego magazynu. Sprawdzenie zakresów punktów nie jest dowodem bezkolizyjności całej drogi narzędzia i oprawki.

NIEZWERYFIKOWANE NA SPRZĘCIE. Autokontrola Codex, bez niezależnego przeglądu.

Dokumentacja parametrów interpretera: [LinuxCNC 2.9 — predefined named parameters](https://www.linuxcnc.org/docs/2.9/html/gcode/overview.html#sec:predefined-named-parameters).
