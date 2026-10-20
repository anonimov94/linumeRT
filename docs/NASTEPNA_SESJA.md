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

## Audyt safety — 2026-10-20, PR #48 (Codex, sesja chmurowa)

Polecenie właściciela: PC w torze zezwolenia; symulacja bez safety. Audyt:
[bezpieczenstwo/README.md](bezpieczenstwo/README.md). Etap 1 na codex/safety-separation:
kontrakt wypchnięty c528144, proces symulacji bez komend CNC d8d5fda; 3 unittest lokalnie OK.
Dla Claude: przejrzeć #48 i CI; nie przywracać E-STOP z procesu materiału/kolizji przy integracji #47.
Zakres usunięcia emulacji w Plant czeka na odpowiedź właściciela; nie zmieniono jego łańcucha.
Następnie jawny profil sprzętowy i kontrakt I/O/nadzoru PC; brak gotowej konfiguracji hardware.
Stan zatrzymania: dokumentacja i pierwszy krok kodu wypchnięte, pełny odbiór Debian 12/GUI przez CI
oraz środowisko lokalne. LOCK pusty; bez lokalnej instancji LinuxCNC.
