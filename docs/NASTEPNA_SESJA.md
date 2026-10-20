# Stan projektu i przekazanie

Tura: Codex · od 2026-10-20 · stan: w toku

Model-Author: Codex, aktualizacja Claude (koniec 2026-10-19). Bieżący stan jest w tym pliku; historia w DZIENNIK.md.
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

1. Scalić PR #47 po zielonym CI (Cykle, Program: Sprawdź/Edytuj, E-STOP dwukanałowy NC, generatory, STL, D38).
2. **D38 wznowienie obróbki**: `core/linumert/programs/resume.py` (punkt wejścia z zakładką, helisa, łuk),
   sprawdzenie w `linumert_sim`, external offsets dla pauzy, przyciski w HMI ([`design/WZNOWIENIE.md`](design/WZNOWIENIE.md)).
3. Raport HTML symulacji i oś czasu zdarzeń (059, 057); walidacja generatorów z bazą narzędzi (040).
4. Usunąć scalone gałęzie (limit właściciela: 5 gałęzi, 2 PR; Claude ma usuwanie zablokowane).
5. Dalszy plan: `prompts/README.md` (stan częściowy 040, 042, 055–059 oznaczony); weryfikacja sprzętu — właściciel.

## Stan zatrzymania — Program, PR #50 · 2026-10-20

Model-Author: Codex. `6beec3d`: kontrola składni w GUI bez LinuxCNC, lista i nawigacja.
Cztery funkcje testowe widoku Program na rzeczywistym Qt offscreen OK; screenshot obejrzany.
Limit 64 KiB/100 wyników jawny w GUI. CI w toku. Następny etap: edycja/zapis programu.
Osobne PR: #48 safety/symulacja; #49 granica procesu rs274. Wszystkie wymagają zakończenia CI.

## Stan zatrzymania — interpreter, PR #49 · 2026-10-20

Model-Author: Codex. Właściciel zlecił kontynuację niezależnych zadań w chmurze bez PC.
`03591cf`: cytowanie ścieżek RIP/G-code, exec i kontrola kodu procesu; 4 testy lokalne OK.
CI w toku; osobna gałąź od main, niezależna od safety PR #48. Następny krok: odbiór CI.

Aktualizacja PR #50: 90cea5f — edycja pełnego pliku i zapis nowej kopii (do 256 KiB).
4 testy plików + 6 funkcji widoku Qt offscreen OK. CI w toku. PR #49 scalony, main włączony.
Dalej: odbiór CI, kontrola niezapisanych zmian i integracja pełnego HMI. LinuxCNC lokalnie brak.

Integracja PR #50 z main 1987f28 (#47/#53): zachowane zmiany Claude i przekazanie.
Jeden przycisk kontroli; zapis kopii zamiast nadpisania. Osiem testów Program Qt offscreen OK,
także bez rdzenia na początkowym PYTHONPATH. CI ponowione po usunięciu importów blokujących start.
