# Stan projektu i przekazanie

Tura: Codex · od 2026-10-19 · stan: w toku

Model-Author: Codex. Bieżący stan jest w tym pliku; historia w DZIENNIK.md.
Zasady: [WSPOLPRACA_MODELI.md](WSPOLPRACA_MODELI.md), kontrakt operatora:
[OBSLUGA_OPERATORA.md](OBSLUGA_OPERATORA.md), D36/D37.

## Wykonane HMI

Start, Maszyna, Bazowanie, Zero detalu 3D (prostopadłościan, walec, rura, odlew 360°),
Narzędzia, Program (wybór/podgląd/wczytanie), Symulacja, Produkcja, Diagnostyka.
Trzy ostatnie alarmy u góry; Reset zachowuje aktywne przyczyny, podwójny potwierdza zatrzask HAL.
Pola wymiarów: 4 miejsca po przecinku, wpis ręczny. JOG/MDI, M3/M4/M5,
wybór T i WYMIANA M6 w Maszyna i Symulacja. Wirtualna wymiana potwierdza handshake HAL.
Specjalista: wolny JOG, maks. 100 mm/s; klawiatura 10 mm/s bez przyspieszania Shiftem.
Wycofanie z kolizji geometrycznej tylko w jawnym bliźniaku i trybie MANUAL.
Reset symulacji odnawia materiał i bazuje do HOME z INI. Fizyczne safety i limity pozostają aktywne.

## Git i testy

PR #44 scalony; #45: integracja Symulacji/Narzędzi Claude. #46: zintegrowany zakres HMI Codex.
Zmiany #46 wypychane po małych testowanych krokach, z zachowaniem poprawki Claude 8b2bc17.
Testy Debian 12: widgety, geometria, model, symulacja, kontrakt HAL, IP i wymagania przechodzą.
Pełny lokalny pytest ograniczony blokadą gniazd sieciowych (EPERM); wynik sieci/LinuxCNC daje CI.
Samotest pełnego HMI ma 42 kroki, w tym MDI/M3/M5/M6 w Symulacji. Przed merge sprawdź oba workflow.
Nie uznawaj otwartego podglądu offline za uruchomione pełne HMI.

## Uruchomienie

- Pełny bliźniak: `tools/linumert-start.sh` (Debian 12 w Podmanie, LinuxCNC).
- Edytor offline: `bash tools/dev/preview-zero.sh` — bez CNC, zapis tylko tymczasowy.
- Lokalnie Codex: `/home/dell/Projekty/linumeRT-codex-hmi`; Claude: osobny checkout.
- Sandbox Codexa blokuje sieć i dostęp do pulpitu; nie omijaj ograniczeń. GUI podglądu sprawdzamy offscreen.
- Testy: `tools/dev/debian-container.sh make lint test test-c test-san`; pełne CNC przez CI/środowisko Claude.

## Dalej

1. Zakończyć CI #46; usunąć regresje; scalić po zielonych kontrolach.
2. Edycja i sprawdzanie G-code w widoku Program; tłumaczenia i pozostałe widoki workflow.
3. Weryfikacja fizycznej maszyny, safety/STO i napędów pozostaje osobnym zadaniem właściciela.
4. Pozostały plan sesji i bramki: `prompts/README.md`, `docs/raporty/G0.md`.

## Stan zatrzymania — interpreter, PR #49 · 2026-10-20

Model-Author: Codex. Właściciel zlecił kontynuację niezależnych zadań w chmurze bez PC.
`03591cf`: cytowanie ścieżek RIP/G-code, exec i kontrola kodu procesu; 4 testy lokalne OK.
CI w toku; osobna gałąź od main, niezależna od safety PR #48. Następny krok: odbiór CI.

## Stan zatrzymania — CI runtime, PR #51 · 2026-10-20

Model-Author: Codex. bb7374d: szersze filtry LinuxCNC i anulowanie starszych przebiegów PR.
YAML/ścieżki sprawdzone lokalnie. Następny krok: wynik obu workflow dla końcowego SHA.
PR #48 i #50 prowadzone osobno; nie nadpisywać ich przekazań przy scalaniu dokumentów.
